import asyncio

from app import storage


async def process_task(task_id: int):
    task = storage.get_task(task_id)

    if task is None:
        raise ValueError(f"Task {task_id} not found")

    task["status"] = "running"

    try:
        await asyncio.sleep(2)
        task["status"] = "completed"

    except Exception:
        task["status"] = "failed"
        raise