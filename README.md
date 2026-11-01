# AI Financial Risk Intelligence Platform
### Risk Scoring · Explainable AI · Regulatory RAG · Relationship Analysis

A financial-risk **decision-support prototype** that brings credit-risk scoring, transaction-fraud analysis, retrieval-backed financial Q&A, and analyst-facing case workflows into one application.

The platform combines a **React + Vite dashboard**, **FastAPI backend**, saved ML artifacts, document retrieval, PostgreSQL-backed operational data, and optional Neo4j relationship queries. It is designed to help analysts review model signals and supporting evidence—not to make autonomous lending, fraud, or regulatory decisions.

> **Implementation note:** This README describes the repository's verified application paths. Some modules are available as utilities but are not fully connected to the primary request flow. In particular, the main compliance RAG path is vector-based; Neo4j graph functionality is implemented but only partially integrated.

---

## Table of contents

- [Visual system workflow](#visual-system-workflow)
- [What the platform does](#what-the-platform-does)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Core workflows](#core-workflows)
- [Repository layout](#repository-layout)
- [Getting started](#getting-started)
- [Configuration and services](#configuration-and-services)
- [API overview](#api-overview)
- [Machine learning and explainability](#machine-learning-and-explainability)
- [RAG and graph capabilities](#rag-and-graph-capabilities)
- [Testing and CI](#testing-and-ci)
- [Limitations and roadmap](#limitations-and-roadmap)
- [Responsible use](#responsible-use)

---

## Visual system workflow

The diagram below illustrates the principal user-facing paths. Credit scoring, direct fraud scoring, fraud investigation, and compliance Q&A are separate backend workflows; they do not all pass through one universal agent pipeline.

```mermaid
flowchart TB
    U[Analyst / User] --> UI[React + Vite Dashboard]
    UI --> API[FastAPI Application]
    API --> AUTH[Bearer-token dependency<br/>or local AUTH_DISABLED mode]

    AUTH --> CREDIT[Credit Risk Endpoint]
    AUTH --> FRAUD[Direct Fraud Scoring]
    AUTH --> INVEST[Fraud Investigation]
    AUTH --> RAG[Compliance / RAG Q&A]
    AUTH --> DOCS[Document Upload & Ingestion]
    AUTH --> OPS[Cases, Customers & Overview]

    CREDIT --> CFE[Dataset-specific feature preparation]
    CFE --> CM[Credit model artifact]
    CM --> CP[Probability + risk band]
    CP --> CSHAP[Optional SHAP drivers]

    FRAUD --> FM[PaySim and IEEE-CIS model artifacts]
    FM --> FP[Probability + threshold result]
    FP --> FSHAP[Optional SHAP drivers]

    INVEST --> IF[PaySim investigation inference]
    IF --> ISHAP[SHAP feature contributions]
    IF --> Q[Build regulatory search query]
    Q --> VDB[(Configured vector index<br/>FAISS or Pinecone)]
    VDB --> E[Retrieved passages + source metadata]
    ISHAP --> REPORT[Local LLM report generation]
    E --> REPORT
    REPORT --> FALLBACK[Structured Markdown fallback<br/>if generation is unavailable]
    REPORT --> IOUT[Investigation response]
    FALLBACK --> IOUT
    INVEST -. optional account ID .-> NEO[(Neo4j relationship queries)]
    NEO -. attached graph evidence .-> IOUT

    RAG --> EXP[Rule-based query expansion]
    EXP --> SEARCH[Vector retrieval]
    SEARCH --> FILTER[Relevance filter + reranking]
    FILTER --> GEN[Grounded response generation]
    GEN --> RAGOUT[Answer + sources + grounding status]
    FILTER -->|No relevant evidence| NOEVID[Insufficient-evidence response]
    NOEVID --> RAGOUT

    DOCS --> PARSE[Parse and chunk supported files]
    PARSE --> INDEX[Vector index]
    INDEX -. retrieved in later queries .-> VDB

    OPS --> PG[(PostgreSQL / SQLAlchemy)]
    CP --> UI
    CSHAP --> UI
    FP --> UI
    FSHAP --> UI
    IOUT --> UI
    RAGOUT --> UI
    PG --> UI

    classDef user fill:#e8f4ff,stroke:#3b82f6,color:#172554;
    classDef service fill:#e9fbf4,stroke:#10b981,color:#064e3b;
    classDef store fill:#fff7e6,stroke:#f59e0b,color:#78350f;
    class U,UI user;
    class API,AUTH,CREDIT,FRAUD,INVEST,RAG,DOCS,OPS,REPORT,GEN service;
    class VDB,NEO,PG store;
```

### Workflow in brief

1. The user submits a credit, fraud, investigation, compliance, or document request through the dashboard.
2. FastAPI validates the request and dispatches it to the corresponding route.
3. The selected ML path prepares the required features and returns a model score or class.
4. Where available, SHAP provides feature-contribution information for analyst review.
5. Investigation and compliance paths retrieve financial/regulatory passages and return source-aware responses.
6. Results are shown in the dashboard; operational case/customer data is handled through PostgreSQL-backed routes.

---

## What the platform does

| Capability | Description |
|---|---|
| Credit-risk scoring | Scores Taiwan and Lending Club applicant inputs with dataset-specific artifacts and feature preparation. |
| Fraud scoring | Runs direct PaySim and IEEE-CIS model inference, returning probability, threshold-based result, and optional SHAP information. |
| Fraud investigation | Combines PaySim inference, SHAP drivers, regulatory-document retrieval, and Markdown report generation with a structured fallback. |
| Compliance Q&A | Expands a question, retrieves and filters vector-indexed passages, reranks evidence, and generates an answer with source information. |
| Document ingestion | Parses supported document formats, creates chunks, and indexes them for retrieval. |
| Relationship analysis | Uses Neo4j graph queries for customer/account/transaction relationships; optional graph evidence can be attached to fraud investigation when an account ID is provided. |
| Analyst dashboard | Provides overview, runtime, cases, credit, fraud, compliance, customer, and document pages. |

---

## Architecture

```mermaid
flowchart LR
    subgraph Frontend
      REACT[React Router]
      CLIENT[riskApi.js<br/>Fetch client]
      REACT --> CLIENT
    end

    subgraph Backend
      FASTAPI[FastAPI routes]
      AGENTS[Specialist agent functions]
      SERVICES[Risk / RAG / Report services]
      FASTAPI --> AGENTS
      FASTAPI --> SERVICES
    end

    subgraph ML_and_Retrieval
      ARTIFACTS[Saved credit & fraud artifacts]
      SHAP[SHAP explainability]
      EMB[Embedding model]
      VECTOR[(FAISS / Chroma / Milvus / Pinecone adapters)]
      LLM[Hugging Face / Ollama<br/>optional OpenAI provider]
    end

    subgraph Persistence
      POSTGRES[(PostgreSQL)]
      NEO4J[(Neo4j - optional)]
      REDIS[(Redis helpers - optional)]
    end

    CLIENT --> FASTAPI
    AGENTS --> ARTIFACTS
    AGENTS --> SHAP
    SERVICES --> EMB
    EMB --> VECTOR
    SERVICES --> LLM
    FASTAPI --> POSTGRES
    AGENTS -. optional relationship queries .-> NEO4J
    FASTAPI -. helper module .-> REDIS
```

**Important architecture distinctions**

- Direct fraud scoring is an inference path; it does not perform document retrieval or LLM report generation.
- Fraud investigation is a separate path that adds retrieval and report creation.
- The primary compliance/RAG service uses vector retrieval. Graph/vector hybrid utilities exist, but the graph evidence is not consistently fused into the primary RAG prompt.
- The multi-agent layer is deterministic Python dispatch and specialist functions. A LangGraph state-machine workflow is not implemented in the inspected source.
- The API report output is Markdown; a PDF-rendering endpoint is not present in the active application path.

---

## Technology stack

| Layer | Technologies |
|---|---|
| Frontend | React, React Router, Vite, Recharts, Framer Motion, Lucide icons, CSS |
| API/backend | Python, FastAPI, Pydantic, SQLAlchemy |
| Machine learning | scikit-learn, pandas, NumPy, joblib/pickle model artifacts |
| Explainability | SHAP |
| RAG / document processing | LangChain document abstractions/loaders, Hugging Face embeddings, retrieval and reranking utilities |
| Vector stores | FAISS, Chroma, Milvus, Pinecone adapters; defaults depend on the code path |
| Graph | Neo4j driver and Cypher query utilities |
| LLM options | Hugging Face generation, Ollama HTTP API, optional OpenAI provider |
| Database / helpers | PostgreSQL, Redis utility module |
| Development / CI | Docker, Docker Compose, GitHub Actions, pytest, Qlty coverage upload |

---

## Core workflows

### 1. Credit risk

`POST /predict/credit-risk`

- Accepts a dataset key (`taiwan` or `lending_club`) and applicant fields.
- Loads the dataset-specific saved artifact and prepares the expected feature columns.
- Uses the positive-class probability as the risk score.
- Applies code-defined bands: **HIGH ≥ 0.50**, **MEDIUM ≥ 0.25**, otherwise **LOW**.
- Attempts to attach SHAP feature contributions.

A high or medium band recommends review. The application does not approve or decline a loan automatically.

### 2. Direct fraud scoring

`POST /predict/fraud-models`

- Scores PaySim and IEEE-CIS inputs using their respective saved artifacts.
- PaySim derives time, balance-difference, zero-balance, ratio, and transaction-type features.
- IEEE-CIS uses its model schema and saved categorical encoders.
- Returns model status, probability, threshold-based risk result, and optional SHAP drivers.
- An incompatible or unavailable model can be represented as a per-model result rather than silently treated as a successful score.

This route is intentionally separate from the investigation/RAG flow.

### 3. Fraud investigation

`POST /investigation` or `POST /predict/fraud`

1. Build PaySim features and calculate the fraud probability.
2. Attempt SHAP feature attribution.
3. Form a regulatory search query using transaction and model information.
4. Retrieve supporting passages from the configured FAISS or Pinecone index.
5. Generate an analyst-facing Markdown report with the selected local generator.
6. Use a structured report fallback if generation is unavailable or unusable.
7. If an account ID is supplied, optionally attach Neo4j fan-in/fan-out evidence.

Graph evidence is attached as optional investigation evidence; it is not merged into the regulatory LLM prompt in the verified route.

### 4. Compliance / RAG Q&A

`POST /compliance/query` or `POST /rag/query`

1. Expand the user question into a limited set of related queries.
2. Search the configured vector backend.
3. Remove duplicate chunks and apply a heuristic relevance filter.
4. Rerank candidate passages using a cross-encoder or keyword fallback.
5. Generate an answer using retrieved context and source metadata.
6. Apply response checks and fallback behavior.
7. Return an explicit insufficient-evidence response when relevant evidence is not found.

The grounding checks are heuristic; they do not guarantee semantic entailment. Retrieved sources should be reviewed by a human.

---

## Repository layout

```text
.
├── frontend/                 # React + Vite dashboard
│   └── src/
│       ├── components/       # Reusable UI components
│       ├── hooks/            # React hooks
│       ├── pages/             # Overview, cases, credit, fraud, compliance, etc.
│       └── services/          # Frontend API client
├── src/
│   ├── agents/                # Supervisor and specialist functions
│   ├── api/                   # FastAPI app, routes, schemas, auth, middleware
│   ├── database/              # SQLAlchemy models, PostgreSQL and Redis helpers
│   ├── embeddings/            # Embedding model and chunk pipeline
│   ├── evaluation/            # Evaluation utilities
│   ├── graph_rag/              # Neo4j graph builder and query utilities
│   ├── ingestion/             # File parsers and loaders
│   ├── llm/                   # Provider factory, prompts, response helpers
│   ├── ml_models/              # Credit, fraud, explainability, forecasting
│   ├── preprocessing/          # Feature engineering and document chunking
│   ├── retriever/              # Search, reranking, query rewrite utilities
│   ├── services/               # Investigation, RAG, reports, document ingestion
│   └── vectordb/               # Vector-store adapters and retrieval
├── models/                    # Saved model and supporting artifacts
├── data/                      # Dataset and document folders
├── vector_store/               # Local vector index assets (where present)
├── scripts/                   # Training, evaluation, ingestion, indexing, utilities
├── notebooks/                 # Experiments and prototypes
├── tests/                     # Python unit tests
├── Dockerfile
├── docker-compose.yml
└── .github/workflows/ci.yml
```

---

## Getting started

> The exact runtime depends on your environment, model artifacts, vector index, and configured providers. Check the repository's current dependency files and environment settings before running.

### Prerequisites

- Python 3.11
- Node.js and npm compatible with the frontend lockfile
- Git and Git LFS if model artifacts are tracked through LFS
- Docker and Docker Compose for container workflows
- PostgreSQL for database-backed routes
- Optional: Neo4j, Redis, Ollama, or a configured hosted provider, depending on the workflow you want to run

### 1. Clone the repository

```bash
git clone https://github.com/Abhishek4209/AI-Financial-Risk-Intelligence-Platform-using-Graph-RAG-Multi-Agent-LLM.git
cd AI-Financial-Risk-Intelligence-Platform-using-Graph-RAG-Multi-Agent-LLM
```

If model files are stored with Git LFS, fetch them:

```bash
git lfs install
git lfs pull
```

### 2. Set up the Python environment

```bash
python -m venv .venv
```

Activate it:

**Windows PowerShell**
```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

Install the project dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Set up the frontend

```bash
cd frontend
npm ci
npm run build
```

For local development, start the Vite server using the frontend's configured development script, then return to the repository root to start the API.

### 4. Start the API

From the repository root:

```bash
python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

API documentation is typically available at:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/health`

The application has a bearer-token dependency for business routes. A local development launcher may set `AUTH_DISABLED=true`; do not use an authentication bypass in a public or production deployment.

### 5. Docker Compose

The checked-in Compose setup includes PostgreSQL and the backend. It does not start the frontend, Redis, or Neo4j.

```bash
docker compose up --build
```

Provide the required environment configuration before starting. Note that the readiness endpoint checks PostgreSQL, Redis, and Neo4j; with only the Compose services running, readiness may report unavailable dependencies.

---

## Configuration and services

Runtime behavior is controlled primarily by environment variables and Python defaults. The checked-in YAML configuration files were empty in the reviewed checkout, so do not assume they provide active settings.

| Component | Notes |
|---|---|
| Authentication | JWT bearer dependency; `AUTH_DISABLED=true` is a local-development bypass. |
| PostgreSQL | Used by operational overview, case, and customer routes. |
| Redis | Helper functions exist, but current business routes do not wire them into the main request flow. |
| Neo4j | Supports graph relationship queries; optional in fraud investigation when an account ID is supplied. |
| Vector store | Backend selection varies by path. General vector adapter defaults to FAISS; investigation retrieval uses a separate setting and supports FAISS/Pinecone. |
| LLM provider | Hugging Face/Ollama options are present; an optional OpenAI provider is also available through configuration. |

**Secrets:** Never commit real API keys or credentials. If a credential has been committed, revoke or rotate it and replace it with a clearly fake placeholder in example files.

---

## API overview

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Process-level health response |
| `/ready` | GET | Checks configured dependencies |
| `/predict/credit-risk` | POST | Credit-risk score and risk band |
| `/predict/fraud-models` | POST | Direct PaySim / IEEE-CIS model scoring |
| `/predict/fraud-models/ieee-cis/schema` | GET | IEEE-CIS feature schema |
| `/predict/fraud` | POST | Fraud investigation path |
| `/investigation` | POST | Investigation response and report |
| `/rag/query` | POST | Retrieval-backed question answering |
| `/compliance/query` | POST | Compliance-oriented RAG response |
| `/api/documents` | POST | Upload and index a supported document |
| `/api/overview` | GET | Dashboard aggregates |
| `/api/cases` | GET / POST | List or create cases |
| `/api/cases/{case_id}` | GET | Fetch a case |
| `/api/customers` | GET / POST | List or create customers |
| `/api/customers/{customer_id}` | GET | Fetch a customer |

See the interactive API docs at `/docs` while the backend is running for request and response schemas.

---

## Machine learning and explainability

### Model inputs

- **Credit:** Taiwan and Lending Club use separate artifacts and feature-preparation logic.
- **PaySim fraud:** Transaction step/type, amount, origin balances, and destination balances are transformed into model features.
- **IEEE-CIS fraud:** Uses its saved feature schema and categorical encoders; raw preprocessing fields may be required to derive model inputs.

### Explainability

SHAP is used where supported to provide feature-contribution information. SHAP values are **not causal explanations** and should be interpreted with the model, input data, and explainer assumptions in mind.

### Evaluation

The repository includes training and evaluation utilities, notebooks, and saved metric reports. Reported metrics are artifact/report-specific; they should not be interpreted as proof of current performance on a live financial institution's population. Independent validation, calibration, fairness testing, temporal evaluation, and model governance are outside the demonstrated active workflow.

---

## RAG and graph capabilities

### Retrieval-Augmented Generation

The RAG path uses document chunks, embeddings, vector search, relevance filtering, reranking, and a generation step. Source metadata is returned to help reviewers trace the response to retrieved material.

### Graph relationship analysis

Neo4j graph utilities model:

- `Customer`
- `Account`
- `Transaction`
- `Document`

Relationship types include ownership, sending/receiving, and document association. Cypher utilities support connected-customer, fan-in, fan-out, transaction-chain, and customer-document queries.

**Graph integration status:** graph schema and query utilities are implemented, and optional graph evidence can be attached in the fraud investigation path. The document upload path does not currently populate the Neo4j document graph, and the main compliance RAG response pipeline does not consistently combine graph evidence with vector evidence.

---

## Testing and CI

The repository includes Python unit tests and a GitHub Actions workflow. The configured CI checks include:

- Python compilation
- YAML and Docker Compose validation
- pytest with coverage
- Frontend dependency installation and Vite build
- Docker image build

Run the Python test suite from the repository root:

```bash
pytest tests --cov=src
```

A passing unit suite is not equivalent to end-to-end financial-system validation, model fairness certification, production SLO validation, or confirmation that external services are available.

---

## Limitations and roadmap

The current repository should be treated as a **prototype / decision-support application**. Key areas to address before production use include:

- Complete browser authentication and authorization; the frontend currently does not attach a bearer token.
- Align readiness checks with the services actually provisioned in the deployment.
- Integrate and validate graph evidence in the main retrieval/answer context if full Graph RAG is a goal.
- Align accepted upload extensions between the UI and API parser.
- Add robust source-grounding evaluation beyond lexical heuristics.
- Establish model calibration, fairness, temporal validation, governance, and monitoring.
- Add database migrations, secrets management, observability, and deployment manifests.
- Add a real PDF report renderer if downloadable PDF output is required.
- Review the overview fallback behavior so server errors cannot be confused with sample dashboard data.
- Validate all dataset licenses, artifact provenance, and feature preprocessing consistency.

---

## Responsible use

This project is intended for educational, experimentation, and analyst decision-support purposes.

- A model score is an estimate—not proof of fraud, default, or wrongdoing.
- A threshold-based “HIGH” result is a review signal, not an automatic block, rejection, or filing.
- SHAP contributions are not causal explanations.
- Generated answers and summaries can be wrong; verify claims against source documents.
- Do not use the prototype as the sole basis for consequential financial decisions.
- Protect personal and financial data and use only authorized datasets.

---

## Acknowledgements

Built with open-source machine-learning, API, frontend, retrieval, and graph technologies. Dataset and model use should follow the respective licenses and terms.

