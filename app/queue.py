import os
from redis.asyncio import Redis


# Nom de la liste Redis utilisée comme file de tâches.
QUEUE_NAME = "ai:tasks:queue"


def create_redis_client() -> Redis:
    """
    Crée un client Redis asynchrone.

    decode_responses=True permet de récupérer
    directement des chaînes Python plutôt que des bytes.
    """
    return Redis.from_url(
        os.environ.get(
            "REDIS_URL",
            "redis://127.0.0.1:6379/0",
        ),
        decode_responses=True,
    )


async def enqueue_task(redis: Redis, task_id: int):
    """
    Ajoute un identifiant de tâche à la file Redis.
    """
    await redis.lpush(QUEUE_NAME, str(task_id))


async def dequeue_task(redis: Redis):
    """
    Attend une tâche dans Redis.

    BRPOP est bloquant côté Redis, mais son appel
    asynchrone ne bloque pas la boucle asyncio Python.
    """
    item = await redis.brpop(QUEUE_NAME, timeout=1)

    # None signifie qu'aucune tâche n'est arrivée.
    if item is None:
        return None

    # BRPOP renvoie (nom_de_liste, valeur).
    _, task_id = item

    return int(task_id)