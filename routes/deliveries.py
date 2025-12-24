from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
from uuid import UUID
import secrets
import uuid  

from database.db import get_db
import database.models as models
import models.schemas as schemas

# Changement du préfixe et des tags pour refléter le nouveau nom
router = APIRouter(prefix="/deliveries", tags=["Deliveries"])

@router.post("/", response_model=schemas.DeliveryOut, status_code=status.HTTP_201_CREATED)
async def create_delivery(delivery_data: schemas.DeliveryCreate, db: AsyncSession = Depends(get_db)):
    """
    Crée une nouvelle livraison Yobulma avec sa localisation.
    Génère automatiquement l'OTP et le lien de suivi.
    """
    # 1. Créer la localisation de livraison en premier
    db_location = models.GeoLocation(**delivery_data.delivery_location.model_dump())
    db.add(db_location)
    await db.flush()  

    # 2. Préparer les données de la livraison
    generated_otp = str(secrets.randbelow(1000000)).zfill(6)
    
    # Extraction des données du schéma (exclusion de la localisation déjà gérée)
    delivery_dict = delivery_data.model_dump(exclude={"delivery_location"})
    
    # Utilisation du modèle Delivery
    db_delivery = models.Delivery(
        **delivery_dict,
        delivery_location_id=db_location.id,
        otp=generated_otp,
        tracking_link=f"https://yobulma.com/track/{uuid.uuid4()}"
    )

    db.add(db_delivery)
    
    try:
        await db.commit()
        
        # 3. Rechargement avec relations pour la réponse
        result = await db.execute(
            select(models.Delivery)
            .options(
                selectinload(models.Delivery.delivery_location),
                selectinload(models.Delivery.seller)
            )
            .filter(models.Delivery.id == db_delivery.id)
        )
        return result.scalars().first()
        
    except Exception as e:
        await db.rollback()
        print(f"DEBUG ERROR: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Erreur lors de la création de la livraison : {str(e)}"
        )

@router.get("/", response_model=List[schemas.DeliveryOut])
async def list_deliveries(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """
    Liste les livraisons avec pagination.
    """
    result = await db.execute(
        select(models.Delivery)
        .options(selectinload(models.Delivery.delivery_location))
        .offset(skip)
        .limit(limit)
        .order_by(models.Delivery.created_at.desc())
    )
    return result.scalars().all()

@router.get("/{delivery_id}", response_model=schemas.DeliveryOut)
async def get_delivery(delivery_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Récupère les détails d'une livraison spécifique.
    """
    result = await db.execute(
        select(models.Delivery)
        .options(selectinload(models.Delivery.delivery_location))
        .filter(models.Delivery.id == delivery_id)
    )
    delivery = result.scalars().first()
    
    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Livraison non trouvée"
        )
    return delivery

@router.patch("/{delivery_id}/status", response_model=schemas.DeliveryOut)
async def update_delivery_status(
    delivery_id: UUID, 
    new_status: models.DeliveryStatus, 
    db: AsyncSession = Depends(get_db)
):
    """
    Met à jour le statut d'une livraison.
    """
    result = await db.execute(select(models.Delivery).filter(models.Delivery.id == delivery_id))
    delivery = result.scalars().first()
    
    if not delivery:
        raise HTTPException(status_code=404, detail="Livraison non trouvée")
    
    delivery.status = new_status
    await db.commit()
    
    result = await db.execute(
        select(models.Delivery)
        .options(selectinload(models.Delivery.delivery_location))
        .filter(models.Delivery.id == delivery_id)
    )
    return result.scalars().first()

@router.post("/{delivery_id}/verify-otp")
async def verify_delivery_otp(delivery_id: UUID, otp: str, db: AsyncSession = Depends(get_db)):
    """
    Vérifie l'OTP et confirme la livraison finale.
    """
    # Utilisation de models.Delivery au lieu de Order
    result = await db.execute(select(models.Delivery).filter(models.Delivery.id == delivery_id))
    delivery = result.scalars().first()

    if not delivery:
        raise HTTPException(status_code=404, detail="Livraison non trouvée")

    if delivery.otp != otp:
        raise HTTPException(status_code=400, detail="Code OTP invalide")
    
    delivery.status = models.DeliveryStatus.DELIVERED
    
    await db.commit()
    return {"message": "Livraison confirmée avec succès"}
