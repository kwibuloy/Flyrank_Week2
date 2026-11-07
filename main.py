from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

app = FastAPI()

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

@app.get("/")
async def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/tasks")
async def get_tasks():
    return tasks

@app.get("/tasks/{id}")
async def get_tasks_id(id: int):
    for task in tasks:
        if task["id"] == id:
            return task
    return JSONResponse(status_code=404, content={"error": f"Task {id} not found."})  

@app.post("/tasks", status_code=201)
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


@app.put("/tasks/{id}")
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

@app.delete("/tasks/{id}", status_code=204)
async def delete_task(id: int):
    for i, task in enumerate(tasks):
        if task["id"] == id:
            tasks.pop(i)
            return Response(status_code=204)
    return JSONResponse(status_code=404, content={"error": f"Task {id} not found."})
