
"""Business API routes for ML predictions and case management."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.agents.compliance_agent import answer_compliance_question
from src.agents.fraud_agent import assess_transaction_fraud
from src.agents.report_agent import compile_report
from src.agents.risk_agent import assess_credit_risk
from src.api.auth import get_current_user
from src.api.middleware import safe_error_detail
from src.api.schemas import (
    CaseCreateRequest,
    ComplianceQueryRequest,
    CreditRiskRequest,
    CreditRiskResponse,
    DocumentUploadResponse,
    FraudModelsResponse,
    FraudRequest,
    InvestigationRequest,
    RagQueryRequest,
)
from src.database.models import Customer, InvestigationCase, Transaction
from src.database.postgres import get_db
from src.ml_models.fraud_detection import (
    load_fraud_artifact,
    predict_fraud_risk,
    predict_paysim_fraud_risk,
)
from src.services.document_service import ingest_document
from src.services.notification_service import notify_case_created
from src.utils.constants import FRAUD_MODEL_FILES, RAW_DATA_ROOT

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.post("/predict/credit-risk", response_model=CreditRiskResponse)
def predict_credit_risk_route(request: CreditRiskRequest):
    try:
        result = assess_credit_risk(request.applicant, request.dataset)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=safe_error_detail(exc),
        ) from exc

    return {
        **result["prediction"],
        "shap_drivers": result.get("shap_drivers", []),
    }


@router.post("/predict/fraud")
def predict_fraud_route(request: FraudRequest):
    try:
        return assess_transaction_fraud(
            request.transaction,
            account_id=request.account_id,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=safe_error_detail(exc),
        ) from exc


@router.post("/predict/fraud-models", response_model=FraudModelsResponse)
def predict_fraud_models_route(request: FraudRequest):
    """Run compatible saved fraud models without calling RAG or an LLM."""
    predictions: list[dict[str, Any]] = []

    for dataset, relative_path in FRAUD_MODEL_FILES.items():
        try:
            if dataset == "paysim":
                result = predict_paysim_fraud_risk(request.transaction)
            else:
                artifact = load_fraud_artifact(dataset)
                feature_columns = artifact["feature_columns"]

                missing = [
                    column
                    for column in feature_columns
                    if column not in request.transaction
                ]
                if missing:
                    raise ValueError(
                        f"{dataset} requires features not supplied "
                        f"by this transaction: {', '.join(missing[:8])}"
                    )

                result = predict_fraud_risk(
                    request.transaction,
                    dataset,
                    artifact=artifact,
                )

            predictions.append(
                {
                    **result,
                    "dataset": dataset,
                    "model_file": relative_path,
                    "status": "ok",
                }
            )
        except (FileNotFoundError, ValueError) as exc:
            predictions.append(
                {
                    "dataset": dataset,
                    "model_file": relative_path,
                    "status": "incompatible",
                    "reason": safe_error_detail(exc),
                }
            )

    return {
        "transaction_id": request.transaction.get("transaction_id"),
        "predictions": predictions,
    }


@router.post("/investigation")
def investigate_route(request: InvestigationRequest):
    try:
        result = assess_transaction_fraud(
            request.transaction,
            account_id=request.account_id,
        )
        report = compile_report([result], case_id=request.case_id)
        return {"result": result, "report": report}
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=safe_error_detail(exc),
        ) from exc


@router.post("/rag/query")
def rag_query_route(request: RagQueryRequest):
    from src.services.rag_service import answer_question

    return answer_question(request.question, top_k=request.top_k)


@router.post("/compliance/query")
def compliance_query_route(request: ComplianceQueryRequest):
    return answer_compliance_question(
        request.question,
        top_k=request.top_k,
    )


@router.post(
    "/api/documents",
    response_model=DocumentUploadResponse,
)
async def upload_document_route(file: UploadFile):
    destination_dir = RAW_DATA_ROOT / "uploads"
    destination_dir.mkdir(parents=True, exist_ok=True)

    document_id = str(uuid.uuid4())
    safe_name = Path(file.filename or "upload.bin").name
    destination = destination_dir / f"{document_id}_{safe_name}"

    try:
        destination.write_bytes(await file.read())
        return ingest_document(destination, document_id=document_id)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=safe_error_detail(exc),
        ) from exc
    finally:
        await file.close()


@router.get("/api/overview")
def overview_route(session: Session = Depends(get_db)):
    total_cases = (
        session.scalar(
            select(func.count()).select_from(InvestigationCase)
        )
        or 0
    )
    open_cases = (
        session.scalar(
            select(func.count())
            .select_from(InvestigationCase)
            .where(InvestigationCase.status == "open")
        )
        or 0
    )
    total_transactions = (
        session.scalar(
            select(func.count()).select_from(Transaction)
        )
        or 0
    )

    case_breakdown = dict(
        session.execute(
            select(
                InvestigationCase.severity,
                func.count(),
            ).group_by(InvestigationCase.severity)
        ).all()
    )

    exposure = (
        session.scalar(
            select(func.coalesce(func.sum(Transaction.amount), 0.0))
            .join(
                InvestigationCase,
                InvestigationCase.transaction_id == Transaction.id,
            )
            .where(InvestigationCase.status == "open")
        )
        or 0.0
    )

    monthly_rows = session.execute(
        select(
            func.date_trunc(
                "month", InvestigationCase.created_at
            ).label("month"),
            func.count(),
        )
        .group_by("month")
        .order_by("month")
    ).all()

    monthly_case_trend = [
        {"month": month.strftime("%b %Y"), "count": count}
        for month, count in monthly_rows[-6:]
    ]

    recent_cases = session.scalars(
        select(InvestigationCase)
        .order_by(InvestigationCase.created_at.desc())
        .limit(5)
    ).all()

    return {
        "total_cases": total_cases,
        "open_cases": open_cases,
        "total_transactions": total_transactions,
        "case_breakdown": case_breakdown,
        "exposure_under_review": float(exposure),
        "monthly_case_trend": monthly_case_trend,
        "recent_cases": recent_cases,
    }


@router.get("/api/cases")
def list_cases_route(
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_db),
):
    query = select(InvestigationCase)

    if status_filter:
        query = query.where(
            InvestigationCase.status == status_filter
        )

    if severity:
        query = query.where(
            InvestigationCase.severity == severity
        )

    query = query.offset((page - 1) * page_size).limit(page_size)
    return list(session.scalars(query).all())


@router.get("/api/cases/{case_id}")
def get_case_route(
    case_id: str,
    session: Session = Depends(get_db),
):
    case = session.get(InvestigationCase, case_id)

    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    return case


@router.post(
    "/api/cases",
    status_code=status.HTTP_201_CREATED,
)
def create_case_route(
    request: CaseCreateRequest,
    session: Session = Depends(get_db),
):
    case = InvestigationCase(
        id=str(uuid.uuid4()),
        customer_id=request.customer_id,
        case_type=request.case_type,
        severity="informational",
        summary=request.reason,
        created_at=datetime.now(timezone.utc),
    )

    session.add(case)
    session.commit()
    session.refresh(case)

    try:
        notify_case_created(
            {"id": case.id, "severity": case.severity}
        )
    except Exception:
        # Notification failure should not undo the saved case.
        pass

    return case


@router.get("/api/customers")
def list_customers_route(
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_db),
):
    query = select(Customer)

    if search:
        query = query.where(
            Customer.name.ilike(f"%{search}%")
        )

    query = query.offset((page - 1) * page_size).limit(page_size)
    return list(session.scalars(query).all())


@router.get("/api/customers/{customer_id}")
def get_customer_route(
    customer_id: str,
    session: Session = Depends(get_db),
):
    customer = session.get(Customer, customer_id)

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    return customer
