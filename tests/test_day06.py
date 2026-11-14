from uuid import uuid4
from app.cache import build_cache_key

from unittest.mock import AsyncMock

from app import storage
from app.queue import (
    enqueue_task,
    reserve_task,
    acknowledge_task,
    get_processing_queue_name,
)
from app.service import process_task
from app.worker import (
    recover_tasks,
    run_worker_once,
)

from test_api import client


PAYLOAD = {
    "model": "GPT",
    "prompt": "Explain reliable distributed queues",
    "max_tokens": 100,
}


def test_reliable_queue(client):
    task_id = client.post(
        "/tasks", json=PAYLOAD
    ).json()["task_id"]

    async def check():
        redis = client.app.state.redis
        processing = get_processing_queue_name()

        await redis.delete(processing)

        try:
            reserved = await reserve_task(redis)

            assert reserved == task_id
            assert await redis.lrange(
                processing, 0, -1
            ) == [str(task_id)]

            await acknowledge_task(redis, task_id)

            assert await redis.llen(processing) == 0

        finally:
            await redis.delete(processing)

    client.portal.call(check)


def test_worker_recovers_abandoned_task(
    client, monkeypatch
):
    monkeypatch.setattr(
        "app.service.execute_ai_task",
        AsyncMock(return_value="Recovered response"),
    )

    payload = {**PAYLOAD, "prompt": f"Explain reliable queues {uuid4()}"}
    task_id = client.post(
        "/tasks", json=payload
    ).json()["task_id"]

    async def check():
        redis = client.app.state.redis
        processing = get_processing_queue_name()

        await redis.delete(processing)

        try:
            # Simuler un worker qui réserve la tâche.
            assert await reserve_task(redis) == task_id

            task = await storage.claim_task(task_id)
            assert task["status"] == "running"

            # Simuler le redémarrage après un crash.
            await recover_tasks(redis)

            task = await storage.get_task(task_id)
            assert task["status"] == "pending"

            await run_worker_once(redis)

            task = await storage.get_task(task_id)
            assert task["status"] == "completed"
            assert task["result"] == "Recovered response"

            assert await redis.llen(processing) == 0

        finally:
            await redis.delete(processing)
            await redis.delete(build_cache_key(**payload))

    client.portal.call(check)


def test_duplicate_task_is_not_executed_twice(
    client, monkeypatch
):
    execute = AsyncMock(return_value="AI response")

    monkeypatch.setattr(
        "app.service.execute_ai_task",
        execute,
    )

    payload = {**PAYLOAD, "prompt": f"Explain reliable queues {uuid4()}"}
    task_id = client.post(
        "/tasks", json=payload
    ).json()["task_id"]

    async def check():
        redis = client.app.state.redis
        processing = get_processing_queue_name()

        await redis.delete(processing)

        try:
            # Simuler un message Redis dupliqué.
            await enqueue_task(redis, task_id)

            await run_worker_once(redis)
            # Remove cache so only the atomic claim prevents execution.
            await redis.delete(build_cache_key(**payload))
            await run_worker_once(redis)

            task = await storage.get_task(task_id)

            assert task["status"] == "completed"
            assert execute.await_count == 1
            assert await redis.llen(processing) == 0

        finally:
            await redis.delete(processing)
            await redis.delete(build_cache_key(**payload))

    client.portal.call(check)


def test_recover_task_missing_from_redis(client):
    async def check():
        redis = client.app.state.redis
        processing = get_processing_queue_name()

        await redis.delete(processing)

        try:
            # Création directement dans PostgreSQL :
            # aucune insertion dans Redis.
            task = await storage.save_task(**PAYLOAD)

            await recover_tasks(redis)

            reserved = await reserve_task(redis)

            assert reserved == task["task_id"]

            await acknowledge_task(redis, reserved)

        finally:
            await redis.delete(processing)

    client.portal.call(check)
