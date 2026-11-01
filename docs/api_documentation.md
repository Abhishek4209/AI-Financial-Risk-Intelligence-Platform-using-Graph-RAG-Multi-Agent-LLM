# API Documentation
## Overview
The AI Financial Risk Intelligence API is a FastAPI decision-support service for:
- Customer risk analysis
- Credit-risk prediction
- Fraud detection
- Compliance analysis
- Financial document ingestion
- Hybrid RAG queries
- Graph-based investigation
- Explainable report generation
The API must not make autonomous lending, fraud, or legal decisions.
**Base URL:** ‘http://localhost:8000‘
- Swagger UI: ‘GET /docs‘
- ReDoc: ‘GET /redoc‘
- OpenAPI schema: ‘GET /openapi.json‘
## Authentication
Production requests must use:
‘‘‘http
Authorization: Bearer <access-token>
‘‘‘
Expected responses:
- ‘401 Unauthorized‘ -- missing or expired token
- ‘403 Forbidden‘ -- insufficient permissions
Authentication may be disabled only when explicitly configured for local development.
## Common Headers
‘‘‘http
Accept: application/json
Content-Type: application/json
X-Request-ID: <optional-client-request-id>
‘‘‘
Every response should include an ‘X-Request-ID‘ header.
## Health and Readiness
### ‘GET /health‘
Checks whether the API process is running. It does not check external services.
‘‘‘json
{
  "status": "ok",
  "service": "financial-risk-api",
  "version": "0.1.0"
}
‘‘‘
### ‘GET /ready‘
Checks PostgreSQL, Redis, and Neo4j connectivity.
‘‘‘json
{
  "status": "ready",
  "dependencies": {
    "postgres": "ok",
    "redis": "ok",
    "neo4j": "ok"
  }
}
‘‘‘
Return ‘503 Service Unavailable‘ when a required dependency is unavailable.
## Overview and Cases
### ‘GET /api/overview‘
Returns operational case metrics from PostgreSQL and separate PaySim
transaction analytics from the local synthetic CSV dataset. PaySim is read in
100,000-row Pandas chunks, and successful aggregates are cached in process for
up to five minutes. The response includes the aggregate refresh timestamp;
it does not import PaySim rows into PostgreSQL or create investigation cases.

Set ‘PAYSIM_CSV_PATH‘ to select a CSV inside
‘data/raw/Fraud/PaySim Financial Transactions‘. The default is
‘PS_20174392719_1491204439457_log.csv‘. The API does not accept a filesystem
path from clients. Missing or invalid PaySim data is reported in the
‘transaction_analytics.status‘ and ‘transaction_analytics.error‘ fields while
PostgreSQL case metrics remain available.

‘total_transactions‘ remains the operational PostgreSQL transaction count for
backwards compatibility. Dataset-level counts and fraud measures are nested
under ‘transaction_analytics‘.
‘‘‘json
{
  "total_cases": 2,
  "open_cases": 1,
  "total_transactions": 25,
  "transaction_analytics": {
    "source": "PaySim",
    "is_synthetic": true,
    "status": "available",
    "total_transactions": 2,
    "total_amount": 150.0,
    "fraud_transaction_count": 1,
    "fraud_transaction_rate": 0.5,
    "fraud_transaction_amount": 100.0,
    "transaction_type_breakdown": {
      "PAYMENT": 1,
      "TRANSFER": 1
    },
    "refreshed_at": "2026-11-01T10:00:00+00:00",
    "cache_ttl_seconds": 300
  },
  "exposure_under_review": 100.0,
  "case_breakdown": {
    "high": 1,
    "informational": 1
  },
  "monthly_case_trend": [
    { "month": "Oct 2026", "count": 2 }
  ],
  "recent_cases": []
}
‘‘‘
The values above are illustrative and are not the current PaySim dataset totals.
Operational exposure sums each PostgreSQL transaction linked to at least one
open case once, even when multiple open cases reference that transaction.
### ‘GET /api/cases‘
Lists risk cases.
Supported query parameters:
- ‘status‘
- ‘severity‘
- ‘owner‘
- ‘page‘
- ‘page_size‘
### ‘GET /api/cases/{case_id}‘
Returns case details, risk explanations, evidence, owner, and activity history.
### ‘POST /api/cases‘
Creates a case for a customer, transaction, document, or manual investigation.
‘‘‘json
{
  "customer_id": "customer_123",
  "case_type": "credit_review",
  "reason": "Debt service coverage ratio declined"
}
‘‘‘
## Customers
### ‘GET /api/customers‘
Lists customers with pagination and optional search.
### ‘GET /api/customers/{customer_id}‘
Returns:
- Customer profile
- Loans and accounts
- Financial exposure
- Risk history
- Associated cases
- Linked documents
### ‘POST /api/customers‘
Creates a customer in the workspace.
‘‘‘json
{
  "name": "Ada Lovelace",
  "segment": "Retail"
}
‘‘‘
## Documents
### ‘POST /api/documents‘
Uploads a PDF, DOCX, XLSX, CSV, or image for asynchronous ingestion.
Request content type:
‘‘‘http
Content-Type: multipart/form-data
‘‘‘
Example response:
‘‘‘json
{
  "document_id": "doc_123",
  "status": "queued",
  "job_id": "job_456"
}
‘‘‘
The ingestion pipeline may perform:
1. File validation
2. Text or table extraction
3. OCR
4. Cleaning
5. Chunking
6. Metadata creation
7. Embedding
8. Vector and graph indexing
### ‘GET /api/documents/{document_id}‘
Returns document metadata and processing status.
‘‘‘json
{
  "document_id": "doc_123",
  "status": "indexed",
  "document_name": "annual_report.pdf",
  "chunks_indexed": 124,
  "vector_indexed": true,
  "graph_indexed": true
}
‘‘‘
### ‘GET /api/documents/{document_id}/citations‘
Returns citation metadata, including:
- Document ID
- Document name
- Page number
- Section
- Chunk ID
- Source
## Risk and Fraud Analysis
### ‘POST /api/risk/predict‘
Runs credit-risk inference for a customer or loan.
‘‘‘json
{
  "customer_id": "customer_123",
  "loan_id": "loan_456"
}
‘‘‘
Example response:
‘‘‘json
{
  "prediction": "high_risk",
  "default_probability": 0.78,
  "risk_level": "HIGH",
  "model_name": "credit_risk_model",
  "model_version": "credit_model_v1.0.0",
  "top_risk_factors": [
    {
      "feature": "debt_to_income",
      "impact": 0.31
    }
  ],
  "human_review_required": true
}
‘‘‘
### ‘POST /api/fraud/analyze‘
Analyzes a transaction or customer transaction history.
‘‘‘json
{
  "transaction_id": "transaction_123"
}
‘‘‘
Example response:
‘‘‘json
{
  "fraud_probability": 0.94,
  "risk_level": "HIGH",
  "model_name": "fraud_detection_model",
  "model_version": "fraud_model_v1.0.0",
  "signals": [
    "new_device",
    "unusual_location",
    "unusual_transaction_amount"
  ],
  "human_review_required": true
}
‘‘‘
A fraud score is an investigation signal, not proof of fraud.
## General Analysis
### ‘POST /api/analysis‘
Starts an asynchronous analysis.
‘‘‘json
{
  "subject_type": "customer",
  "subject_id": "customer_123",
  "analysis_types": [
    "credit_risk",
    "fraud",
    "compliance",
    "finance"
  ],
  "include_sources": true
}
‘‘‘
Example response:
‘‘‘json
{
  "analysis_id": "analysis_123",
  "status": "queued",
  "job_id": "job_456"
}
‘‘‘
### ‘GET /api/analysis/{analysis_id}‘
Returns analysis status and completed findings.
Results must distinguish:
1. ML predictions
2. Deterministic calculations
3. Retrieved evidence
4. LLM-generated explanations
5. Recommended human-review actions
## RAG and Graph Queries
### ‘POST /api/rag/query‘
Queries trusted financial and regulatory documents using basic or hybrid retrieval.
Responses include `question`, `answer`, `evidence`, `grounding_status`, and
`limitations`, alongside the compatibility fields `sources`, `grounded`, and
`evidence_sufficient`. Evidence entries include the available document name,
section, page, and retrieved text. If no directly relevant evidence supports an
answer, `answer` is `Insufficient evidence.` and `grounding_status` is
`Insufficient evidence`.
‘‘‘json
{
  "question": "What are the applicable KYC requirements?",
  "include_citations": true,
  "top_k": 5
}
‘‘‘
### ‘POST /api/query‘
Runs a question through the supervisor, hybrid retrieval, and graph retrieval when appropriate.
‘‘‘json
{
  "question": "What changed in the customer’s credit risk this quarter?",
  "customer_id": "customer_123",
  "include_citations": true
}
‘‘‘
Example response:
‘‘‘json
{
  "answer": "The available evidence indicates increased credit risk due to ...",
  "findings": [],
  "sources": [
    {
      "document_name": "RBI_KYC.pdf",
      "page_number": 15,
      "chunk_id": "chunk_001"
    }
  ],
  "confidence": "medium",
  "human_review_required": true
}
‘‘‘
If reliable evidence is unavailable, return:
‘‘‘text
Insufficient evidence from the available sources.
‘‘‘
Citations must never be fabricated.
## Reports
### ‘POST /api/reports‘
Generates an executive, risk, fraud, finance, or regulatory report from completed analysis.
‘‘‘json
{
  "analysis_id": "analysis_123",
  "report_type": "risk",
  "include_sources": true
}
‘‘‘
### ‘GET /api/reports/{report_id}‘
Returns report status, metadata, findings, citations, and rendered report location.
Reports should contain:
1. Executive summary
2. Subject profile
3. Credit risk
4. Fraud risk
5. Compliance risk
6. Financial analysis
7. Model explanations
8. Retrieved evidence
9. Overall risk assessment
10. Human-review recommendations
## Error Format
All errors should use this structure:
‘‘‘json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The requested analysis type is not supported.",
    "request_id": "req_123",
    "details": []
  }
}
‘‘‘
Expected status codes:
- ‘400‘ -- malformed request
- ‘401‘ -- unauthenticated request
- ‘403‘ -- forbidden request
- ‘404‘ -- resource not found
- ‘409‘ -- state conflict
- ‘422‘ -- validation error
- ‘500‘ -- unexpected server error
- ‘503‘ -- dependency unavailable
API responses must not expose stack traces, secrets, credentials, or unnecessary customer PII.
## Implementation Rules
- API routes belong in ‘src/api/‘.
- Business workflows belong in ‘src/services/‘.
- Database access belongs in ‘src/database/‘.
- ML inference belongs in ‘src/ml_models/‘.
- RAG logic belongs in retrieval, embedding, vector-store, graph, and LLM modules.
- Long-running ingestion and analysis tasks should use Celery and Redis.
- Predictions must include model and feature versions where applicable.
- Financial decisions require human review.
- Deterministic calculations must not be delegated to the LLM.
## Local Development
From the repository root:
‘‘‘powershell
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
‘‘‘
Using Docker:
‘‘‘powershell
docker compose up --build
‘‘‘
The frontend should use:
‘‘‘dotenv
VITE_API_URL=http://localhost:8000
‘‘‘
