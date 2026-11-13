
import os
from redis.asyncio import Redis


DEFAULT_QUEUE_NAME = "ai:tasks:queue"


def get_queue_name() -> str:
    """
    Retourne la queue Redis de l'environnement actuel.

    Développement : ai:tasks:queue
    Tests         : ai:tasks:test:queue

    La variable est lue à chaque appel.
    """
    return os.environ.get(
        "REDIS_QUEUE_NAME",
        DEFAULT_QUEUE_NAME,
    )


def create_redis_client() -> Redis:
    """
    Crée un client Redis asynchrone.
    """
    return Redis.from_url(
        os.environ.get(
            "REDIS_URL",
            "redis://127.0.0.1:6380/0",
        ),
        decode_responses=True,
    )


async def enqueue_task(
    redis: Redis,
    task_id: int,
    queue_name: str | None = None,
):
    """
    Ajoute une tâche dans Redis.

    LPUSH ajoute l'ID à gauche de la liste.
    """
    name = queue_name if queue_name is not None else get_queue_name()

    await redis.lpush(name, str(task_id))


async def dequeue_task(
    redis: Redis,
    queue_name: str | None = None,
):
    """
    Attend une tâche dans Redis.

    BRPOP retire un élément à droite.
    Avec LPUSH + BRPOP, on obtient une queue FIFO.
    """
    name = queue_name if queue_name is not None else get_queue_name()

    item = await redis.brpop(name, timeout=1)

    if item is None:
        return None

    _, task_id = item

    return int(task_id)

def get_processing_queue_name() -> str:
    return f"{get_queue_name()}:processing"


async def reserve_task(redis: Redis) -> int | None:
    """
    Déplace atomiquement une tâche de la queue
    principale vers la queue de traitement.
    """
    item = await redis.blmove(
        get_queue_name(),
        get_processing_queue_name(),
        timeout=1,
        src="RIGHT",
        dest="LEFT",
    )

    return int(item) if item is not None else None


async def acknowledge_task(
    redis: Redis,
    task_id: int,
):
    """
    Supprime la tâche de la queue de traitement
    après enregistrement de son état final.
    """
    await redis.lrem(
        get_processing_queue_name(),
        1,
        str(task_id),
    )


async def recover_reserved_tasks(redis: Redis):
    """
    Replace les tâches abandonnées dans la queue
    principale. À utiliser uniquement après avoir
    obtenu le verrou exclusif du worker.
    """
    while True:
        item = await redis.lmove(
            get_processing_queue_name(),
            get_queue_name(),
            "RIGHT",
            "LEFT",
        )

        if item is None:
            break

