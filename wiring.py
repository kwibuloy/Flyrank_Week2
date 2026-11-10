"""Composition root: the one place that decides which repository the app uses.

Swapping storage backends means changing this file only. The service and the
routes stay exactly the same.
"""
import os

from dotenv import load_dotenv

from postgres_repository import PostgresTaskRepository
from service import TaskService

_repository: PostgresTaskRepository | None = None
_service: TaskService | None = None


def startup() -> None:
    global _repository, _service
    # Reads .env when running on your machine. Inside docker compose the
    # variables are already set, and load_dotenv never overrides them.
    load_dotenv()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set. Copy .env.example to .env and fill it in.")
    _repository = PostgresTaskRepository(database_url)
    _service = TaskService(_repository)


def shutdown() -> None:
    global _repository, _service
    if _repository is not None:
        _repository.close()
    _repository = None
    _service = None


def get_service() -> TaskService:
    """FastAPI dependency used by the routes."""
    assert _service is not None, "startup() has not run"
    return _service
