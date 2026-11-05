
import asyncio
from typing import Literal

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field


app = FastAPI()

# Stockage temporaire en mémoire
tasks = {}
next_task_id = 1


# ---------- MODELS ----------

class TaskRequest(BaseModel):
    prompt: str = Field(..., min_length=10)
    model: Literal["GPT", "Claude", "Gemini"]
    max_tokens: int = Field(default=512, ge=1, le=4096)


class TaskResponse(BaseModel):
    task_id: int
    model: Literal["GPT", "Claude", "Gemini"]
    prompt: str
    status: Literal["pending", "running", "completed", "failed"]


# ---------- BACKGROUND PROCESSING ----------

async def process_task(task_id: int):
    task = tasks.get(task_id)

    if task is None:
        raise ValueError(f"Task {task_id} not found")

    task["status"] = "running"

    try:
        # Simulation d'un appel à un modèle IA
        await asyncio.sleep(2)
        task["status"] = "completed"

    except Exception:
        task["status"] = "failed"
        raise


# ---------- BASIC ENDPOINTS ----------

@app.get("/")
async def root():
    return {"message": "Welcome to my AI API"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/hello/{name}")
async def get_name(name: str):
    return {"message": f"Hello, {name}!"}


@app.get("/square/{number}")
async def square(number: int):
    return {"square": number ** 2}


@app.get("/models")
async def get_models():
    return {"models": ["GPT", "Claude", "Gemini", "Llama", "Mistral"]}


# ---------- TASK ENDPOINTS ----------

@app.post("/tasks", response_model=TaskResponse, status_code=201)
async def create_task(
    request: TaskRequest,
    background_tasks: BackgroundTasks
):
    global next_task_id

    task = {
        "task_id": next_task_id,
        "model": request.model,
        "prompt": request.prompt,
        "status": "pending"
    }

    tasks[next_task_id] = task
    next_task_id += 1

    # Planifier l'exécution après l'envoi de la réponse
    background_tasks.add_task(process_task, task["task_id"])

    return task


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int):
    if task_id not in tasks:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    return tasks[task_id]
