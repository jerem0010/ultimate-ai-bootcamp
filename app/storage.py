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
                      max_tokens, status, result, created_at, updated_at
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
                      max_tokens, status, result, created_at, updated_at
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
                   max_tokens, status, result, created_at, updated_at
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
                   max_tokens, status, result, created_at, updated_at
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
            SET status = $1, updated_at = now()
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
                result = $1, updated_at = now()
            WHERE task_id = $2
            """,
            result,
            task_id,
        )


async def list_tasks(limit: int, before_id: int | None, status: str | None):
    conditions = []
    args = []
    if status is not None:
        args.append(status)
        conditions.append(f"status = ${len(args)}")
    if before_id is not None:
        args.append(before_id)
        conditions.append(f"task_id < ${len(args)}")
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    args.append(limit + 1)
    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            f"""SELECT task_id, model, prompt, max_tokens, status, result,
                       created_at, updated_at
                FROM tasks {where}
                ORDER BY task_id DESC LIMIT ${len(args)}""",
            *args,
        )
    items = [dict(row) for row in rows[:limit]]
    return {"items": items,
            "next_cursor": items[-1]["task_id"] if len(rows) > limit else None}

async def claim_task(task_id: int):
    """
    Réserve atomiquement une tâche pending.

    Si elle est déjà running, completed ou failed,
    aucune ligne n'est modifiée.
    """
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE tasks
            SET status = 'running',
                updated_at = now()
            WHERE task_id = $1
              AND status = 'pending'
            RETURNING *
            """,
            task_id,
        )

        return dict(row) if row else None


async def reset_abandoned_tasks():
    """
    Remet les tâches interrompues en pending.

    Doit uniquement être appelé lorsqu'aucun
    autre worker ne traite de tâches.
    """
    async with get_pool().acquire() as conn:
        await conn.execute(
            """
            UPDATE tasks
            SET status = 'pending',
                updated_at = now()
            WHERE status = 'running'
            """
        )


async def get_pending_task_ids():
    """
    PostgreSQL est notre source de vérité.
    """
    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT task_id
            FROM tasks
            WHERE status = 'pending'
            ORDER BY task_id
            """
        )

        return [row["task_id"] for row in rows]