import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

# The database file lives next to this script, so it is found no matter
# which folder the server is started from.
DB_PATH = Path(__file__).parent / "tasks.db"

EXAMPLE_TASKS = [("Workout", False), ("Eat", True), ("Shower", True)]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the tasks table if needed and seed it on the very first run."""
    conn = get_db()
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id    INTEGER PRIMARY KEY,
                title TEXT    NOT NULL,
                done  BOOLEAN NOT NULL DEFAULT 0
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if count == 0:
            conn.executemany("INSERT INTO tasks (title, done) VALUES (?, ?)", EXAMPLE_TASKS)
    conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Task API",
    version="1.0",
    description="A small to-do API with full CRUD, stored in SQLite.",
    lifespan=lifespan,
)

@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    if any(err.get("loc", [None])[0] == "path" for err in exc.errors()):
        id = request.path_params.get("id")
        return JSONResponse(status_code=404, content={"error": f"Task {id} not found."})
    return JSONResponse(status_code=400, content={"error": "invalid request"})

tasks = [
    {
        "id": 1,
        "title": "Workout",
        "done": False
    },
    {
        "id": 2,
        "title": "Eat",
        "done": True
    },
    {
        "id": 3,
        "title": "Shower",
        "done": True
    }
]

@app.get("/", summary="API info", description="Returns the API name, version and available endpoints.")
async def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}

@app.get("/health", summary="Health check", description="Returns ok when the server is running.")
async def health():
    return {"status": "ok"}

@app.get("/tasks", summary="List tasks", description="Returns every task.")
async def get_tasks():
    return tasks

@app.get("/tasks/{id}", summary="Get a task", description="Returns one task by id, or 404 if it does not exist.")
async def get_tasks_id(id: int):
    for task in tasks:
        if task["id"] == id:
            return task
    return JSONResponse(status_code=404, content={"error": f"Task {id} not found."})  

@app.post(
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
async def create_task(request: Request):
    try:
        task = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "body must be valid JSON"})

    if not isinstance(task, dict):
        return JSONResponse(status_code=400, content={"error": "body must be a JSON object with a title"})

    title = task.get("title")

    if not isinstance(title, str) or title.strip() == "":
        return JSONResponse(status_code=400, content={"error": "title is required and cannot be empty"})

    new_id = max([t["id"]for t in tasks], default=0) + 1

    new_task = {"id": new_id, "title": title.strip(), "done": False}
    tasks.append(new_task)
    return new_task


@app.put(
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
async def update_task(id: int, request: Request):
    task = next((t for t in tasks if t["id"] == id), None)
    if task is None:
        return JSONResponse(status_code=404, content={"error": f"Task {id} not found."})

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "body must be valid JSON"})

    if not isinstance(body, dict) or not body:
        return JSONResponse(status_code=400, content={"error": "body must be a non-empty object with title and/or done"})

    unknown = set(body) - {"title", "done"}
    if unknown:
        return JSONResponse(status_code=400, content={"error": f"unknown fields: {', '.join(sorted(unknown))}"})

    if "title" in body:
        title = body["title"]
        if not isinstance(title, str) or title.strip() == "":
            return JSONResponse(status_code=400, content={"error": "title must be a non-empty string"})

    if "done" in body and not isinstance(body["done"], bool):
        return JSONResponse(status_code=400, content={"error": "done must be true or false"})

    if "title" in body:
        task["title"] = body["title"].strip()
    if "done" in body:
        task["done"] = body["done"]
    return task

@app.delete("/tasks/{id}", status_code=204, summary="Delete a task", description="Removes the task. Returns 204 with an empty body, or 404 for an unknown id.")
async def delete_task(id: int):
    for i, task in enumerate(tasks):
        if task["id"] == id:
            tasks.pop(i)
            return Response(status_code=204)
    return JSONResponse(status_code=404, content={"error": f"Task {id} not found."})
