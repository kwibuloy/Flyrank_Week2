"""Composition root: the one place that decides which repository the app uses.

Swapping storage backends means changing this file only. The service and the
routes stay exactly the same.
"""
from repositories import InMemoryTaskRepository
from service import TaskService

_service: TaskService | None = None


def startup() -> None:
    global _service
    _service = TaskService(InMemoryTaskRepository())


def shutdown() -> None:
    global _service
    _service = None


def get_service() -> TaskService:
    """FastAPI dependency used by the routes."""
    assert _service is not None, "startup() has not run"
    return _service
