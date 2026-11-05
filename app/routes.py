from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.schemas import TaskRequest, TaskResponse
from app import storage
from app.service import process_task


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
    request: TaskRequest,
    background_tasks: BackgroundTasks,
):
    """
    Crée une tâche en base et programme son traitement.

    HTTP 201 : ressource créée.
    """

    # Enregistre la tâche avec le statut pending.
    task = await storage.save_task(
        model=request.model,
        prompt=request.prompt,
    )

    # Programme le traitement après l'envoi de la réponse HTTP.
    background_tasks.add_task(
        process_task,
        task["task_id"],
    )

    # Retourne immédiatement les informations de la tâche.
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