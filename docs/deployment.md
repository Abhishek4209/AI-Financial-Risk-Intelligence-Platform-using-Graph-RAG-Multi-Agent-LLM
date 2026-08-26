# Deployment Guide

## Prerequisites

- Docker Desktop with Docker Compose v2 for local containers
- Python 3.11 or newer for local backend development
- Node.js 20 or newer and npm for frontend development
- Access credentials for the selected LLM, embedding, vector database, and external data providers

## Environment Configuration

Create a local `.env` file beside `docker-compose.yml`. Do not commit it.

```dotenv
POSTGRES_DB=financial_risk
POSTGRES_USER=risk_user
POSTGRES_PASSWORD=replace-with-a-local-password
POSTGRES_PORT=5432
REDIS_PORT=6379
NEO4J_AUTH=neo4j/replace-with-a-local-password
NEO4J_PASSWORD=replace-with-a-local-password
NEO4J_HTTP_PORT=7474
NEO4J_BOLT_PORT=7687
BACKEND_PORT=8000
```

Use strong, unique values outside local development. LLM and vector-store credentials should be added through a secret manager or CI environment, not stored in this file.

## Local Infrastructure

Start PostgreSQL, Redis, and Neo4j:

```bash
docker compose up -d
```

Inspect service status and logs:

```bash
docker compose ps
docker compose logs -f postgres redis neo4j
```

The Compose file persists data in named volumes: `postgres_data`, `redis_data`, `neo4j_data`, and `neo4j_logs`.

Stop the services without deleting data:

```bash
docker compose down
```

Delete local data only when resetting the development environment:

```bash
docker compose down -v
```

## Backend Container

The backend is behind the `app` Compose profile because the API entrypoint is still being implemented. Once `src.main:app` exists, build and start it with:

```bash
docker compose --profile app up --build
```

The image is built from `Dockerfile`, listens on port `8000`, and receives internal service names through `DATABASE_URL`, `REDIS_URL`, and `NEO4J_URI`.

For direct local development:

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend

Install and run the Vite frontend:

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_URL` before starting the frontend when the API is not on the default host:

```bash
# Windows PowerShell
$env:VITE_API_URL = "http://localhost:8000"
npm run dev
```

Build production assets with `npm run build`; serve the generated `frontend/dist/` directory through a static web server or reverse proxy.

## CI/CD

The workflow in `.github/workflows/ci.yml` runs for pushes and pull requests targeting `main` or `master`. It currently:

1. Installs Python 3.11 dependencies.
2. Compiles Python sources.
3. Parses the Compose and application YAML files.
4. Runs the test suite.
5. Builds the backend Docker image without pushing it.

Before enabling deployment, add protected environment secrets, image registry authentication, database migration steps, and a smoke test against a deployed health endpoint.

## Production Recommendations

- Use a managed PostgreSQL, Redis, Neo4j, and vector database where possible.
- Store uploaded documents and model artifacts in durable object storage.
- Put the API and frontend behind TLS termination and a reverse proxy.
- Restrict database ports to private networks; do not expose them publicly.
- Pin base image and dependency versions after a compatibility review.
- Run the API as a non-root user and set CPU, memory, and request-size limits.
- Configure backups, retention, audit logging, secret rotation, and alerting before handling regulated data.
- Deploy separate worker processes for Celery tasks and scale them independently from the API.
- Add readiness probes for dependencies and liveness probes for the API process.

## Kubernetes Direction

The `deployment/kubernetes/` directory is reserved for manifests. A production deployment should include separate workloads for the API, frontend, Celery workers, and scheduled ingestion tasks, with Services, Ingress, ConfigMaps, Secrets, resource requests, probes, and horizontal scaling policies.

## Troubleshooting

### Port already in use

Change the host-side port in `.env`, for example `POSTGRES_PORT=55432`, then restart Compose.

### Neo4j authentication failure

Ensure `NEO4J_AUTH` is set as `neo4j/password` on the first volume initialization. Changing it after the database volume exists does not reset the existing password.

### Backend image starts but API is unavailable

Confirm that the application exports `app` from the module targeted by the Dockerfile command and inspect logs:

```bash
docker compose --profile app logs -f backend
```

### Resetting a failed local database

Stop Compose and remove volumes only if the local data can be discarded:

```bash
docker compose down -v
docker compose up -d
```
