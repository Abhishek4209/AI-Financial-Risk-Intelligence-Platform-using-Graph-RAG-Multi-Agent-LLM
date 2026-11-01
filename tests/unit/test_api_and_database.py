from __future__ import annotations

import asyncio
import importlib
import io
import sys
import types
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile
from starlette.responses import Response
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.api import auth, middleware, schemas
from src.database import models, postgres, redis as redis_module
from src.services.paysim_analytics import PaySimAnalyticsError


routes = importlib.import_module("src.api.routes")
api_main = importlib.import_module("src.api.main")


def _install_module(monkeypatch, name: str, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)


def test_authentication_tokens_roles_and_disabled_mode(monkeypatch):
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        auth._secret_key()
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-secret")

    class JWTError(Exception):
        pass

    jwt = SimpleNamespace(
        encode=lambda payload, secret, algorithm: f"{payload['sub']}:{secret}:{algorithm}",
        decode=lambda token, secret, algorithms: (
            {"sub": "analyst", "role": "analyst"}
            if token == "valid"
            else (_ for _ in ()).throw(JWTError("bad token"))
        ),
    )
    _install_module(monkeypatch, "jose", jwt=jwt, JWTError=JWTError)
    assert auth.create_access_token("analyst").startswith("analyst:unit-test-secret:HS256")
    assert auth.decode_access_token("valid")["sub"] == "analyst"
    with pytest.raises(HTTPException) as invalid:
        auth.decode_access_token("invalid")
    assert invalid.value.status_code == 401

    monkeypatch.delenv("AUTH_DISABLED", raising=False)
    with pytest.raises(HTTPException) as missing:
        auth.get_current_user(None)
    assert missing.value.status_code == 401
    credentials = SimpleNamespace(credentials="valid")
    assert auth.get_current_user(credentials)["role"] == "analyst"
    monkeypatch.setenv("AUTH_DISABLED", "TRUE")
    assert auth.get_current_user(None)["sub"] == "local-dev-user"
    assert auth.require_role("analyst")(user={"role": "analyst"})["role"] == "analyst"
    with pytest.raises(HTTPException) as denied:
        auth.require_role("admin")(user={"role": "analyst"})
    assert denied.value.status_code == 403


def test_request_id_middleware_success_and_error_paths():
    async def exercise():
        middleware_instance = middleware.RequestIDMiddleware(lambda scope, receive, send: None)
        request = SimpleNamespace(
            headers={"X-Request-ID": "request-1"},
            state=SimpleNamespace(),
        )

        async def successful(_request):
            return Response("ok")

        response = await middleware_instance.dispatch(request, successful)
        assert response.headers["X-Request-ID"] == "request-1"
        assert request.state.request_id == "request-1"

        second_request = SimpleNamespace(headers={}, state=SimpleNamespace())

        async def failing(_request):
            raise RuntimeError("traceback details\nprivate line")

        error_response = await middleware_instance.dispatch(second_request, failing)
        assert error_response.status_code == 500
        assert error_response.headers["X-Request-ID"]
        assert b"traceback details" in error_response.body
        assert b"private line" not in error_response.body

    asyncio.run(exercise())
    assert middleware.safe_error_detail(ValueError("first line\nsecond")) == "first line"


def test_api_schema_validation_and_defaults():
    assert schemas.HealthResponse().service == "financial-risk-api"
    assert schemas.ReadyResponse(status="ready", dependencies={"redis": "ok"}).status == "ready"
    credit = schemas.CreditRiskRequest(dataset="taiwan", applicant={"AGE": 20})
    assert credit.applicant["AGE"] == 20
    with pytest.raises(Exception):
        schemas.CreditRiskRequest(dataset="other", applicant={})
    assert schemas.CreditRiskResponse(
        dataset="taiwan",
        default_probability=0.2,
        risk_band="LOW",
        recommended_for_review=False,
        interpretation="support",
    ).shap_drivers == []
    assert schemas.FraudRequest(transaction={}).account_id is None
    assert schemas.FraudResponse(model={}, report="report", human_review_required=True).evidence == []
    assert schemas.FraudModelsResponse(predictions=[]).predictions == []
    assert schemas.InvestigationRequest(transaction={}).case_id is None
    with pytest.raises(Exception):
        schemas.RagQueryRequest(question="q", top_k=0)
    with pytest.raises(Exception):
        schemas.ComplianceQueryRequest(question="q", top_k=21)
    assert schemas.RagQueryResponse(
        question="q",
        answer="x",
        grounding_status="Grounded",
        grounded=True,
    ).evidence_sufficient
    assert schemas.DocumentUploadResponse(
        document_id="d",
        status="indexed",
        document_name="a.pdf",
        chunks_indexed=1,
        vector_indexed=True,
    ).vector_indexed
    case = schemas.CaseCreateRequest(customer_id="c", case_type="fraud", reason="alert")
    assert case.reason == "alert"
    assert schemas.ErrorResponse(detail="safe").detail == "safe"


def test_api_prediction_and_agent_routes(monkeypatch):
    request = schemas.CreditRiskRequest(dataset="taiwan", applicant={"AGE": 30})
    monkeypatch.setattr(
        routes,
        "assess_credit_risk",
        lambda applicant, dataset: {
            "prediction": {"dataset": dataset, "default_probability": 0.1},
            "shap_drivers": [{"feature": "AGE"}],
        },
    )
    assert routes.predict_credit_risk_route(request)["shap_drivers"] == [
        {"feature": "AGE"}
    ]
    monkeypatch.setattr(
        routes,
        "assess_credit_risk",
        lambda *args: (_ for _ in ()).throw(ValueError("invalid input")),
    )
    with pytest.raises(HTTPException) as credit_error:
        routes.predict_credit_risk_route(request)
    assert credit_error.value.status_code == 400

    fraud_request = schemas.FraudRequest(transaction={"amount": 1}, account_id="A1")
    monkeypatch.setattr(
        routes,
        "assess_transaction_fraud",
        lambda transaction, account_id: {"transaction": transaction, "account": account_id},
    )
    assert routes.predict_fraud_route(fraud_request)["account"] == "A1"
    monkeypatch.setattr(
        routes,
        "assess_transaction_fraud",
        lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError("missing")),
    )
    with pytest.raises(HTTPException) as fraud_error:
        routes.predict_fraud_route(fraud_request)
    assert fraud_error.value.status_code == 400

    monkeypatch.setattr(routes, "FRAUD_MODEL_FILES", {
        "paysim": "paysim.pkl",
        "missing": "missing.pkl",
        "custom": "custom.pkl",
    })
    monkeypatch.setattr(routes, "predict_paysim_fraud_risk", lambda transaction: {"fraud_risk_score": 0.9})
    monkeypatch.setattr(
        routes,
        "load_fraud_artifact",
        lambda dataset: {"feature_columns": ["required"]},
    )
    monkeypatch.setattr(
        routes,
        "predict_fraud_risk",
        lambda transaction, dataset, artifact: {"fraud_risk_score": 0.1},
    )
    predictions = routes.predict_fraud_models_route(
        schemas.FraudRequest(transaction={"transaction_id": "T", "required": 2})
    )
    assert [item["status"] for item in predictions["predictions"]] == [
        "ok", "ok", "ok"
    ]

    monkeypatch.setattr(
        routes,
        "load_fraud_artifact",
        lambda dataset: (
            {"feature_columns": ["required"]}
            if dataset == "custom"
            else (_ for _ in ()).throw(FileNotFoundError("artifact missing"))
        ),
    )
    predictions = routes.predict_fraud_models_route(
        schemas.FraudRequest(transaction={"transaction_id": "T"})
    )
    assert [item["status"] for item in predictions["predictions"]] == [
        "ok", "incompatible", "incompatible"
    ]
    assert "required" in predictions["predictions"][2]["reason"]

    monkeypatch.setattr(routes, "assess_transaction_fraud", lambda *args, **kwargs: {"agent": "fraud"})
    monkeypatch.setattr(routes, "compile_report", lambda results, case_id=None: {"case": case_id})
    investigation = routes.investigate_route(
        schemas.InvestigationRequest(transaction={}, account_id="A", case_id="C")
    )
    assert investigation["report"] == {"case": "C"}
    monkeypatch.setattr(
        routes,
        "assess_transaction_fraud",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("bad")),
    )
    with pytest.raises(HTTPException):
        routes.investigate_route(schemas.InvestigationRequest(transaction={}))

    rag_service = importlib.import_module("src.services.rag_service")
    monkeypatch.setattr(rag_service, "answer_question", lambda question, top_k: {"answer": question})
    assert routes.rag_query_route(schemas.RagQueryRequest(question="query"))["answer"] == "query"
    monkeypatch.setattr(routes, "answer_compliance_question", lambda question, top_k: {"answer": "policy"})
    assert routes.compliance_query_route(
        schemas.ComplianceQueryRequest(question="policy")
    )["answer"] == "policy"


def test_document_upload_uses_isolated_path_and_closes_file(monkeypatch, tmp_path):
    monkeypatch.setattr(routes, "RAW_DATA_ROOT", tmp_path)
    monkeypatch.setattr(routes.uuid, "uuid4", lambda: "fixed-id")
    ingested = []
    monkeypatch.setattr(
        routes,
        "ingest_document",
        lambda path, document_id: ingested.append((path, document_id)) or {
            "document_id": document_id,
            "status": "indexed",
            "document_name": path.name,
            "chunks_indexed": 1,
            "vector_indexed": True,
        },
    )
    upload = UploadFile(filename="../policy.pdf", file=io.BytesIO(b"safe test content"))
    response = asyncio.run(routes.upload_document_route(upload))
    assert response["document_id"] == "fixed-id"
    path, document_id = ingested[0]
    assert path.parent == tmp_path / "uploads"
    assert path.name == "fixed-id_policy.pdf"
    assert path.read_bytes() == b"safe test content"
    assert document_id == "fixed-id"
    assert upload.file.closed

    failed_upload = UploadFile(filename=None, file=io.BytesIO(b"bad"))
    monkeypatch.setattr(
        routes,
        "ingest_document",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("invalid upload")),
    )
    with pytest.raises(HTTPException) as error:
        asyncio.run(routes.upload_document_route(failed_upload))
    assert error.value.status_code == 400
    assert failed_upload.file.closed


class FakeResult:
    def __init__(self, rows=()):
        self.rows = rows

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self):
        self.scalar_values = iter([3, 2, 8, 125.5])
        self.execute_values = iter([
            FakeResult([("high", 2), ("low", 1)]),
            FakeResult([(datetime(2025, 1, 1, tzinfo=timezone.utc), 3)]),
        ])
        self.recent = [SimpleNamespace(id="C1")]
        self.added = []

    def scalar(self, query):
        return next(self.scalar_values)

    def execute(self, query):
        return next(self.execute_values)

    def scalars(self, query):
        return SimpleNamespace(all=lambda: self.recent)

    def get(self, model, key):
        return SimpleNamespace(id=key) if key == "found" else None

    def add(self, value):
        self.added.append(value)

    def commit(self):
        return None

    def refresh(self, value):
        return None


def test_case_customer_overview_and_crud_routes(monkeypatch):
    session = FakeSession()
    paysim_analytics = {
        "source": "PaySim",
        "is_synthetic": True,
        "status": "available",
        "total_transactions": 2,
        "fraud_transaction_count": 1,
        "fraud_transaction_rate": 0.5,
    }
    monkeypatch.setattr(
        routes,
        "get_paysim_analytics",
        lambda: paysim_analytics,
    )
    overview = routes.overview_route(session)
    assert overview["total_cases"] == 3
    assert overview["open_cases"] == 2
    assert overview["total_transactions"] == 8
    assert overview["transaction_analytics"] == paysim_analytics
    assert overview["exposure_under_review"] == 125.5
    assert overview["case_breakdown"] == {"high": 2, "low": 1}
    assert overview["monthly_case_trend"] == [{"month": "Jan 2025", "count": 3}]
    assert routes.list_cases_route(None, None, 2, 10, session) == session.recent
    assert routes.list_cases_route("open", "high", 1, 5, session) == session.recent
    assert routes.get_case_route("found", session).id == "found"
    with pytest.raises(HTTPException) as missing_case:
        routes.get_case_route("absent", session)
    assert missing_case.value.status_code == 404

    monkeypatch.setattr(routes, "notify_case_created", lambda case: None)
    request = schemas.CaseCreateRequest(
        customer_id="C1", case_type="fraud", reason="suspicious activity"
    )
    created = routes.create_case_route(request, session)
    assert created.customer_id == "C1"
    assert created.severity == "informational"
    assert session.added[-1] is created
    monkeypatch.setattr(
        routes,
        "notify_case_created",
        lambda case: (_ for _ in ()).throw(RuntimeError("webhook unavailable")),
    )
    assert routes.create_case_route(request, session).case_type == "fraud"

    assert routes.list_customers_route("Ada", 1, 10, session) == session.recent
    assert routes.list_customers_route(None, 1, 10, session) == session.recent
    assert routes.get_customer_route("found", session).id == "found"
    with pytest.raises(HTTPException) as missing_customer:
        routes.get_customer_route("absent", session)
    assert missing_customer.value.status_code == 404

    customer_request = schemas.CustomerCreateRequest(
        name="  Ada Lovelace  ", segment="  Retail  "
    )
    customer = routes.create_customer_route(customer_request, session)
    assert customer.name == "Ada Lovelace"
    assert customer.segment == "Retail"
    assert customer.id
    assert session.added[-1] is customer
    with pytest.raises(HTTPException) as blank_customer:
        routes.create_customer_route(
            schemas.CustomerCreateRequest(name="   "),
            session,
        )
    assert blank_customer.value.status_code == 422


def test_overview_retains_postgres_metrics_when_paysim_is_unavailable(
    monkeypatch,
):
    session = FakeSession()

    def unavailable():
        raise PaySimAnalyticsError(
            "The configured PaySim CSV file is missing."
        )

    monkeypatch.setattr(routes, "get_paysim_analytics", unavailable)

    overview = routes.overview_route(session)

    assert overview["total_cases"] == 3
    assert overview["open_cases"] == 2
    assert overview["total_transactions"] == 8
    assert overview["case_breakdown"] == {"high": 2, "low": 1}
    assert overview["transaction_analytics"]["status"] == "unavailable"
    assert "missing" in overview["transaction_analytics"]["error"]


def test_database_models_and_sqlite_relationships():
    engine = create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(engine)
    with Session(engine) as session:
        user = models.User(email="analyst@example.test", hashed_password="hash")
        customer = models.Customer(id="C1", name="Test Customer")
        account = models.Account(
            id="A1", customer=customer, account_type="checking", balance=100
        )
        loan = models.Loan(
            id="L1", customer=customer, principal_amount=50
        )
        transaction = models.Transaction(
            id="T1",
            customer_id="C1",
            from_account_id="A1",
            amount=10,
            transaction_type="TRANSFER",
            occurred_at=datetime.now(timezone.utc),
        )
        document = models.Document(file_name="policy.pdf")
        prediction = models.Prediction(
            task="fraud",
            model_version="v1",
            probability=0.9,
            threshold=0.5,
            transaction_id="T1",
        )
        case = models.InvestigationCase(
            case_type="fraud",
            severity="high",
            summary="Review transaction",
            customer_id="C1",
            transaction_id="T1",
        )
        report = models.Report(case_id=case.id, report_type="investigation", content="Report")
        message = models.ChatMessage(
            session_id="S1", role="user", content="Analyze this"
        )
        audit = models.AuditLog(event_type="case_created", actor="analyst")
        session.add_all([
            user, customer, account, loan, transaction, document,
            prediction, case, report, message, audit,
        ])
        session.commit()
        assert session.query(models.Account).one().customer.name == "Test Customer"
        assert session.query(models.Loan).one().status == "active"
        assert session.query(models.Document).one().status == "queued"
        assert session.query(models.Prediction).one().probability == 0.9
        assert session.query(models.InvestigationCase).one().status == "open"
        assert session.query(models.ChatMessage).one().sources == []
        assert session.query(models.AuditLog).one().details == {}
        assert user.created_at is not None
        assert len(models._uuid()) == 36
        assert models._now().tzinfo is not None


def test_postgres_session_management_with_mocked_engine(monkeypatch):
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        postgres.database_url()
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
    assert postgres.database_url() == "postgresql+psycopg2://user:pass@localhost/db"
    assert postgres._normalize_url("sqlite:///:memory:") == "sqlite:///:memory:"

    created = []
    fake_engine = object()
    monkeypatch.setattr(
        postgres,
        "create_engine",
        lambda url, pool_pre_ping: created.append((url, pool_pre_ping)) or fake_engine,
    )
    postgres.get_engine.cache_clear()
    postgres._session_factory.cache_clear()
    try:
        assert postgres.get_engine() is fake_engine
        assert postgres.get_engine() is fake_engine
        assert created == [("postgresql+psycopg2://user:pass@localhost/db", True)]
        factory = postgres._session_factory()
        assert factory.kw["bind"] is fake_engine
        created_all = []
        monkeypatch.setattr(
            postgres.Base.metadata,
            "create_all",
            lambda engine: created_all.append(engine),
        )
        postgres.init_db()
        assert created_all == [fake_engine]
    finally:
        postgres.get_engine.cache_clear()
        postgres._session_factory.cache_clear()

    closed = []
    session = SimpleNamespace(close=lambda: closed.append(True))
    monkeypatch.setattr(postgres, "get_session", lambda: session)
    generator = postgres.get_db()
    assert next(generator) is session
    with pytest.raises(StopIteration):
        next(generator)
    assert closed == [True]


def test_redis_cache_rate_limit_and_client_configuration(monkeypatch):
    class Client:
        def __init__(self):
            self.values = {}
            self.count = 0
            self.expiries = []

        def get(self, key):
            return self.values.get(key)

        def set(self, key, value, ex=None):
            self.values[key] = value
            self.expiries.append((key, ex))

        def delete(self, key):
            self.values.pop(key, None)

        def incr(self, key):
            self.count += 1
            return self.count

        def expire(self, key, seconds):
            self.expiries.append((key, seconds))

    client = Client()
    calls = []
    redis_package = types.ModuleType("redis")
    redis_package.Redis = SimpleNamespace(
        from_url=lambda url, decode_responses: calls.append((url, decode_responses)) or client
    )
    monkeypatch.setitem(sys.modules, "redis", redis_package)
    monkeypatch.setenv("REDIS_URL", "redis://test.local/3")
    redis_module.get_redis_client.cache_clear()
    try:
        assert redis_module.get_redis_client() is client
        assert calls == [("redis://test.local/3", True)]
        redis_module.cache_set("key", {"count": 1}, ttl_seconds=20)
        assert redis_module.cache_get("key") == {"count": 1}
        assert redis_module.cache_get("missing") is None
        redis_module.cache_delete("key")
        assert redis_module.cache_get("key") is None
        assert redis_module.check_rate_limit("budget", max_requests=1, window_seconds=30)
        assert not redis_module.check_rate_limit("budget", max_requests=1, window_seconds=30)
        assert client.expiries[-1] == ("budget", 30)
        with pytest.raises(ValueError, match="must be positive"):
            redis_module.check_rate_limit("budget", max_requests=0, window_seconds=1)
    finally:
        redis_module.get_redis_client.cache_clear()


def test_api_health_readiness_and_dependency_checks(monkeypatch):
    check_postgres = api_main._check_postgres
    check_neo4j = api_main._check_neo4j
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://one.test, ,http://two.test")
    assert api_main._allowed_origins() == ["http://one.test", "http://two.test"]
    monkeypatch.setattr(api_main, "_check_postgres", lambda: "ok")
    monkeypatch.setattr(api_main, "_check_redis", lambda: "ok")
    monkeypatch.setattr(api_main, "_check_neo4j", lambda: "ok")
    client = TestClient(api_main.create_app())
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/ready").json()["status"] == "ready"
    monkeypatch.setattr(api_main, "_check_redis", lambda: "unavailable")
    not_ready = client.get("/ready")
    assert not_ready.status_code == 503
    assert not_ready.json()["detail"]["redis"] == "unavailable"

    monkeypatch.setattr(api_main, "_check_postgres", check_postgres)
    monkeypatch.setattr(api_main, "_check_neo4j", check_neo4j)
    monkeypatch.setattr(
        postgres,
        "get_engine",
        lambda: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    assert api_main._check_postgres() == "unavailable"
    redis_module.get_redis_client.cache_clear()
    monkeypatch.setattr(
        redis_module,
        "get_redis_client",
        lambda: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    assert api_main._check_redis() == "unavailable"
    graph_loader = importlib.import_module("src.graph_rag.neo4j_loader")
    monkeypatch.setattr(graph_loader, "verify_connectivity", lambda: False)
    assert api_main._check_neo4j() == "unavailable"
