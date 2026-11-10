"""Storage layer: where tasks live.

The service only ever talks to the TaskRepository interface, so a different
storage backend can be swapped in without touching the service or the routes.
"""
from typing import Optional, Protocol, TypedDict


class Task(TypedDict):
    id: int
    title: str
    done: bool


class TaskRepository(Protocol):
    def list(self) -> list[Task]:
        """Every task, ordered by id."""

    def get(self, id: int) -> Optional[Task]:
        """One task, or None if no task has this id."""

    def add(self, title: str) -> Task:
        """Store a new, not-done task and return it with its new id."""

    def update(self, id: int, title: Optional[str] = None, done: Optional[bool] = None) -> Optional[Task]:
        """Change the given fields and return the task, or None if it doesn't exist."""

    def delete(self, id: int) -> bool:
        """Remove the task. True if it existed, False if not."""


EXAMPLE_TASKS = [("Workout", False), ("Eat", True), ("Shower", True)]


class InMemoryTaskRepository:
    """Keeps tasks in a Python list. Everything is lost when the server stops."""

    def __init__(self, seed=EXAMPLE_TASKS):
        self._tasks: list[Task] = []
        for title, done in seed:
            self.update(self.add(title)["id"], done=done)

    def list(self) -> list[Task]:
        return [dict(t) for t in sorted(self._tasks, key=lambda t: t["id"])]

    def get(self, id: int) -> Optional[Task]:
        task = self._find(id)
        return dict(task) if task else None

    def add(self, title: str) -> Task:
        new_id = max((t["id"] for t in self._tasks), default=0) + 1
        task: Task = {"id": new_id, "title": title, "done": False}
        self._tasks.append(task)
        return dict(task)

    def update(self, id: int, title: Optional[str] = None, done: Optional[bool] = None) -> Optional[Task]:
        task = self._find(id)
        if task is None:
            return None
        if title is not None:
            task["title"] = title
        if done is not None:
            task["done"] = done
        return dict(task)

    def delete(self, id: int) -> bool:
        task = self._find(id)
        if task is None:
            return False
        self._tasks.remove(task)
        return True

    def _find(self, id: int) -> Optional[Task]:
        return next((t for t in self._tasks if t["id"] == id), None)
