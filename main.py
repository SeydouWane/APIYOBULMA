from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database.db import engine, Base
from routes import orders, dispatch, payments # dispatch et payments à créer

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Création automatique des tables
    # Note: En production avec Docker/Kubernetes, on utilisera 'alembic upgrade head'
    async with engine.begin() as conn:
        # Cette commande crée les tables et les types ENUM PostgreSQL s'ils n'existent pas
        await conn.run_sync(Base.metadata.create_all)
    
    print("🚀 Yobulma API: Base de données synchronisée et prête.")
    yield
    # Logique de fermeture (ex: fermer les connexions Redis ou clients HTTP) si nécessaire
    print("🛑 Yobulma API: Arrêt en cours...")

app = FastAPI(
    title="YOBULMA API",
    description="Backend de gestion logistique et financière pour la livraison au Sénégal",
    version="1.1.0",
    lifespan=lifespan
)

# --- CONFIGURATION CORS ---
# Crucial pour permettre les appels depuis l'application Flutter et le Dashboard React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En prod, remplacer par les domaines spécifiques
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- INCLUSION DES ROUTERS ---
# On centralise ici toutes les briques du système
app.include_router(orders.router)
# app.include_router(dispatch.router)  # Pour la gestion des Batches et de l'optimisation
# app.include_router(payments.router)  # Pour la gestion des transactions et des dettes
# app.include_router(users.router)     # Pour l'authentification et les profils agents

@app.get("/", tags=["Root"])
def read_root():
    """Vérification rapide de l'état du système."""
    return {
        "status": "online",
        "project": "Yobulma",
        "version": "1.1.0",
        "region": "Dakar, Senegal",
        "environment": "Development/Testing"
    }

