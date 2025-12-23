from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database.db import engine, Base
from routes import orders

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Création automatique des tables (Utile en dev, à remplacer par Alembic en prod)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="YOBULMA API",
    description="Backend de livraison groupée Dakar",
    version="1.0.0",
    lifespan=lifespan
)

# --- CONFIGURATION CORS ---
# Permet à votre frontend ou mobile de communiquer avec l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production (ex: ["https://yobulma.com"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- INCLUSION DES ROUTERS ---
app.include_router(orders.router)
# Pensez à ajouter : app.include_router(users.router) une fois créé

@app.get("/", tags=["Root"])
def read_root():
    return {
        "status": "online",
        "project": "Yobulma",
        "team": "Nexus Force",
        "environment": "Production"
    }
