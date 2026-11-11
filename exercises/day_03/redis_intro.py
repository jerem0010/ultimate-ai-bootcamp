import asyncio
from redis.asyncio import Redis


async def main():
    """
    Découvre les commandes Redis de base :
    SET, GET, LPUSH et BRPOP.
    """

    # Connexion au Redis local exposé par Docker.
    redis = Redis(
        host="127.0.0.1",
        port=6380,
        decode_responses=True,
    )

    try:
        # SET enregistre une paire clé/valeur.
        await redis.set("bootcamp:day", "3")

        # GET récupère la valeur associée à la clé.
        day = await redis.get("bootcamp:day")
        print("Day:", day)

        # LPUSH ajoute des éléments à gauche d'une liste.
        await redis.lpush("demo:queue", "task-1")
        await redis.lpush("demo:queue", "task-2")

        # BRPOP retire un élément à droite de la liste.
        # timeout=1 attend au maximum une seconde.
        item = await redis.brpop("demo:queue", timeout=1)
        print("First task:", item)

    finally:
        # Ferme les connexions Redis.
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())