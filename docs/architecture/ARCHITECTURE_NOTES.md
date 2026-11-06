# Verified Working Architecture

**Project:** AI Financial Risk Intelligence Platform using Graph RAG and multi-agent utilities  
**Evidence basis:** the checked-out source and runtime files, with README/context material used as secondary context.  
**Verification status:** Source-verified from repository files. The application was not launched, so end-to-end runtime behavior was not verified.  
**Diagram files:** [PNG](./project_working_architecture.png), [SVG](./project_working_architecture.svg), [Mermaid](./project_working_architecture.mmd).

## Status key

- **Active in source:** A workflow is wired to an API route in the inspected code. This does not claim that it was launched or exercised end to end.
- **Optional / conditional:** A provider or integration is selected by environment/configuration, or invoked only when its required input or service is available.
- **Not active / unverified as an active workflow:** The codebase contains references, dependencies, helpers, or artifacts, but no active request workflow for the capability was verified.

## Executive summary

The verified application is a React/Vite dashboard backed by a FastAPI API. The browser calls separate endpoints for credit scoring, fraud scoring, fraud investigation, compliance/document Q&A, document upload, and operational dashboard data. These are **distinct request paths**, not a single universal multi-agent pipeline.

The active ML paths are Taiwan/Lending Club credit-risk scoring and PaySim/IEEE-CIS fraud scoring. A separate PaySim investigation path adds SHAP, regulatory vector retrieval, and an analyst-facing Markdown report. Compliance Q&A uses vector RAG with query expansion, heuristic relevance checks, reranking, and guarded answer generation. Neo4j relationship evidence is optional and is only attached to the investigation response when an account ID is supplied; it is not fused into the RAG prompt or the investigation report.

## Step-by-step execution flow

### 1. User input and HTTP boundary

1. The analyst uses the React/Vite Ledgerline dashboard.
2. `frontend/src/services/riskApi.js` sends JSON or multipart requests to FastAPI. In local Vite development, the API base can be same-origin; otherwise `VITE_API_URL` or a hostname-based port-8000 URL is used.
3. `src/api/main.py` creates the FastAPI app, installs CORS and request-ID middleware, exposes `/health` and `/ready`, and mounts the business router.
4. Business routes have a shared bearer-token dependency (`src/api/auth.py`). `AUTH_DISABLED=true` bypasses token validation for local development. The frontend client does not attach a bearer token, so local use depends on that bypass or an external authentication arrangement.

### 2. Credit-risk scoring

`POST /predict/credit-risk` takes a `dataset` and applicant fields. `src/agents/risk_agent.py` dispatches directly to the credit inference utilities:

1. Taiwan inputs are converted to the expected Taiwan credit feature columns; Lending Club inputs use their own mapped model columns.
2. The matching saved model artifact is loaded (`models/taiwan_credit_default_model.pkl` or `models/lending_club_default_model.pkl`).
3. The positive-class probability is returned with code-defined bands: HIGH at 0.50 or higher, MEDIUM at 0.25 or higher, and LOW otherwise.
4. SHAP feature drivers are attempted and returned when available. They are explanatory signals, not causal explanations.
5. The endpoint returns the score, band, interpretation, and drivers to the dashboard. The implementation recommends review; it does not approve or decline a loan.

### 3. Direct fraud model scoring

The dashboard's fraud-scoring page calls `POST /predict/fraud-models`. The endpoint loops through saved fraud model definitions and returns one status per model:

- **PaySim:** transaction fields are transformed into time, balance-difference, zero-balance, ratio, and transaction-type features before inference using `models/Fraud_models/paysim_fraud_model.pkl`.
- **IEEE-CIS:** the supplied IEEE feature values and saved categorical encoders are used with `models/Fraud_models/ieee_fraud_model.pkl`.
- The endpoint returns probability, model threshold/risk result, and available SHAP drivers. A model that cannot accept the supplied input is marked incompatible rather than represented as a successful prediction.
- This endpoint explicitly does **not** call retrieval or an LLM.

The two model paths keep their input schemas separate. Although the endpoint currently iterates the configured models in one request, they are not a shared or blended model.

### 4. PaySim fraud investigation

`POST /predict/fraud` and `POST /investigation` call the fraud specialist function, which calls `src/services/risk_investigation.py`:

1. Validate PaySim fields and build the saved model's feature row.
2. Score with the PaySim fraud artifact and derive a threshold-based risk level.
3. Compute SHAP drivers and compose a regulatory search query from transaction type, score, and model factors.
4. Retrieve relevant regulatory/document passages from FAISS or Pinecone, selected for this path with `RAG_VECTOR_BACKEND` (FAISS is the code default).
5. Generate a short analyst summary with the Hugging Face model by default, or Ollama when configured. If generation fails or produces unusable text, return a structured Markdown fallback and a warning.
6. If `account_id` is present, the fraud specialist optionally calls Neo4j fan-in/fan-out queries. The graph results are attached separately as `graph_evidence`; they do not get added to the report-generation context.
7. Return the investigation content to the dashboard. `/investigation` additionally wraps the result in a report record object, but the route does not persist that record to PostgreSQL.

The investigation path does not use the RAG Q&A query-expansion/filter/reranking sequence below.

### 5. Compliance and general RAG Q&A

`POST /compliance/query` and `POST /rag/query` both use `src/services/rag_service.py`; the compliance route adds a compliance-agent label. The active sequence is:

1. Expand the question with rule-based query rewriting (up to four searches).
2. Retrieve candidates from the selected vector backend.
3. Deduplicate chunk text and apply heuristic relevance/evidence-sufficiency checks.
4. Rerank with `cross-encoder/ms-marco-MiniLM-L-6-v2` when available; the code falls back to keyword ranking when cross-encoder loading or scoring fails.
5. Generate an answer from retrieved context. The default response provider is Hugging Face; OpenAI and Ollama providers are also implemented as optional choices.
6. Apply lexical support/usable-answer checks and source-aware evidence extraction. If evidence is insufficient, return an explicit insufficient-evidence result instead of a confident unsupported answer.
7. Return the answer, source references, evidence, and grounding status to the dashboard.

The grounding checks are lexical/heuristic safeguards. They do not prove semantic entailment.

### 6. Document upload and indexing

`POST /api/documents` stores the uploaded bytes under `data/raw/uploads` with a generated ID prefix. `src/services/document_service.py` then:

1. Parses the uploaded document using the extension-specific loaders.
2. Splits extracted text into chunks (default 1,000 characters with 150-character overlap).
3. Indexes chunks via the vector database adapter. The adapter creates embeddings as part of vector-store insertion.
4. Returns indexing status and chunk count to the dashboard.

The parser currently handles PDF, XLSX/XLS, email (`.eml`/`.email`), TXT/MD, and HTML. The frontend file picker also advertises CSV and DOCX, which the backend parser does not currently handle. Conversely, the parser accepts email files that are not listed in the frontend picker. Uploads are not inserted into the SQLAlchemy `Document` table by this route.

The general upload/Q&A vector adapter is selected with `VECTOR_DB_PROVIDER` (FAISS by default). Investigation retrieval uses a separate `RAG_VECTOR_BACKEND` selector and supports FAISS/Pinecone only. Although the defaults can point to the same local FAISS location, configure both selectors and any hosted index consistently before assuming an uploaded document will be available to every RAG path.

## Persistence and integrations

| Component | Verified responsibility | Integration status |
|---|---|---|
| PostgreSQL / SQLAlchemy | Operational customer and case endpoints; overview aggregation reads cases and transactions. | Active for `/api/cases`, `/api/customers`, and `/api/overview`; `DATABASE_URL` is required. |
| FAISS | Local vector indexing/retrieval through the common vector adapter; also the default investigation retrieval backend. | Default in code; requires the local index and embedding dependencies/model. |
| Pinecone | Hosted vector adapter and investigation retrieval option. | Optional; requires API credentials, index configuration, and dependencies. |
| Chroma / Milvus | Provider adapters exposed by the general vector-store interface. | Optional; not the default and requires provider configuration/services. |
| Neo4j | Relationship queries including fan-in/fan-out and transaction chains. | Optional; investigation only calls fan-in/fan-out when `account_id` is provided. A graph must already contain the expected nodes/relationships. |
| Redis | Cache/rate-limit helper functions. | Helper module exists, but the current business request flow does not call it. `/ready` nevertheless probes Redis. |
| Hugging Face embeddings | Default local embedding implementation; default model name is `BAAI/bge-small-en-v1.5`. | Used by vector indexing/retrieval when that provider is selected; model/dependencies must be available. |
| Hugging Face report generation | Default RAG answer provider and default investigation report provider (separate code paths and model defaults). | Optional local model assets/dependencies are needed. |
| Ollama / OpenAI | Alternate generation providers. | Environment-dependent; OpenAI requires its API key, while Ollama requires a reachable local/remote service. |
| Notification webhook | Case-created logging plus optional webhook delivery. | Webhook is only sent when configured; it is not a general model-alert workflow. |

### What PostgreSQL does not currently persist in the active scoring paths

The ORM defines `Prediction`, `Report`, `Document`, `Transaction`, and other tables. However, the active prediction and report handlers do not insert model predictions or generated reports into those tables. Case/customer creation endpoints do write records. The overview route reads existing operational records; fraud analytics are separately calculated from the local PaySim CSV, with a five-minute in-process cache.

## Agent, graph, and model scope

### Implemented and called by active routes

- `risk_agent`: called by the credit-risk endpoint.
- `fraud_agent`: called by fraud prediction/investigation routes; delegates to the PaySim investigation service and optionally adds graph results.
- `compliance_agent`: called by the compliance route and delegates to the same RAG service as `/rag/query`.
- `report_agent`: called by `/investigation` to assemble a response record.

These are direct Python functions called by route handlers. The `supervisor.py` keyword-based dispatcher is not used by the API router. The repository lists LangGraph as a dependency, but the inspected application source does not construct or invoke a LangGraph workflow. LangGraph orchestration is therefore **not active / unverified as an active workflow**.

### Graph RAG qualification

Neo4j graph-building and Cypher query utilities exist, but the main compliance RAG pipeline is vector-based. The current document upload endpoint does not populate the Neo4j document graph. Graph results are not merged into the compliance answer context or into the fraud report context. Neo4j relationship evidence is **optional / conditional** in fraud investigation. Full Graph RAG fusion is **not active / unverified as an active workflow**.

### Not active as prediction APIs

- **AML model:** no active AML prediction route/model inference path was found. AML/KYC appears in search-query text and compliance concepts, not as a dedicated active model workflow.
- **Customer analytics:** a bank-marketing model artifact is present, but no active dashboard/API prediction route loads it.
- **Financial NLP/sentiment and forecasting:** associated files/utilities/notebooks may exist, but no corresponding active dashboard inference route was found.
- **Finance-ratio agent:** deterministic ratio helpers and a keyword supervisor branch exist, but they are not wired into the main FastAPI route flow.
- **Feature importance:** the active explainability implementation returns SHAP drivers; no separate feature-importance response path was found in the active routes.
- **PDF report output:** reports are Markdown/text responses. No active PDF rendering or download endpoint was found.

## Local run behavior verified from source

The repository documents `python run_project.py` as the one-command launcher. In the checked-out `run_project.py`, it:

1. Loads the root `.env` and requires the configured Conda Python executable at a machine-specific absolute path.
2. Checks that PostgreSQL is reachable at `127.0.0.1:5432` and that `DATABASE_URL` is present.
3. Starts `uvicorn src.api.main:app` on port 8000, sets local CORS origins, and sets `AUTH_DISABLED=true`.
4. Starts `npm run dev` in `frontend` on port 5173 if frontend dependencies and the configured `npm.cmd` path exist.
5. Opens the dashboard in a browser.

The run-instructions text also documents starting Uvicorn and Vite in separate terminals. The launcher is therefore not portable as-is to machines without its configured Windows paths. The application was **not launched** during this review; therefore, there was no end-to-end runtime verification. Startup requires local PostgreSQL, a valid local environment, model/index availability, and potentially external or local LLM/vector services. `/ready` checks PostgreSQL, Redis, and Neo4j together and may return 503 when any one is unavailable.

The checked-in YAML files under `configs/` are empty in this checkout; runtime selection is primarily by environment variables and Python defaults. `environment.yml` declares Python 3.11.

## Diagram interpretation and caveats

- Solid arrows indicate source-backed active workflow wiring, not a runtime-tested result. Dashed connectors/callouts indicate optional or configuration-dependent integrations; separately labeled status callouts indicate features not verified as active workflows.
- Different route lanes are independent workflows. They are not a parallel agent fan-out and do not all pass through the same RAG or LLM layer.
- This architecture is source-verified only. The application was not launched, and no end-to-end runtime verification was performed.
- The stored model artifacts were verified by path/existence and the inference-loading code. Their serialized contents were not opened to infer estimator families or performance.
- LangGraph orchestration, full Graph RAG fusion, AML prediction, customer-analytics prediction, and Redis caching are not shown as active workflows.
- The diagram excludes deployment/hosting and CI/CD.
- The frontend Overview has sample fallback values if its API request fails; these values are not backend predictions or persisted operational records.

## Source areas reviewed

- Application/API: `src/main.py`, `src/api/main.py`, `src/api/auth.py`, `src/api/schemas.py`, `src/api/routes/__init__.py`
- Frontend: `frontend/src/App.jsx`, `frontend/src/services/riskApi.js`, dashboard pages for overview, credit, fraud, compliance, and documents
- Inference and features: `src/agents/risk_agent.py`, `src/agents/fraud_agent.py`, `src/agents/compliance_agent.py`, `src/ml_models/credit_risk/`, `src/ml_models/fraud_detection/`, `src/ml_models/explainability/`, `src/preprocessing/feature_engineering.py`
- RAG and ingestion: `src/services/rag_service.py`, `src/services/document_service.py`, `src/services/risk_investigation.py`, `src/ingestion/`, `src/embeddings/`, `src/retriever/`, `src/vectordb/`, `src/llm/`
- Graph and persistence: `src/graph_rag/`, `src/database/`, `src/database/redis.py`
- Runtime/configuration: `run_project.py`, `requirements.txt`, `environment.yml`, `configs/`, `docker-compose.yml`, README and run instructions
