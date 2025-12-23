from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import engine, Base, SessionLocal
from database.models import PaymentActor, PaymentPurpose
from routes import orders, dispatch, payments, users
# --- FONCTION DE SEEDING ---
async def seed_data(db: AsyncSession):
    # 1. Acteurs
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

    # 2. Motifs (Purposes) - Doit inclure 'active'
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

# --- LIFECYCLE MANAGEMENT ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # FORCE LA RÉINITIALISATION (À NE FAIRE QU'UNE FOIS)
    async with engine.begin() as conn:
        # On supprime tout pour être sûr que 'active' soit créé
        await conn.run_sync(Base.metadata.drop_all) 
        await conn.run_sync(Base.metadata.create_all)
    
    async with SessionLocal() as db:
        await seed_data(db)
        
    print("🚀 Yobulma API: Base de données réinitialisée avec succès.")
    yield

# --- APPLICATION CONFIGURATION ---
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
app.include_router(dispatch.router)
app.include_router(payments.router)
app.include_router(users.router) # À décommenter après création du fichier

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
