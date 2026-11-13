
import os
import asyncpg


pool: asyncpg.Pool | None = None


async def connect_db():
    global pool

    pool = await asyncpg.create_pool(
        dsn=os.environ["DATABASE_URL"],
        min_size=1,
        max_size=5,
    )


async def disconnect_db():
    global pool

    if pool is not None:
        await pool.close()
        pool = None


def get_pool() -> asyncpg.Pool:
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    return pool


async def save_task(
    model: str,
    prompt: str,
    max_tokens: int = 512,
):
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO tasks (model, prompt, max_tokens)
            VALUES ($1, $2, $3)
            RETURNING task_id, model, prompt,
                      max_tokens, status, result
            """,
            model,
            prompt,
            max_tokens,
        )

        return dict(row)


async def save_idempotent_task(
    model: str,
    prompt: str,
    max_tokens: int,
    idempotency_key: str,
):
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO tasks (
                model, prompt, max_tokens, idempotency_key
            )
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (idempotency_key) DO NOTHING
            RETURNING task_id, model, prompt,
                      max_tokens, status, result
            """,
            model,
            prompt,
            max_tokens,
            idempotency_key,
        )

        # Nouvelle tâche créée.
        if row is not None:
            return dict(row), True

        # La clé existe déjà : récupérer la tâche.
        row = await conn.fetchrow(
            """
            SELECT task_id, model, prompt,
                   max_tokens, status, result
            FROM tasks
            WHERE idempotency_key = $1
            """,
            idempotency_key,
        )

        return dict(row), False


async def get_task(task_id: int):
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT task_id, model, prompt,
                   max_tokens, status, result
            FROM tasks
            WHERE task_id = $1
            """,
            task_id,
        )

        return dict(row) if row else None


async def update_status(task_id: int, status: str):
    async with get_pool().acquire() as conn:
        await conn.execute(
            """
            UPDATE tasks
            SET status = $1
            WHERE task_id = $2
            """,
            status,
            task_id,
        )


async def complete_task(task_id: int, result: str | None):
    async with get_pool().acquire() as conn:
        await conn.execute(
            """
            UPDATE tasks
            SET status = 'completed',
                result = $1
            WHERE task_id = $2
            """,
            result,
            task_id,
        )
