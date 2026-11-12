
import asyncio

from app import storage


async def execute_ai_task(task: dict):
    """
    Simule un appel à un fournisseur IA.
    """
    await asyncio.sleep(2)


async def process_task(task_id: int):
    """
    Simule le traitement d'une tâche IA.

    Cycle de vie :
    pending -> running -> completed
                       -> failed (si erreur)
    """

    task = await storage.get_task(task_id)

    if task is None:
        raise ValueError(f"Task {task_id} not found")

    await storage.update_status(task_id, "running")

    try:
        await execute_ai_task(task)

        await storage.update_status(task_id, "completed")

    except Exception:
        await storage.update_status(task_id, "failed")

        # Le worker doit être informé de l'erreur.
        raise
