"""
Task API — a small in-memory CRUD API built with FastAPI.

FlyRank Internship · Backend Track · W2 · A1 — Build your first CRUD API

Run with:
    uvicorn main:app --reload

Then open:
    http://localhost:8000/          -> API info
    http://localhost:8000/health    -> health check
    http://localhost:8000/docs      -> Swagger UI
"""

from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from typing import Optional, List

app = FastAPI(
    title="Task API",
    version="1.0",
    description="A tiny in-memory to-do list API — the CRUD warm-up project."
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    The assignment asks for 400 Bad Request on invalid input.
    FastAPI's default is 422 — we override it here so POST/PUT with a
    missing or empty title correctly return 400.
    """
    first_error = exc.errors()[0]
    message = first_error.get("msg", "Invalid request body")
    return JSONResponse(status_code=400, content={"error": message})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    FastAPI's default error body is {"detail": "..."}. The assignment
    spec asks for {"error": "..."} instead, so we normalize it here.
    """
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

# ---------------------------------------------------------------------------
# "Database" — just a list in memory. Restart the server and it resets.
# ---------------------------------------------------------------------------

tasks = [
    {"id": 1, "title": "Buy milk", "done": False},
    {"id": 2, "title": "Read FastAPI docs", "done": True},
    {"id": 3, "title": "Build the Task API", "done": False},
]
next_id = 4  # simple counter for new task ids


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------

class TaskCreate(BaseModel):
    title: str

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("title must not be empty")
        return v


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank_if_present(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("title must not be empty")
        return v


class Task(BaseModel):
    id: int
    title: str
    done: bool


# ---------------------------------------------------------------------------
# Stage 1 — root and health
# ---------------------------------------------------------------------------

@app.get("/", summary="API info")
def read_root():
    """Describes what this API is and what it offers."""
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health", summary="Health check")
def health_check():
    """Used to confirm the server is alive."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Stage 2 — Read
# ---------------------------------------------------------------------------

def find_task(task_id: int):
    return next((t for t in tasks if t["id"] == task_id), None)


@app.get("/tasks", response_model=List[Task], summary="List tasks")
def list_tasks(done: Optional[bool] = None, search: Optional[str] = None,
                limit: Optional[int] = None, offset: int = 0):
    """
    Returns all tasks.

    Optional query parameters (stretch goals):
      - done: filter by completion status (?done=true)
      - search: filter by a word in the title (?search=milk)
      - limit / offset: pagination (?limit=2&offset=2)
    """
    result = tasks

    if done is not None:
        result = [t for t in result if t["done"] == done]

    if search:
        result = [t for t in result if search.lower() in t["title"].lower()]

    if offset:
        result = result[offset:]
    if limit is not None:
        result = result[:limit]

    return result


@app.get("/tasks/{task_id}", response_model=Task, summary="Get a single task")
def get_task(task_id: int):
    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


# ---------------------------------------------------------------------------
# Stage 3 — Create
# ---------------------------------------------------------------------------

@app.post("/tasks", response_model=Task, status_code=201, summary="Create a task")
def create_task(payload: TaskCreate):
    global next_id
    new_task = {"id": next_id, "title": payload.title.strip(), "done": False}
    tasks.append(new_task)
    next_id += 1
    return new_task


# ---------------------------------------------------------------------------
# Stage 4 — Update & Delete
# ---------------------------------------------------------------------------

@app.put("/tasks/{task_id}", response_model=Task, summary="Update a task")
def update_task(task_id: int, payload: TaskUpdate):
    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if payload.title is None and payload.done is None:
        raise HTTPException(status_code=400, detail="Provide at least one of: title, done")

    if payload.title is not None:
        task["title"] = payload.title.strip()
    if payload.done is not None:
        task["done"] = payload.done

    return task


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    tasks.remove(task)
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Extras (optional stretch goals)
# ---------------------------------------------------------------------------

@app.get("/stats", summary="Task stats")
def get_stats():
    total = len(tasks)
    done_count = sum(1 for t in tasks if t["done"])
    return {"total": total, "done": done_count, "open": total - done_count}


@app.post("/reset", summary="Reset to the 3 example tasks")
def reset_tasks():
    global tasks, next_id
    tasks = [
        {"id": 1, "title": "Buy milk", "done": False},
        {"id": 2, "title": "Read FastAPI docs", "done": True},
        {"id": 3, "title": "Build the Task API", "done": False},
    ]
    next_id = 4
    return {"message": "Tasks reset to defaults", "tasks": tasks}
