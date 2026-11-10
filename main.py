"""App entry point: creates the FastAPI app and maps service errors to HTTP responses.

Start it with:  python -m uvicorn main:app --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

import wiring
from routes import router
from service import InvalidRequest, TaskNotFound


@asynccontextmanager
async def lifespan(app: FastAPI):
    wiring.startup()
    yield
    wiring.shutdown()


app = FastAPI(
    title="Task API",
    version="1.0",
    description="A small to-do API with full CRUD.",
    lifespan=lifespan,
)
app.include_router(router)


@app.exception_handler(TaskNotFound)
async def task_not_found(request: Request, exc: TaskNotFound):
    return JSONResponse(status_code=404, content={"error": str(exc)})


@app.exception_handler(InvalidRequest)
async def invalid_request(request: Request, exc: InvalidRequest):
    return JSONResponse(status_code=400, content={"error": str(exc)})


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # A non-numeric id like /tasks/abc can't match any task, so it's a 404.
    if any(err.get("loc", [None])[0] == "path" for err in exc.errors()):
        return JSONResponse(status_code=404, content={"error": str(TaskNotFound(request.path_params.get("id")))})
    return JSONResponse(status_code=400, content={"error": "invalid request"})
