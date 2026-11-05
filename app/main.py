from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import storage
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gère le cycle de vie de FastAPI.

    Avant yield : initialisation.
    Après yield : nettoyage.
    """

    # Ouvre le pool PostgreSQL au démarrage du serveur.
    await storage.connect_db()

    try:
        # FastAPI commence à accepter les requêtes HTTP.
        yield

    finally:
        # Ferme le pool à l'arrêt du serveur.
        await storage.disconnect_db()


# Crée l'application et associe son cycle de vie.
app = FastAPI(lifespan=lifespan)

# Enregistre toutes les routes définies dans routes.py.
app.include_router(router)