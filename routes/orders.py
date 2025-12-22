from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from uuid import UUID
import secrets

# On importe get_db depuis database.db (qui utilise SessionLocal de manière asynchrone)
from database.db import get_db
import database.models as models
import models.schemas as schemas

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/", response_model=schemas.OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(order_data: schemas.OrderCreate, db: AsyncSession = Depends(get_db)):
    """
    Crée une nouvelle commande avec sa localisation de livraison (Version Asynchrone).
    """
    # 1. Créer la localisation de livraison
    db_location = models.GeoLocation(
        region=order_data.delivery_location.region,
        area=order_data.delivery_location.area,
        address=order_data.delivery_location.address,
        latitude=order_data.delivery_location.latitude,
        longitude=order_data.delivery_location.longitude
    )
    db.add(db_location)
    await db.flush()  # Récupère l'ID sans commiter

    # 2. Préparer les données de la commande
    generated_otp = str(secrets.randbelow(1000000)).zfill(6)
    
    db_order = models.Order(
        seller_id=order_data.seller_id,
        client_id=order_data.client_id,
        client_name=order_data.client_name,
        client_phone=order_data.client_phone,
        package_description=order_data.package_description,
        package_weight_kg=order_data.package_weight_kg,
        delivery_location_id=db_location.id,
        otp=generated_otp,
        tracking_link=f"https://yobulma.com/track/{db_location.id}",
        status=models.OrderStatus.CREATED
    )

    db.add(db_order)
    
    try:
        await db.commit()
        await db.refresh(db_order)
        # Charger explicitement la location pour le schéma de retour
        await db.refresh(db_order, ["delivery_location"])
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Erreur lors de la création : {str(e)}")
        
    return db_order

@router.get("/", response_model=List[schemas.OrderOut])
async def list_orders(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """
    Liste les commandes avec pagination.
    """
    result = await db.execute(
        select(models.Order).offset(skip).limit(limit)
    )
    orders = result.scalars().all()
    return orders

@router.get("/{order_id}", response_model=schemas.OrderOut)
async def get_order(order_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Récupère les détails d'une commande spécifique.
    """
    result = await db.execute(
        select(models.Order).filter(models.Order.id == order_id)
    )
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    return order

@router.patch("/{order_id}/status", response_model=schemas.OrderOut)
async def update_order_status(order_id: UUID, new_status: models.OrderStatus, db: AsyncSession = Depends(get_db)):
    """
    Met à jour le statut d'une commande.
    """
    result = await db.execute(
        select(models.Order).filter(models.Order.id == order_id)
    )
    db_order = result.scalars().first()
    
    if not db_order:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    
    db_order.status = new_status
    await db.commit()
    await db.refresh(db_order)
    return db_order
