from typing import Literal

from pydantic import BaseModel, Field


class TaskRequest(BaseModel):
    """
    Structure attendue lors d'un POST /tasks.

    Pydantic valide automatiquement les champs.
    """

    # Le prompt doit contenir au moins 10 caractères.
    prompt: str = Field(..., min_length=10)

    # Seuls ces trois modèles sont acceptés.
    model: Literal["GPT", "Claude", "Gemini"]

    # Valeur par défaut : 512 tokens.
    # La valeur doit rester entre 1 et 4096.
    max_tokens: int = Field(default=512, ge=1, le=4096)


class TaskResponse(BaseModel):
    """
    Structure de la réponse HTTP d'une tâche.

    FastAPI valide et sérialise la réponse avec ce modèle.
    """

    task_id: int
    model: Literal["GPT", "Claude", "Gemini"]
    prompt: str

    # Le statut doit appartenir à l'une de ces quatre valeurs.
    status: Literal[
        "pending",
        "running",
        "completed",
        "failed",
    ]