# API Documentation

## Overview

The AI Financial Risk Intelligence API is designed as a FastAPI service for document ingestion, portfolio risk analysis, fraud detection, compliance checks, and report generation.

The backend implementation is currently a scaffold. The endpoint contracts below define the intended interface for the frontend and future service implementations.

**Base URL:** `http://localhost:8000`

**Interactive documentation:**

- Swagger UI: `GET /docs`
- ReDoc: `GET /redoc`
- OpenAPI schema: `GET /openapi.json`

## Authentication

Production requests should use a bearer token:

```http
Authorization: Bearer <access-token>
```

The authentication layer should reject missing or expired tokens with `401 Unauthorized` and insufficient permissions with `403 Forbidden`. Local development may run without authentication only when the API is explicitly configured for development mode.

## Common Headers

```http
Accept: application/json
Content-Type: application/json
X-Request-ID: <optional-client-request-id>
```

The server should return an `X-Request-ID` value on every response so requests can be traced through logs and asynchronous jobs.

## Health and Readiness

### `GET /health`

Returns the process health status without checking external dependencies.

```json
{
	"status": "ok",
	"service": "financial-risk-api",
	"version": "0.1.0"
}
```

### `GET /ready`

Checks whether the API can reach its configured PostgreSQL, Redis, and Neo4j services.

```json
{
	"status": "ready",
	"dependencies": {
		"postgres": "ok",
		"redis": "ok",
		"neo4j": "ok"
	}
}
```

## Overview and Portfolio

### `GET /api/overview`

Returns the dashboard summary consumed by the frontend.

Example response:

```json
{
	"portfolioRiskScore": 68,
	"exposureUnderReview": 24.8,
	"exposureThresholdPercent": 68,
	"openCases": 42,
	"caseBreakdown": { "high": 8, "medium": 19, "low": 15 },
	"trend": [62, 58, 61, 49, 43, 42.6],
	"distribution": { "low": 48.2, "medium": 24.9, "high": 13.3 },
	"cases": []
}
```

### `GET /api/cases`

Returns risk cases. Supported query parameters should include `status`, `severity`, `owner`, `page`, and `page_size`.

### `GET /api/cases/{case_id}`

Returns a case, its score explanation, evidence, assigned owner, and activity history.

### `POST /api/cases`

Creates a case from a customer, transaction, document, or manually supplied investigation reason.

```json
{
	"customer_id": "customer_123",
	"case_type": "credit_review",
	"reason": "Debt service coverage ratio declined"
}
```

## Customers

### `GET /api/customers`

Lists portfolio customers with pagination and optional search.

### `GET /api/customers/{customer_id}`

Returns customer profile, exposure, risk history, associated cases, and linked documents.

## Documents

### `POST /api/documents`

Uploads a PDF, DOCX, XLSX, CSV, or image file for ingestion. The endpoint should use `multipart/form-data` and return an ingestion job.

```json
{
	"document_id": "doc_123",
	"status": "queued",
	"job_id": "job_456"
}
```

### `GET /api/documents/{document_id}`

Returns document metadata, processing status, extracted text summary, and indexing status.

### `GET /api/documents/{document_id}/citations`

Returns source locations that can be attached to generated answers and reports.

## Analysis

### `POST /api/analysis`

Starts a risk analysis for a customer, case, transaction, or set of documents.

```json
{
	"subject_type": "customer",
	"subject_id": "customer_123",
	"analysis_types": ["credit_risk", "fraud", "compliance"],
	"include_sources": true
}
```

### `GET /api/analysis/{analysis_id}`

Returns analysis status and the completed findings. Long-running work should be processed asynchronously through Celery and Redis.

### `POST /api/query`

Runs a question through hybrid retrieval, graph retrieval, and the multi-agent supervisor.

```json
{
	"question": "What changed in Northstar Logistics' credit risk this quarter?",
	"customer_id": "customer_123",
	"include_citations": true
}
```

## Reports

### `POST /api/reports`

Generates an executive, risk, fraud, or regulatory report from completed analysis results.

### `GET /api/reports/{report_id}`

Returns report metadata, generation status, and the rendered report location.

## Error Format

Errors should use a consistent response shape:

```json
{
	"error": {
		"code": "VALIDATION_ERROR",
		"message": "The requested analysis type is not supported.",
		"request_id": "req_123",
		"details": []
	}
}
```

Expected status codes include `400` for malformed input, `401` for missing authentication, `403` for forbidden access, `404` for missing resources, `409` for state conflicts, `422` for validation errors, and `500` for unexpected server failures.

## Local Development

Run the API from the repository root after implementing `src/api/main.py`:

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

The frontend uses `VITE_API_URL` to select the API host. Its local default is `http://localhost:8000`.
