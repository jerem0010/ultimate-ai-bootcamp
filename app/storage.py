import os
import asyncpg


# Variable contenant le pool partagé par l'application.
# None signifie que la base n'est pas encore connectée.
pool: asyncpg.Pool | None = None


async def connect_db():
    """
    Initialise le pool de connexions au démarrage de FastAPI.
    """
    global pool

    # Lit l'URL PostgreSQL depuis une variable d'environnement.
    # Cela évite d'écrire le mot de passe dans le code source.
    database_url = os.environ["DATABASE_URL"]

    # Crée le pool avec 1 à 5 connexions réutilisables.
    pool = await asyncpg.create_pool(
        dsn=database_url,
        min_size=1,
        max_size=5,
    )


async def disconnect_db():
    """
    Ferme le pool lorsque FastAPI s'arrête.
    """
    global pool

    if pool is not None:
        await pool.close()
        pool = None


def get_pool() -> asyncpg.Pool:
    """
    Retourne le pool actif ou signale qu'il n'est pas initialisé.
    """
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    return pool


async def save_task(model: str, prompt: str):
    """
    Insère une nouvelle tâche dans PostgreSQL
    et retourne la ligne créée.
    """

    # Emprunte une connexion pendant la requête SQL.
    async with get_pool().acquire() as conn:

        # INSERT crée une ligne.
        # RETURNING récupère l'ID et les autres champs générés.
        # $1 et $2 sont des paramètres SQL sécurisés.
        row = await conn.fetchrow(
            """
            INSERT INTO tasks (model, prompt)
            VALUES ($1, $2)
            RETURNING task_id, model, prompt, status
            """,
            model,
            prompt,
        )

        # Convertit le Record PostgreSQL en dictionnaire Python.
        return dict(row)


async def get_task(task_id: int):
    """
    Recherche une tâche par son identifiant.
    Retourne None si elle n'existe pas.
    """

    async with get_pool().acquire() as conn:

        # WHERE limite la recherche à un identifiant précis.
        row = await conn.fetchrow(
            """
            SELECT task_id, model, prompt, status
            FROM tasks
            WHERE task_id = $1
            """,
            task_id,
        )

        return dict(row) if row else None


async def update_status(task_id: int, status: str):
    """
    Modifie le statut d'une tâche existante.
    """

    async with get_pool().acquire() as conn:

        # Met à jour uniquement la tâche demandée.
        await conn.execute(
            """
            UPDATE tasks
            SET status = $1
            WHERE task_id = $2
            """,
            status,
            task_id,
        )