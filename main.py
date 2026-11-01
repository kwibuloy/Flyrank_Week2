from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

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
def create_task(task: dict):
    title = task.get("title")

    if not isinstance(title, str) or title.strip() == "":
        return JSONResponse(status_code=400, content={"error": "title is required and cannot be empty"})

    new_id = max([t["id"]for t in tasks], default=0) + 1

    new_task = {"id": new_id, "title": title.strip(), "done": False}
    tasks.append(new_task)
    return new_task
