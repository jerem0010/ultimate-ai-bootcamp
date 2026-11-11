
import asyncio

from app import storage
from app.queue import dequeue_task
from app.service import process_task

# Réutilise la fixture pytest du fichier test_api.
from test_api import client


def test_redis_worker_pipeline(client):
    """
    Vérifie le pipeline complet :

    1. FastAPI crée une tâche.
    2. PostgreSQL stocke son statut pending.
    3. Redis reçoit l'ID.
    4. Le worker traite la tâche.
    5. PostgreSQL contient completed.
    """

    # 1. Créer une tâche via HTTP.
    response = client.post(
        "/tasks",
        json={
            "prompt": "Explain Ethereum reentrancy",
            "model": "GPT",
            "max_tokens": 500,
        },
    )

    assert response.status_code == 201

    task_id = response.json()["task_id"]
    assert response.json()["status"] == "pending"

    # 2. Exécuter la logique du worker sur la boucle
    # événementielle de FastAPI.
    async def run_worker_once():
        redis = client.app.state.redis

        queued_id = await dequeue_task(redis)

        assert queued_id == task_id

        await process_task(queued_id)

    # TestClient possède son propre portail AnyIO.
    # On utilise ce portail plutôt que asyncio.run().
    client.portal.call(run_worker_once)

    # 3. Vérifier le statut final via HTTP.
    response = client.get(f"/tasks/{task_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
