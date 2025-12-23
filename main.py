from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import engine, Base, SessionLocal
from database.models import PaymentActor, PaymentPurpose
# Importation de tous les modules de routes
from routes import orders, dispatch, payments, users, auth 

# --- FONCTION DE SEEDING (Données de base) ---
async def seed_data(db: AsyncSession):
    """Initialise les tables de référence essentielles au système financier."""
    # 1. Configuration des Acteurs de paiement
    actors_data = [
        {"code": "CLIENT", "description": "Celui qui paie la commande"},
        {"code": "SELLER", "description": "Le marchand qui vend le produit"},
        {"code": "AGENT", "description": "Le livreur qui transporte et collecte"},
        {"code": "PLATFORM", "description": "Yobulma (Commission & Frais)"}
    ]
    for actor in actors_data:
        q = await db.execute(select(PaymentActor).where(PaymentActor.code == actor["code"]))
        if not q.scalar_one_or_none():
            db.add(PaymentActor(**actor))

    # 2. Motifs de paiement (Purposes)
    purposes_data = [
        {"code": "ITEM_PRICE", "description": "Prix produit", "active": True},
        {"code": "DELIVERY_FEE", "description": "Frais livraison", "active": True},
        {"code": "PLATFORM_COMMISSION", "description": "Commission Yobulma", "active": True},
        {"code": "INSURANCE", "description": "Assurance colis", "active": True}
    ]
    for p in purposes_data:
        q = await db.execute(select(PaymentPurpose).where(PaymentPurpose.code == p["code"]))
        if not q.scalar_one_or_none():
            db.add(PaymentPurpose(**p))

    await db.commit()

# --- GESTION DU CYCLE DE VIE (LIFESPAN) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialisation de la base de données
    async with engine.begin() as conn:
        # ATTENTION: drop_all supprime TOUTES les données. 
        # À commenter dès que votre schéma est stable.
        # await conn.run_sync(Base.metadata.drop_all) 
        await conn.run_sync(Base.metadata.create_all)
    
    async with SessionLocal() as db:
        await seed_data(db)
        
    print("🚀 Yobulma API: Système démarré et données de référence synchronisées.")
    yield
    # Nettoyage lors de la fermeture si nécessaire
    print("👋 Fermeture de l'API Yobulma.")

# --- CONFIGURATION DE L'APPLICATION ---
app = FastAPI(
    title="YOBULMA API",
    description="Backend de gestion logistique et financière pour la livraison au Sénégal",
    version="1.1.0",
    lifespan=lifespan
)

# --- CONFIGURATION CORS (Sécurité pour le Frontend) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En production, remplacez par vos domaines spécifiques
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- INCLUSION DES ROUTERS (Endpoints) ---
app.include_router(auth.router)     # Authentification & JWT
app.include_router(users.router)    # Profils & Utilisateurs
app.include_router(orders.router)   # Gestion des commandes
app.include_router(dispatch.router) # Intelligence logistique & Batches
app.include_router(payments.router) # Flux financiers & Retraits

@app.get("/", tags=["Root"])
def read_root():
    """Vérification rapide de l'état du système."""
    return {
        "status": "online",
        "project": "Yobulma",
        "version": "1.1.0",
        "region": "Dakar, Senegal",
        "timestamp": "2025-12-23"
    }
