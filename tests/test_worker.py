
import asyncio
import pytest

from app import storage
from app.queue import dequeue_task
from app.service import process_task

# Réutilise la fixture pytest du fichier test_api.
from test_api import client

from app.retry import RetryableError
from unittest.mock import AsyncMock


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



def test_worker_task_failure(client, monkeypatch):
    """
    Vérifie qu'une tâche en erreur passe à failed
    et que l'exception est propagée au worker.
    """

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

    async def failing_ai_task(task):
        raise RuntimeError("AI provider unavailable")

    monkeypatch.setattr(
        "app.service.execute_ai_task",
        failing_ai_task,
    )

    async def run_worker_once():
        redis = client.app.state.redis

        queued_id = await dequeue_task(redis)

        assert queued_id == task_id

        # On s'attend à ce que le service propage l'erreur.
        with pytest.raises(
            RuntimeError,
            match="AI provider unavailable",
        ):
            await process_task(queued_id)

    client.portal.call(run_worker_once)

    # Malgré l'exception, PostgreSQL doit contenir failed.
    response = client.get(f"/tasks/{task_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "failed"


def test_worker_continues_after_failure(client, monkeypatch):
    """
    Vérifie qu'une tâche échouée n'empêche pas
    le traitement de la tâche suivante.
    """

    # Première tâche : elle doit échouer.
    response1 = client.post(
        "/tasks",
        json={
            "prompt": "Explain Ethereum reentrancy",
            "model": "GPT",
            "max_tokens": 500,
        },
    )

    # Deuxième tâche : elle doit réussir.
    response2 = client.post(
        "/tasks",
        json={
            "prompt": "Explain zero knowledge proofs",
            "model": "Gemini",
            "max_tokens": 500,
        },
    )

    assert response1.status_code == 201
    assert response2.status_code == 201

    task_id1 = response1.json()["task_id"]
    task_id2 = response2.json()["task_id"]

    # Simule un fournisseur GPT indisponible.
    async def mock_ai_task(task):
        if task["model"] == "GPT":
            raise RuntimeError("GPT unavailable")

        # Gemini fonctionne normalement.

    monkeypatch.setattr(
        "app.service.execute_ai_task",
        mock_ai_task,
    )

    async def run_worker():
        redis = client.app.state.redis

        # Traite les deux tâches dans l'ordre FIFO.
        for expected_id in [task_id1, task_id2]:
            queued_id = await dequeue_task(redis)

            assert queued_id == expected_id

            try:
                await process_task(queued_id)

            except RuntimeError:
                # L'erreur ne doit pas arrêter la boucle.
                continue

    client.portal.call(run_worker)

    # Vérifie les statuts finaux dans PostgreSQL.
    response1 = client.get(f"/tasks/{task_id1}")
    response2 = client.get(f"/tasks/{task_id2}")

    assert response1.status_code == 200
    assert response2.status_code == 200

    assert response1.json()["status"] == "failed"
    assert response2.json()["status"] == "completed"

def test_worker_retry_success(client, monkeypatch):
    calls = 0

    async def fake_execute_ai_task(task):
        nonlocal calls
        calls += 1

        if calls < 3:
            raise RetryableError("Provider unavailable")

        return "AI response"

    monkeypatch.setattr(
        "app.service.execute_ai_task",
        fake_execute_ai_task,
    )

    monkeypatch.setattr(
        "app.retry.asyncio.sleep",
        AsyncMock(),
    )

    response = client.post(
        "/tasks",
        json={
            "model": "GPT",
            "prompt": "Explain how neural networks work",
            "max_tokens": 100,
        },
    )

    assert response.status_code == 201, response.json()
    task_id = response.json()["task_id"]

    async def run_worker_once():
        queued_id = await dequeue_task(client.app.state.redis)
        assert queued_id == task_id

        await process_task(queued_id)

    client.portal.call(run_worker_once)

    response = client.get(f"/tasks/{task_id}")

    assert response.json()["status"] == "completed"
    assert calls == 3


from uuid import uuid4
from app.cache import build_cache_key


def test_worker_cache_hit(client, monkeypatch):
    calls = 0

    async def fake_execute_ai_task(task):
        nonlocal calls
        calls += 1
        return "Cached AI response"

    monkeypatch.setattr(
        "app.service.execute_ai_task",
        fake_execute_ai_task,
    )

    payload = {
        "model": "GPT",
        "prompt": f"Explain caching {uuid4()}",
        "max_tokens": 100,
    }

    key = build_cache_key(**payload)

    async def run_worker_once(expected_id):
        redis = client.app.state.redis

        queued_id = await dequeue_task(redis)

        assert queued_id == expected_id

        await process_task(
            queued_id,
            redis=redis,
        )

    try:
        # Première tâche : cache MISS.
        response = client.post(
            "/tasks",
            json=payload,
        )

        assert response.status_code == 201, response.json()

        first_id = response.json()["task_id"]

        client.portal.call(
            run_worker_once,
            first_id,
        )

        first = client.get(
            f"/tasks/{first_id}"
        ).json()

        assert first["status"] == "completed"
        assert first["result"] == "Cached AI response"
        assert first["max_tokens"] == 100
        assert calls == 1

        # Deuxième tâche : cache HIT.
        response = client.post(
            "/tasks",
            json=payload,
        )

        assert response.status_code == 201, response.json()

        second_id = response.json()["task_id"]

        assert second_id != first_id

        client.portal.call(
            run_worker_once,
            second_id,
        )

        second = client.get(
            f"/tasks/{second_id}"
        ).json()

        assert second["status"] == "completed"
        assert second["result"] == first["result"]

        # Un seul appel au fournisseur IA.
        assert calls == 1

    finally:
        # Nettoyer la clé de cache du test.
        client.portal.call(
            client.app.state.redis.delete,
            key,
        )
