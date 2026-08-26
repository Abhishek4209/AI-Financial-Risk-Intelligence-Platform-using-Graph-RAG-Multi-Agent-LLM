# Deployment Guide

## Prerequisites

- Docker Desktop with Docker Compose v2
- Python 3.11 or newer
- Conda, optional for environment management
- Node.js 20 or newer and npm
- Credentials for the selected LLM, embedding, vector database, and external data providers

## Environment Configuration

Create `.env` beside `docker-compose.yml`. Do not commit it.

```dotenv
APP_ENV=development

POSTGRES_DB=financial_risk
POSTGRES_USER=risk_user
POSTGRES_PASSWORD=replace-with-a-secure-password
POSTGRES_PORT=5432

REDIS_PORT=6379

NEO4J_PASSWORD=replace-with-a-secure-password
NEO4J_HTTP_PORT=7474
NEO4J_BOLT_PORT=7687

BACKEND_PORT=8000

VECTOR_DB_PROVIDER=chroma
LLM_PROVIDER=
LLM_MODEL=
LLM_API_KEY=
```

The Compose configuration builds the internal database URLs automatically. The `.env` file must not contain production secrets in a committed file.

## Start Infrastructure and Backend

Start all Compose services:

```powershell
docker compose up -d --build
```

This starts:

- PostgreSQL
- Redis
- Neo4j
- FastAPI backend

Inspect service status:

```powershell
docker compose ps
```

View logs:

```powershell
docker compose logs -f backend
docker compose logs -f postgres redis neo4j
```

The API is available at:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Neo4j Browser: `http://localhost:7474`

## Stop Services

Stop services without deleting data:

```powershell
docker compose down
```

Delete development data only when resetting the environment:

```powershell
docker compose down -v
```

Persistent named volumes:

- `postgres_data`
- `redis_data`
- `neo4j_data`
- `neo4j_logs`

## Backend Container

The backend image is built from the repository `Dockerfile`.

The container:

- Uses Python 3.11
- Installs dependencies from `requirements.txt`
- Installs PostgreSQL, OCR, and computer-vision system libraries
- Exposes port `8000`
- Runs `src.main:app`
- Mounts source, configuration, data, and model directories during development

The backend depends on healthy PostgreSQL, Redis, and Neo4j services.

## Local Backend Development

Using a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
$env:PYTHONPATH = (Get-Location).Path
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Using Conda:

```powershell
conda env create -f environment.yml
conda activate financial-risk-intelligence
$env:PYTHONPATH = (Get-Location).Path
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend Development

Install and start the React frontend:

```powershell
cd frontend
npm install
$env:VITE_API_URL = "http://localhost:8000"
npm run dev
```

Build production assets:

```powershell
npm run build
```

Serve the generated `frontend/dist/` directory through a static web server or reverse proxy.

The frontend must communicate with FastAPI and must not contain ML, database, or RAG business logic.

## Data and Model Mounts

During local Compose development:

- `./src` is mounted at `/app/src`
- `./configs` is mounted at `/app/configs`
- `./data` is mounted at `/app/data`
- `./models` is mounted at `/app/models`

Keep raw datasets in `data/raw/` immutable. Do not commit sensitive customer or financial data.

## Database Initialization

PostgreSQL and Neo4j data persist in Docker volumes.

Neo4j credentials are initialized when the volume is created. Changing `NEO4J_PASSWORD` later does not change an existing database password.

To reset local databases:

```powershell
docker compose down -v
docker compose up -d --build
```

Use this only when local data can be deleted.

## CI/CD

The CI workflow should:

1. Install Python dependencies.
2. Compile Python sources.
3. Validate YAML and Compose configuration.
4. Run unit and integration tests.
5. Run linting and security checks.
6. Build the backend Docker image.
7. Deploy only after protected-environment approval.

Production deployment should additionally include:

- Database migrations
- Registry authentication
- Secret injection
- Deployment smoke tests
- Health and readiness checks

## Production Recommendations

- Use managed PostgreSQL, Redis, Neo4j, and vector infrastructure where practical.
- Store documents and model artifacts in durable object storage.
- Use HTTPS behind a reverse proxy.
- Keep database ports private.
- Pin image and dependency versions.
- Run the backend as a non-root user.
- Set CPU, memory, upload-size, and request-timeout limits.
- Configure backups, retention, audit logging, and secret rotation.
- Run Celery workers separately for ingestion, embedding, inference, and report generation.
- Add monitoring for latency, failures, model drift, and retrieval quality.
- Require human review for lending, fraud, and compliance decisions.

## Kubernetes Direction

The `deployment/kubernetes/` directory is reserved for production manifests.

A production deployment should include separate workloads for:

- FastAPI API
- React frontend
- Celery workers
- Scheduled ingestion jobs

Include Services, Ingress, ConfigMaps, Secrets, resource limits, readiness probes, liveness probes, and autoscaling policies.

## Troubleshooting

### Port already in use

Change the host-side port in `.env`, for example:

```dotenv
POSTGRES_PORT=55432
```

Then restart Compose:

```powershell
docker compose down
docker compose up -d --build
```

### Neo4j authentication failure

Verify that `NEO4J_PASSWORD` is correct. If the volume was already initialized, reset local data:

```powershell
docker compose down -v
docker compose up -d --build
```

### Backend is unavailable

Check the backend logs:

```powershell
docker compose logs -f backend
```

Confirm that the application exports `app` from `src.main`:

```python
from fastapi import FastAPI

app = FastAPI()
```

Check the health endpoint:

```powershell
Invoke-WebRequest http://localhost:8000/health
```

### Dependency is unhealthy

Inspect service status and logs:

```powershell
docker compose ps
docker compose logs postgres redis neo4j
```

### Complete local reset

Only use this when all local database data can be discarded:

```powershell
docker compose down -v
docker compose up -d --build
```