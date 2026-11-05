import asyncio

from app import storage


async def process_task(task_id: int):
    """
    Simule le traitement d'une tâche IA.

    Cycle de vie :
    pending -> running -> completed
                       -> failed (si erreur)
    """

    # Recherche la tâche dans PostgreSQL.
    task = await storage.get_task(task_id)

    if task is None:
        raise ValueError(f"Task {task_id} not found")

    # Indique que le traitement commence.
    await storage.update_status(task_id, "running")

    try:
        # Simule un appel à un modèle IA prenant 2 secondes.
        # asyncio.sleep ne bloque pas la boucle événementielle.
        await asyncio.sleep(2)

        # Marque la tâche comme terminée.
        await storage.update_status(task_id, "completed")

    except Exception:
        # En cas d'erreur, conserve un statut failed en base.
        await storage.update_status(task_id, "failed")

        # Propage l'erreur pour faciliter le diagnostic.
        raise