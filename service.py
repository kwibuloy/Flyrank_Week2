"""Business rules for tasks: validation and what each operation means.

The service doesn't know about HTTP or about how tasks are stored. It works
with whatever TaskRepository it is given.
"""
from typing import Any

from repositories import Task, TaskRepository


class TaskNotFound(Exception):
    def __init__(self, id):
        super().__init__(f"Task {id} not found.")
        self.id = id


class InvalidRequest(Exception):
    pass


# Passed in by the routes when the request body isn't valid JSON, so the
# service can still check "does this task exist?" first, as the API always has.
INVALID_JSON = object()


class TaskService:
    def __init__(self, repository: TaskRepository):
        self.repository = repository

    def list_tasks(self) -> list[Task]:
        return self.repository.list()

    def get_task(self, id: int) -> Task:
        task = self.repository.get(id)
        if task is None:
            raise TaskNotFound(id)
        return task

    def create_task(self, body: Any) -> Task:
        if body is INVALID_JSON:
            raise InvalidRequest("body must be valid JSON")
        if not isinstance(body, dict):
            raise InvalidRequest("body must be a JSON object with a title")

        title = body.get("title")
        if not isinstance(title, str) or title.strip() == "":
            raise InvalidRequest("title is required and cannot be empty")

        return self.repository.add(title.strip())

    def update_task(self, id: int, body: Any) -> Task:
        self.get_task(id)  # unknown id -> 404, checked before the body

        if body is INVALID_JSON:
            raise InvalidRequest("body must be valid JSON")
        if not isinstance(body, dict) or not body:
            raise InvalidRequest("body must be a non-empty object with title and/or done")

        unknown = set(body) - {"title", "done"}
        if unknown:
            raise InvalidRequest(f"unknown fields: {', '.join(sorted(unknown))}")

        title = None
        if "title" in body:
            title = body["title"]
            if not isinstance(title, str) or title.strip() == "":
                raise InvalidRequest("title must be a non-empty string")
            title = title.strip()

        done = None
        if "done" in body:
            done = body["done"]
            if not isinstance(done, bool):
                raise InvalidRequest("done must be true or false")

        task = self.repository.update(id, title=title, done=done)
        if task is None:  # deleted between the check above and now
            raise TaskNotFound(id)
        return task

    def delete_task(self, id: int) -> None:
        if not self.repository.delete(id):
            raise TaskNotFound(id)
