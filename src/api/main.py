"""FastAPI application factory; exported as `app` for `uvicorn src.main:app`."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.middleware import RequestIDMiddleware, safe_error_detail
from src.api.routes import router as api_router
from src.api.schemas import HealthResponse, ReadyResponse



def create_app() -> FastAPI:
        app = FastAPI(
                title="AI Financial Risk Intelligence API",
                version="0.1.0",
                description="Decision-support API for credit risk, fraud, compliance, and document RAG. "
                "This API does not make autonomous lending, fraud, or legal decisions.",
        )

        app.add_middleware(RequestIDMiddleware)
        app.add_middleware(
                CORSMiddleware,
                allow_origins=_allowed_origins(),
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
        )

        @app.exception_handler(Exception)
        async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
                return JSONResponse(status_code=500, content={"detail": safe_error_detail(exc)})

        @app.get("/health")
        def health() -> HealthResponse:
                return HealthResponse()

        @app.get("/ready", responses={503: {"description": "A required dependency is unavailable"}})
        def ready() -> ReadyResponse:
                dependencies = {"postgres": _check_postgres(), "redis": _check_redis(), "neo4j": _check_neo4j()}
                if any(status != "ok" for status in dependencies.values()):
                        raise HTTPException(status_code=503, detail=dependencies)
                return ReadyResponse(status="ready", dependencies=dependencies)

        app.include_router(api_router)
        return app



def _check_postgres() -> str:
        try:
                from sqlalchemy import text

                from src.database.postgres import get_engine


                with get_engine().connect() as connection:
                        connection.execute(text("SELECT 1"))
                return "ok"
        except Exception:
                return "unavailable"



def _check_redis() -> str:
        try:
                from src.database.redis import get_redis_client

                get_redis_client().ping()
                return "ok"
        except Exception:

                return "unavailable"



def _check_neo4j() -> str:
        try:
                from src.graph_rag.neo4j_loader import verify_connectivity

                return "ok" if verify_connectivity() else "unavailable"
        except Exception:
                return "unavailable"



def _allowed_origins() -> list[str]:
        import os

        origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
        return [origin.strip() for origin in origins.split(",") if origin.strip()]



app = create_app()
