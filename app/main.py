from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import storage
from app.queue import create_redis_client
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialise PostgreSQL et Redis au démarrage
    et ferme les connexions à l'arrêt.
    """

    # Initialise PostgreSQL.
    await storage.connect_db()

    try:
        # Initialise le client Redis.
        app.state.redis = create_redis_client()

        # Vérifie immédiatement la connexion à Redis.
        await app.state.redis.ping()

        # L'application peut maintenant traiter les requêtes.
        yield

    finally:
        # Ferme Redis, puis PostgreSQL.
        if hasattr(app.state, "redis"):
            await app.state.redis.aclose()

        await storage.disconnect_db()


app = FastAPI(lifespan=lifespan)
app.include_router(router)