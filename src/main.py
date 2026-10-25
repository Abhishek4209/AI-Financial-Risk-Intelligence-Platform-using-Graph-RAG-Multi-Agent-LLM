"""Top-level entry point; Dockerfile and docker-compose run `uvicorn src.main:app`."""

from src.api.main import app

__all__ = ["app"]
