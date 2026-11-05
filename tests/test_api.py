
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
def client():
    """
    Prépare un environnement isolé pour chaque test.

    1. Vérifie les variables d'environnement.
    2. Vide la base de test.
    3. Démarre FastAPI sur cette base.
    4. Restaure la configuration initiale.
    """

    # Base utilisée normalement par l'application.
    database_url = os.environ.get("DATABASE_URL")

    # Base séparée réservée aux tests.
    test_database_url = os.environ.get("TEST_DATABASE_URL")

    # Empêche l'exécution si la configuration est absente.
    if not database_url or not test_database_url:
        raise RuntimeError(
            "DATABASE_URL and TEST_DATABASE_URL must be configured"
        )

    # Sécurité : les tests ne doivent jamais vider la base de développement.
    if database_url == test_database_url:
        raise RuntimeError(
            "Test database must be separate from development database"
        )

    # Réinitialise la base de test avant chaque test.
    asyncio.run(reset_test_database())

    # Redirige temporairement FastAPI vers la base de test.
    os.environ["DATABASE_URL"] = test_database_url

    try:
        # TestClient lance le lifespan de FastAPI :
        # ouverture du pool PostgreSQL au démarrage.
        with TestClient(app) as test_client:
            yield test_client

    finally:
        # Restaure la base de développement après le test.
        os.environ["DATABASE_URL"] = database_url


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


def test_background_task_completed(client):
    """
    Vérifie le traitement asynchrone d'une tâche.

    pending -> running -> completed
    """

    # Prépare les données de la tâche.
    payload = {
        "prompt": "Explain Ethereum reentrancy",
        "model": "GPT",
        "max_tokens": 500
    }

    # Crée la tâche et déclenche son traitement.
    response = client.post("/tasks", json=payload)

    assert response.status_code == 201

    # Récupère l'identifiant de la tâche.
    task_id = response.json()["task_id"]

    # TestClient attend la fin des BackgroundTasks.
    # Le traitement simulé dure environ 2 secondes.
    response = client.get(f"/tasks/{task_id}")

    assert response.status_code == 200

    # Vérifie que PostgreSQL contient le statut final.
    assert response.json()["status"] == "completed"


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
