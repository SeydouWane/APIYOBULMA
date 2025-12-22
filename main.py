from fastapi import FastAPI
from contextlib import asynccontextmanager
from database.db import engine, Base
from routes import orders

# Utilisation du lifespan pour gérer le démarrage et l'arrêt de l'app
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Logique de démarrage : Création des tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Logique d'arrêt si nécessaire (ex: fermer les connexions)

app = FastAPI(
    title="YOBULMA API",
    description="Backend de livraison groupée Dakar",
    lifespan=lifespan # On branche le lifespan ici
)

app.include_router(orders.router)

@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l'API Yobulma - Team Nexus Force"}
