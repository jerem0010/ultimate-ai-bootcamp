import asyncio
import asyncpg


async def main():
    """
    Se connecte à PostgreSQL et exécute trois types
    de requêtes : fetch, fetchval et fetchrow.
    """

    # Ouvre une connexion asynchrone à PostgreSQL.
    # 5433 = port exposé sur ton Mac par Docker.
    conn = await asyncpg.connect(
        user="ai_user",
        password="ai_password",
        database="ai_tasks",
        host="127.0.0.1",
        port=5433,
    )

    try:
        # fetch() récupère plusieurs lignes.
        # $1 représente le premier paramètre SQL.
        pending = await conn.fetch(
            "SELECT * FROM tasks WHERE status = $1",
            "pending",
        )

        # asyncpg renvoie des Record :
        # dict(row) les transforme en dictionnaires Python.
        print("PENDING:", [dict(row) for row in pending])

        # fetchval() récupère une seule valeur.
        # Ici, le nombre total de tâches.
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM tasks"
        )
        print("TOTAL:", count)

        # fetchrow() récupère une seule ligne ou None.
        # On recherche la tâche dont l'identifiant est 1.
        task = await conn.fetchrow(
            "SELECT * FROM tasks WHERE task_id = $1",
            1,
        )

        print("TASK 1:", dict(task) if task else None)

    finally:
        # Ferme la connexion même si une requête échoue.
        await conn.close()


if __name__ == "__main__":
    # Crée et exécute la boucle événementielle asyncio.
    asyncio.run(main())