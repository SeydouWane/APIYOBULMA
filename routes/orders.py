from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload # Important pour l'asynchrone
from typing import List
from uuid import UUID
import secrets

from database.db import get_db
import database.models as models
import models.schemas as schemas

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/", response_model=schemas.OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(order_data: schemas.OrderCreate, db: AsyncSession = Depends(get_db)):
    # 1. Créer la localisation
    db_location = models.GeoLocation(**order_data.delivery_location.model_dump())
    db.add(db_location)
    await db.flush() 

    # 2. Préparer la commande
    generated_otp = str(secrets.randbelow(1000000)).zfill(6)
    
    # On extrait les données sauf la localisation qui est gérée à part
    order_dict = order_data.model_dump(exclude={"delivery_location"})
    
    db_order = models.Order(
        **order_dict,
        delivery_location_id=db_location.id,
        otp=generated_otp,
        tracking_link=f"https://yobulma.com/track/{db_location.id}"
    )

    db.add(db_order)
    
    try:
        await db.commit()
        # Charger la relation pour éviter l'erreur LazyLoad en asynchrone
        result = await db.execute(
            select(models.Order)
            .options(selectinload(models.Order.delivery_location))
            .filter(models.Order.id == db_order.id)
        )
        return result.scalars().first()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Erreur SQL : {str(e)}")

@router.get("/", response_model=List[schemas.OrderOut])
async def list_orders(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    # selectinload permet de récupérer la localisation en une seule requête SQL
    result = await db.execute(
        select(models.Order)
        .options(selectinload(models.Order.delivery_location))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

@router.get("/{order_id}", response_model=schemas.OrderOut)
async def get_order(order_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Order)
        .options(selectinload(models.Order.delivery_location))
        .filter(models.Order.id == order_id)
    )
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    return order
