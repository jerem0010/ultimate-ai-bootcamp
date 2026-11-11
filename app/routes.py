from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.schemas import TaskRequest, TaskResponse
from app import storage
from app.service import process_task

# Request donne accès à l'application et à son client Redis.
from fastapi import Request

# Fonction qui ajoute une tâche à la queue.
from app.queue import enqueue_task


# Regroupe les routes HTTP de l'application.
router = APIRouter()


@router.get("/")
async def root():
    """Endpoint d'accueil de l'API."""
    return {"message": "Welcome to my AI API"}


@router.get("/health")
async def health():
    """Vérifie que le serveur HTTP répond."""
    return {"status": "ok"}


@router.get("/hello/{name}")
async def get_name(name: str):
    """Retourne un message personnalisé."""
    return {"message": f"Hello, {name}!"}


@router.get("/square/{number}")
async def square(number: int):
    """Calcule le carré d'un entier."""
    return {"square": number ** 2}


@router.get("/models")
async def get_models():
    """Liste les modèles IA disponibles dans cette API."""
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
):
    """
    Crée une tâche dans PostgreSQL puis place son ID
    dans Redis pour qu'un worker la traite.
    """

    # 1. Enregistre la tâche avec le statut pending.
    task = await storage.save_task(
        model=task_request.model,
        prompt=task_request.prompt,
    )

    # 2. Récupère le client Redis partagé par FastAPI.
    redis = request.app.state.redis

    # 3. Ajoute l'identifiant dans la file de tâches.
    await enqueue_task(redis, task["task_id"])

    # 4. Retourne immédiatement la tâche au client HTTP.
    return task


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
)
async def read_task(task_id: int):
    """
    Récupère une tâche depuis PostgreSQL.

    HTTP 404 : tâche inexistante.
    """

    # Recherche la tâche dans la base.
    task = await storage.get_task(task_id)

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    return task