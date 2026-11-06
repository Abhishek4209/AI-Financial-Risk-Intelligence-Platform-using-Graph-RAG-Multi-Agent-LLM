# Local Development Guide

This project is intended to run on your own computer. No cloud hosting account or deployment configuration is required.

## Requirements

- Python 3.11 or newer
- Node.js 20 or newer and npm
- Git and Git LFS (for tracked model artifacts)
- Optional: Docker Desktop with Docker Compose v2, PostgreSQL, Redis, and Neo4j
- Local credentials for any LLM, embedding, or external data provider you choose to use

## First-time setup

From the repository root:

```powershell
git lfs install
git lfs pull
python -m pip install --upgrade pip
pip install -r requirements.txt
cd frontend
npm ci
cd ..
```

Create a local `.env` file from `.env.example` if the backend requires environment configuration. Never commit real credentials or customer data.

## Run the application

The recommended launcher starts the backend and frontend:

```powershell
python run_project.py
```

Run it from the repository root. Use the local URLs printed in the terminal. Typical development URLs are:

- Frontend: `http://localhost:5173`
- Backend API: `http://127.0.0.1:8000`
- API documentation: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

If you start the backend and frontend separately, use the project's documented local commands and set `VITE_API_URL=http://127.0.0.1:8000` only when needed.

## Optional local Docker environment

Create a local `.env` beside `docker-compose.yml`, then start the local supporting services:

```powershell
docker compose up -d --build
docker compose ps
docker compose logs -f backend
```

This Compose setup is for local development. Stop the containers without deleting their data:

```powershell
docker compose down
```

To stop the application launcher, press `Ctrl + C` in its terminal.

## Tests

Run the Python tests from the repository root:

```powershell
pytest tests --cov=src
```

The GitHub Actions CI workflow runs checks and tests only; it does not publish or host the application.

## Local configuration and data

- Keep datasets under `data/raw/` and do not commit private or licensed data.
- Keep model artifacts in the configured local model directories.
- Configure PostgreSQL, Redis, Neo4j, vector stores, and LLM providers only if the feature you are using needs them.
- Keep passwords, API keys, database URLs, and `.env` files out of Git.
