"""HTTP layer: turns requests into service calls and service results into responses.

No validation rules and no storage code live here. Service calls run in a
thread pool so a slow storage backend never blocks the event loop.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from service import INVALID_JSON, TaskService
from wiring import get_service

router = APIRouter()


async def read_json(request: Request):
    try:
        return await request.json()
    except Exception:
        return INVALID_JSON


@router.get("/", summary="API info", description="Returns the API name, version and available endpoints.")
async def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@router.get("/health", summary="Health check", description="Returns ok when the server is running.")
async def health():
    return {"status": "ok"}


@router.get("/tasks", summary="List tasks", description="Returns every task.")
async def get_tasks(service: TaskService = Depends(get_service)):
    return await run_in_threadpool(service.list_tasks)


@router.get("/tasks/{id}", summary="Get a task", description="Returns one task by id, or 404 if it does not exist.")
async def get_tasks_id(id: int, service: TaskService = Depends(get_service)):
    return await run_in_threadpool(service.get_task, id)


@router.post(
    "/tasks",
    status_code=201,
    summary="Create a task",
    description="Creates a task from a non-empty title. Returns 201 with the new task, or 400 if the body is invalid or the title is missing or empty.",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["title"],
                        "properties": {"title": {"type": "string"}},
                    },
                    "example": {"title": "Buy milk"},
                }
            },
        }
    },
)
async def create_task(request: Request, service: TaskService = Depends(get_service)):
    body = await read_json(request)
    return await run_in_threadpool(service.create_task, body)


@router.put(
    "/tasks/{id}",
    summary="Update a task",
    description="Replaces the task's title and/or done. Returns the updated task, 404 for an unknown id, or 400 for an empty or invalid body.",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {"title": {"type": "string"}, "done": {"type": "boolean"}},
                    },
                    "example": {"title": "Buy oat milk", "done": True},
                }
            },
        }
    },
)
async def update_task(id: int, request: Request, service: TaskService = Depends(get_service)):
    body = await read_json(request)
    return await run_in_threadpool(service.update_task, id, body)


@router.delete("/tasks/{id}", status_code=204, summary="Delete a task", description="Removes the task. Returns 204 with an empty body, or 404 for an unknown id.")
async def delete_task(id: int, service: TaskService = Depends(get_service)):
    await run_in_threadpool(service.delete_task, id)
    return Response(status_code=204)
