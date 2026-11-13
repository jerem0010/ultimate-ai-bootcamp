
import asyncio
import logging

from app import storage
from app.queue import create_redis_client, dequeue_task
from app.service import process_task


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    # Connexion PostgreSQL.
    await storage.connect_db()

    # Connexion Redis.
    redis = create_redis_client()

    logger.info("Worker started. Waiting for tasks...")

    try:
        while True:
            # Attendre une tâche.
            task_id = await dequeue_task(redis)

            if task_id is None:
                continue

            logger.info("Processing task %s", task_id)

            try:
                # Traiter la tâche avec le cache Redis.
                await process_task(
                    task_id,
                    redis=redis,
                )

                logger.info("Task %s completed", task_id)

            except Exception:
                logger.exception(
                    "Task %s failed",
                    task_id,
                )

    finally:
        await redis.aclose()
        await storage.disconnect_db()


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        pass
