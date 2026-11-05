from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.schemas import TaskRequest, TaskResponse
from app import storage
from app.service import process_task


router = APIRouter()


@router.get("/")
async def root():
    return {"message": "Welcome to my AI API"}


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/hello/{name}")
async def get_name(name: str):
    return {"message": f"Hello, {name}!"}


@router.get("/square/{number}")
async def square(number: int):
    return {"square": number ** 2}


@router.get("/models")
async def get_models():
    return {"models": ["GPT", "Claude", "Gemini", "Llama", "Mistral"]}


@router.post("/tasks", response_model=TaskResponse, status_code=201)
async def create_task(
    request: TaskRequest,
    background_tasks: BackgroundTasks
):
    task = storage.save_task(
        model=request.model,
        prompt=request.prompt
    )

    background_tasks.add_task(process_task, task["task_id"])

    return task


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def read_task(task_id: int):
    task = storage.get_task(task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return task