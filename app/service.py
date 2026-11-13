
import asyncio
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app import storage
from app.retry import retry
from app.cache import (
    build_cache_key,
    get_cached_response,
    cache_response,
)


logger = logging.getLogger(__name__)


async def execute_ai_task(task: dict) -> str:
    # Simulation d'un appel à un fournisseur IA.
    await asyncio.sleep(2)

    return (
        f"Response from {task['model']}: "
        f"{task['prompt']}"
    )


async def process_task(
    task_id: int,
    redis: Redis | None = None,
):
    # 1. Récupérer la tâche.
    task = await storage.claim_task(task_id)

    if task is None:
        logger.info(
            "Task %s skipped: missing or already claimed",
            task_id,
        )
        return

    # 2. Passer la tâche en running.
    await storage.update_status(task_id, "running")

    try:
        # 3. Construire la clé de cache.
        key = build_cache_key(
            model=task["model"],
            prompt=task["prompt"],
            max_tokens=task["max_tokens"],
        )

        result = None

        # 4. Vérifier si la réponse existe dans Redis.
        if redis is not None:
            try:
                result = await get_cached_response(
                    redis,
                    key,
                )

            except RedisError:
                logger.warning("Cache read failed")

        # 5. Cache MISS : générer une réponse.
        if result is None:
            logger.info("Cache MISS: task %s", task_id)

            result = await retry(
                lambda: execute_ai_task(task),
                max_attempts=3,
                base_delay=1.0,
                max_delay=10.0,
                jitter=True,
            )

            # 6. Enregistrer la réponse dans Redis.
            if redis is not None and result is not None:
                try:
                    await cache_response(
                        redis,
                        key,
                        result,
                    )

                except RedisError:
                    logger.warning("Cache write failed")

        # Cache HIT : aucune génération nécessaire.
        else:
            logger.info("Cache HIT: task %s", task_id)

        # 7. Enregistrer le résultat dans PostgreSQL.
        await storage.complete_task(task_id, result)

    except Exception:
        await storage.update_status(task_id, "failed")
        raise
