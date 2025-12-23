from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database.db import engine, Base

# 1. IMPORTS DES ROUTES (Assure-toi que les fichiers existent dans /routes)
from routes import orders, dispatch, payments
# from routes import users # À décommenter uniquement quand users.py sera créé

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Synchronisation automatique des tables et des ENUMS
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("🚀 Yobulma API: Base de données synchronisée et prête.")
    yield
    print("🛑 Yobulma API: Arrêt en cours...")

app = FastAPI(
    title="YOBULMA API",
    description="Backend de gestion logistique et financière pour la livraison au Sénégal",
    version="1.1.0",
    lifespan=lifespan
)

# --- CONFIGURATION CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- INCLUSION DES ROUTERS ---
app.include_router(orders.router)
app.include_router(dispatch.router)   # OK : on l'a créé ensemble
app.include_router(payments.router)   # OK : on l'a créé ensemble
# app.include_router(users.router)    # Garder commenté jusqu'à création du fichier

@app.get("/", tags=["Root"])
def read_root():
    """Vérification rapide de l'état du système."""
    return {
        "status": "online",
        "project": "Yobulma",
        "version": "1.1.0",
        "region": "Dakar, Senegal",
        "environment": "Production/Render"
    }
