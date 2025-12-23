from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database.db import engine, Base

# Importez uniquement ce qui existe physiquement dans le dossier /routes
from routes import orders 
# Les autres seront importés ici au fur et à mesure de leur création :
# from routes import dispatch, payments, users

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Synchronisation des modèles avec la DB (Utile en Dev/Render Free tier)
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
# N'incluez que les routeurs dont l'import a réussi plus haut
app.include_router(orders.router)

# Ces lignes restent commentées tant que les fichiers routes/dispatch.py etc. ne sont pas créés
# app.include_router(dispatch.router)  
# app.include_router(payments.router)  
# app.include_router(users.router)

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
