tasks = {}
next_task_id = 1


def reset_storage():
    global next_task_id
    tasks.clear()
    next_task_id = 1


def save_task(model: str, prompt: str):
    global next_task_id

    task = {
        "task_id": next_task_id,
        "model": model,
        "prompt": prompt,
        "status": "pending"
    }

    tasks[next_task_id] = task
    next_task_id += 1

    return task


def get_task(task_id: int):
    return tasks.get(task_id)