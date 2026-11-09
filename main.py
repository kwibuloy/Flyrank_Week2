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


def row_to_task(row):
    # SQLite stores booleans as 0/1, so turn them back into true/false for JSON.
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


def fetch_task(id: int):
    conn = get_db()
    row = conn.execute("SELECT id, title, done FROM tasks WHERE id = ?", (id,)).fetchone()
    conn.close()
    return row_to_task(row) if row else None


def not_found(id: int):
    return JSONResponse(status_code=404, content={"error": f"Task {id} not found."})


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

@app.get("/", summary="API info", description="Returns the API name, version and available endpoints.")
async def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}

@app.get("/health", summary="Health check", description="Returns ok when the server is running.")
async def health():
    return {"status": "ok"}

@app.get("/tasks", summary="List tasks", description="Returns every task.")
async def get_tasks():
    conn = get_db()
    rows = conn.execute("SELECT id, title, done FROM tasks ORDER BY id").fetchall()
    conn.close()
    return [row_to_task(row) for row in rows]

@app.get("/tasks/{id}", summary="Get a task", description="Returns one task by id, or 404 if it does not exist.")
async def get_tasks_id(id: int):
    task = fetch_task(id)
    if task is None:
        return not_found(id)
    return task

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

    conn = get_db()
    with conn:
        cursor = conn.execute("INSERT INTO tasks (title, done) VALUES (?, 0)", (title.strip(),))
        new_id = cursor.lastrowid
    conn.close()
    return fetch_task(new_id)


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
    if fetch_task(id) is None:
        return not_found(id)

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

    conn = get_db()
    with conn:
        if "title" in body:
            conn.execute("UPDATE tasks SET title = ? WHERE id = ?", (body["title"].strip(), id))
        if "done" in body:
            conn.execute("UPDATE tasks SET done = ? WHERE id = ?", (int(body["done"]), id))
    conn.close()
    return fetch_task(id)

@app.delete("/tasks/{id}", status_code=204, summary="Delete a task", description="Removes the task. Returns 204 with an empty body, or 404 for an unknown id.")
async def delete_task(id: int):
    conn = get_db()
    with conn:
        deleted = conn.execute("DELETE FROM tasks WHERE id = ?", (id,)).rowcount
    conn.close()
    if deleted == 0:
        return not_found(id)
    return Response(status_code=204)
