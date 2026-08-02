"""
Task API — a Postgres-backed CRUD API built with FastAPI.

FlyRank Internship · Backend Track · W3 · A3 — Containerize your stack

Run with:
    docker compose up

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
from database import get_connection, init_db

app = FastAPI(
    title="Task API",
    version="1.0",
    description="A tiny Postgres-backed to-do list API."
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0]
    message = first_error.get("msg", "Invalid request body")
    return JSONResponse(status_code=400, content={"error": message})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


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
# Root and health
# ---------------------------------------------------------------------------

@app.get("/", summary="API info")
def read_root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health", summary="Health check")
def health_check():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

@app.get("/tasks", response_model=List[Task], summary="List all tasks")
def list_tasks():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/tasks/{task_id}", response_model=Task, summary="Get a single task")
def get_task(task_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return dict(row)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@app.post("/tasks", response_model=Task, status_code=201, summary="Create a task")
def create_task(payload: TaskCreate):
    conn = get_connection()
    row = conn.execute(
        "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING *",
        (payload.title.strip(), False)
    ).fetchone()
    conn.commit()
    conn.close()
    return dict(row)


# ---------------------------------------------------------------------------
# Update & Delete
# ---------------------------------------------------------------------------

@app.put("/tasks/{task_id}", response_model=Task, summary="Update a task")
def update_task(task_id: int, payload: TaskUpdate):
    if payload.title is None and payload.done is None:
        raise HTTPException(status_code=400, detail="Provide at least one of: title, done")

    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    new_title = payload.title.strip() if payload.title is not None else row["title"]
    new_done = payload.done if payload.done is not None else row["done"]

    conn.execute(
        "UPDATE tasks SET title = %s, done = %s WHERE id = %s",
        (new_title, new_done, task_id)
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()
    conn.close()
    return dict(updated)


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    conn.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    conn.commit()
    conn.close()
    return Response(status_code=204)