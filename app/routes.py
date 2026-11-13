
from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    Header,
    Response,
)

from app.schemas import TaskRequest, TaskResponse
from app import storage
from app.queue import enqueue_task, get_queue_name
from app.rate_limit import check_rate_limit


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
    return {
        "models": ["GPT", "Claude", "Gemini", "Llama", "Mistral"]
    }


@router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=201,
)
async def create_task(
    task_request: TaskRequest,
    request: Request,
    response: Response,
    idempotency_key: str | None = Header(
        default=None,
        min_length=1,
        max_length=128,
    ),
):
    redis = request.app.state.redis

    # 1. Rate Limiting.
    client_ip = (
        request.client.host
        if request.client
        else "unknown"
    )

    rate_key = (
        f"{get_queue_name()}:rate:{client_ip}"
    )

    allowed, ttl = await check_rate_limit(
        redis,
        rate_key,
    )

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many requests",
            headers={
                "Retry-After": str(max(ttl, 1)),
            },
        )

    # 2. Création idempotente si une clé est fournie.
    if idempotency_key is not None:
        task, created = await storage.save_idempotent_task(
            model=task_request.model,
            prompt=task_request.prompt,
            max_tokens=task_request.max_tokens,
            idempotency_key=idempotency_key,
        )

        if not created:
            # Vérifier que la clé n'est pas réutilisée
            # pour une requête différente.
            if (
                task["model"] != task_request.model
                or task["prompt"] != task_request.prompt
                or task["max_tokens"] != task_request.max_tokens
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Idempotency key already used with different parameters",
                )

            response.status_code = 200

            return task

    # 3. Création normale sans clé.
    else:
        task = await storage.save_task(
            model=task_request.model,
            prompt=task_request.prompt,
            max_tokens=task_request.max_tokens,
        )

    # 4. Seules les nouvelles tâches sont mises en queue.
    await enqueue_task(redis, task["task_id"])

    return task


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
)
async def read_task(task_id: int):
    task = await storage.get_task(task_id)

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    return task
