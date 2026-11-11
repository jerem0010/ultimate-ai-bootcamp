
import asyncio
import os

import asyncpg
import pytest
from fastapi.testclient import TestClient

from app.main import app


# ============================================================
# DATABASE SETUP
# ============================================================

async def reset_test_database():
    """
    Vide la table tasks dans la base PostgreSQL de test.

    TRUNCATE : supprime toutes les lignes.
    RESTART IDENTITY : réinitialise les IDs à 1.
    """

    # Récupère l'URL de la base réservée aux tests.
    database_url = os.environ["TEST_DATABASE_URL"]

    # Ouvre une connexion asynchrone à PostgreSQL.
    conn = await asyncpg.connect(database_url)

    try:
        # Supprime les anciennes tâches avant chaque test.
        await conn.execute(
            "TRUNCATE TABLE tasks RESTART IDENTITY"
        )

    finally:
        # Ferme la connexion même si une erreur survient.
        await conn.close()


# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture
def client(monkeypatch):
    """
    Crée un client FastAPI isolé pour chaque test.

    - PostgreSQL : base de test
    - Redis      : queue de test
    - Nettoyage automatique de la queue
    """

    database_url = os.environ.get("DATABASE_URL")
    test_database_url = os.environ.get("TEST_DATABASE_URL")

    if not database_url or not test_database_url:
        raise RuntimeError(
            "DATABASE_URL and TEST_DATABASE_URL must be configured"
        )

    if database_url == test_database_url:
        raise RuntimeError(
            "Test database must be separate from development database"
        )

    # Configure les ressources de test avant de lancer FastAPI.
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv(
        "REDIS_QUEUE_NAME",
        "ai:tasks:test:queue",
    )

    # Nettoie PostgreSQL avant chaque test.
    asyncio.run(reset_test_database())

    # Nettoie uniquement la queue Redis de test.
    async def clear_test_queue():
        from app.queue import create_redis_client

        redis = create_redis_client()

        try:
            await redis.delete("ai:tasks:test:queue")
        finally:
            await redis.aclose()

    asyncio.run(clear_test_queue())

    # Démarre FastAPI avec la configuration de test.
    with TestClient(app) as test_client:
        yield test_client

    # monkeypatch restaure automatiquement les variables.



# ============================================================
# TASK TESTS
# ============================================================

def test_create_task(client):
    """
    Vérifie que POST /tasks crée une tâche.

    HTTP 201 : ressource créée.
    Le statut initial doit être pending.
    """

    # Envoie une requête HTTP POST avec un corps JSON.
    response = client.post(
        "/tasks",
        json={
            "prompt": "Explain smart contract reentrancy",
            "model": "GPT",
            "max_tokens": 500
        }
    )

    # Vérifie que la création a réussi.
    assert response.status_code == 201

    # La base est vide avant le test : premier ID = 1.
    assert response.json()["task_id"] == 1

    # La réponse POST contient le statut initial.
    assert response.json()["status"] == "pending"


def test_create_and_get_task(client):
    """
    Vérifie qu'une tâche créée peut être récupérée par son ID.
    """

    # Crée une tâche dans PostgreSQL via l'API.
    response = client.post(
        "/tasks",
        json={
            "prompt": "Explain smart contract reentrancy",
            "model": "GPT",
            "max_tokens": 500
        }
    )

    assert response.status_code == 201

    # Récupère l'identifiant généré par PostgreSQL.
    task_id = response.json()["task_id"]

    # Recherche la tâche avec une requête HTTP GET.
    response = client.get(f"/tasks/{task_id}")

    # Vérifie que la tâche existe.
    assert response.status_code == 200

    # Vérifie que les données enregistrées sont correctes.
    assert response.json()["prompt"] == "Explain smart contract reentrancy"


def test_task_starts_pending(client):
    """
    Vérifie que FastAPI crée une tâche sans l'exécuter.

    Le traitement appartient au worker Redis,
    pas au serveur HTTP.
    """

    payload = {
        "prompt": "Explain Ethereum reentrancy",
        "model": "GPT",
        "max_tokens": 500,
    }

    # Crée la tâche via FastAPI.
    response = client.post("/tasks", json=payload)

    assert response.status_code == 201

    task_id = response.json()["task_id"]

    # La tâche doit initialement être en attente.
    assert response.json()["status"] == "pending"

    # Vérifie qu'elle existe bien dans PostgreSQL.
    response = client.get(f"/tasks/{task_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "pending"


# ============================================================
# BASIC ENDPOINT TESTS
# ============================================================

def test_health(client):
    """
    Vérifie que l'API répond correctement sur /health.
    """

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_square(client):
    """
    Vérifie le calcul du carré d'un nombre.
    """

    # Appelle /square avec le nombre 7.
    response = client.get("/square/7")

    assert response.status_code == 200

    # 7² = 49.
    assert response.json() == {"square": 49}


# ============================================================
# ERROR TESTS
# ============================================================

def test_task_not_found(client):
    """
    Vérifie qu'une tâche inexistante retourne HTTP 404.
    """

    # La base est vide, donc l'ID 999 n'existe pas.
    response = client.get("/tasks/999")

    assert response.status_code == 404


def test_invalid_task(client):
    """
    Vérifie la validation Pydantic du prompt.

    Le prompt doit contenir au moins 10 caractères.
    """

    response = client.post(
        "/tasks",
        json={
            "prompt": "short",
            "model": "GPT",
            "max_tokens": 500
        }
    )

    # HTTP 422 : données invalides.
    assert response.status_code == 422


def test_invalid_model(client):
    """
    Vérifie que Pydantic rejette un modèle non autorisé.
    """

    response = client.post(
        "/tasks",
        json={
            "prompt": "Explain Ethereum reentrancy",
            "model": "UnknownAI",
            "max_tokens": 500
        }
    )

    # UnknownAI n'est pas autorisé par le schéma TaskRequest.
    assert response.status_code == 422
