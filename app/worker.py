import asyncio
import logging

from app import storage
from app.queue import create_redis_client, dequeue_task
from app.service import process_task


# Configure l'affichage des logs du worker.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """
    Démarre un worker indépendant de FastAPI.

    Il attend des IDs dans Redis et traite
    les tâches correspondantes dans PostgreSQL.
    """

    # Initialise le pool PostgreSQL du worker.
    await storage.connect_db()

    # Ouvre le client Redis.
    redis = create_redis_client()

    logger.info("Worker started. Waiting for tasks...")

    try:
        while True:
            # Attend une nouvelle tâche dans la queue.
            task_id = await dequeue_task(redis)

            # Aucune tâche disponible : on recommence.
            if task_id is None:
                continue

            logger.info("Processing task %s", task_id)

            try:
                # Exécute la logique métier existante.
                await process_task(task_id)

                logger.info("Task %s completed", task_id)

            except Exception:
                # Logue l'erreur sans arrêter le worker.
                logger.exception("Task %s failed", task_id)

    finally:
        # Libère les connexions lors de l'arrêt.
        await redis.aclose()
        await storage.disconnect_db()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Permet un arrêt propre avec Ctrl+C.
        pass