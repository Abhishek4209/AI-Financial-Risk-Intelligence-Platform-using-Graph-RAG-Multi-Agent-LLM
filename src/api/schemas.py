"""Pydantic request/response schemas, matching docs/api_documentation.md."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field



class HealthResponse(BaseModel):
        status: str = "ok"
        service: str = "financial-risk-api"
        version: str = "0.1.0"



class ReadyResponse(BaseModel):
        status: str
        dependencies: dict[str, str]



class CreditRiskRequest(BaseModel):
        dataset: Literal["taiwan", "lending_club"]
        applicant: dict[str, Any]



class CreditRiskResponse(BaseModel):
        dataset: str
        default_probability: float
        risk_band: str
        recommended_for_review: bool
        interpretation: str
        shap_drivers: list[dict[str, Any]] = Field(default_factory=list)



class FraudRequest(BaseModel):
        transaction: dict[str, Any]
        account_id: str | None = None



class FraudResponse(BaseModel):
        transaction_id: str | None = None
        model: dict[str, Any]
        shap_drivers: list[dict[str, Any]] = Field(default_factory=list)
        evidence: list[dict[str, Any]] = Field(default_factory=list)
        report: str
        human_review_required: bool



class InvestigationRequest(BaseModel):
        transaction: dict[str, Any]
        account_id: str | None = None
        case_id: str | None = None



class RagQueryRequest(BaseModel):
        question: str
        top_k: int = Field(default=5, ge=1, le=20)



class RagQueryResponse(BaseModel):
        answer: str
        sources: list[str] = Field(default_factory=list)
        grounded: bool
        evidence_sufficient: bool = True



class ComplianceQueryRequest(BaseModel):
        question: str

        top_k: int = Field(default=5, ge=1, le=20)



class DocumentUploadResponse(BaseModel):
        document_id: str
        status: str
        document_name: str
        chunks_indexed: int
        vector_indexed: bool



class CaseCreateRequest(BaseModel):
        customer_id: str
        case_type: str
        reason: str



class CaseResponse(BaseModel):
        id: str
        customer_id: str | None = None
        case_type: str
        status: str
        severity: str
        summary: str
        created_at: datetime



class ErrorResponse(BaseModel):
        detail: str
