
import asyncio
import logging
import time

from app import storage
from app.queue import (
    create_redis_client,
    enqueue_task,
    get_queue_name,
    reserve_task,
    acknowledge_task,
    recover_reserved_tasks,
)
from app.service import process_task


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RECOVERY_INTERVAL = 30


async def reconcile_pending_tasks(redis):
    """
    Réconcilie PostgreSQL et Redis.

    Une tâche pending présente en base mais absente
    de Redis est remise dans la queue.
    """
    pending_ids = await storage.get_pending_task_ids()

    queued_ids = set(
        await redis.lrange(get_queue_name(), 0, -1)
    )

    for task_id in pending_ids:
        if str(task_id) not in queued_ids:
            await enqueue_task(redis, task_id)
            logger.info("Recovered task %s", task_id)


async def recover_tasks(redis):
    """
    Récupération après interruption du worker.
    """
    await storage.reset_abandoned_tasks()
    await recover_reserved_tasks(redis)
    await reconcile_pending_tasks(redis)


async def run_worker_once(redis):
    task_id = await reserve_task(redis)

    if task_id is None:
        return False

    try:
        await process_task(task_id, redis=redis)

    except Exception:
        logger.exception("Task %s failed", task_id)

    # Vérifier que PostgreSQL contient bien un état
    # final avant de supprimer le message Redis.
    task = await storage.get_task(task_id)

    if task is None or task["status"] in (
        "completed",
        "failed",
    ):
        await acknowledge_task(redis, task_id)

    else:
        # Une erreur d'infrastructure peut empêcher
        # l'enregistrement du statut final.
        # On conserve le message pour récupération.
        raise RuntimeError(
            f"Task {task_id} has no terminal state"
        )

    return True


async def main():
    await storage.connect_db()
    redis = None

    try:
        redis = create_redis_client()

        # Connexion dédiée : le verrou appartient
        # à cette session PostgreSQL.
        async with storage.get_pool().acquire() as lock_conn:

            lock_key = f"worker:{get_queue_name()}"

            acquired = await lock_conn.fetchval(
                """
                SELECT pg_try_advisory_lock(
                    hashtextextended($1, 0)
                )
                """,
                lock_key,
            )

            if not acquired:
                raise RuntimeError(
                    "Another worker is already active"
                )

            try:
                await recover_tasks(redis)

                logger.info("Reliable worker started")

                last_recovery = time.monotonic()

                while True:
                    # Vérifier que la session détenant
                    # le verrou est toujours active.
                    await lock_conn.fetchval("SELECT 1")

                    if (
                        time.monotonic() - last_recovery
                        >= RECOVERY_INTERVAL
                    ):
                        await reconcile_pending_tasks(redis)
                        last_recovery = time.monotonic()

                    await run_worker_once(redis)

            finally:
                if not lock_conn.is_closed():
                    await lock_conn.fetchval(
                        """
                        SELECT pg_advisory_unlock(
                            hashtextextended($1, 0)
                        )
                        """,
                        lock_key,
                    )

    finally:
        if redis is not None:
            await redis.aclose()

        await storage.disconnect_db()


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        pass
