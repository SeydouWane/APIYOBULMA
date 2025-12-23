from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
from uuid import UUID
import secrets

from database.db import get_db
import database.models as models
import models.schemas as schemas

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/", response_model=schemas.OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(order_data: schemas.OrderCreate, db: AsyncSession = Depends(get_db)):
    """
    Crée une nouvelle commande Yobulma avec sa localisation de livraison.
    Génère automatiquement l'OTP et le lien de suivi.
    """
    # 1. Créer la localisation de livraison en premier
    db_location = models.GeoLocation(**order_data.delivery_location.model_dump())
    db.add(db_location)
    await db.flush()  # Récupère l'ID de la localisation sans committer toute la transaction

    # 2. Préparer les données de la commande
    # On génère un OTP sécurisé à 6 chiffres
    generated_otp = str(secrets.randbelow(1000000)).zfill(6)
    
    # Extraction des données du schéma (on exclut delivery_location car traitée manuellement)
    order_dict = order_data.model_dump(exclude={"delivery_location"})
    
    db_order = models.Order(
        **order_dict,
        delivery_location_id=db_location.id,
        otp=generated_otp,
        tracking_link=f"https://yobulma.com/track/{uuid.uuid4()}" # UUID unique pour le tracking
    )

    db.add(db_order)
    
    try:
        await db.commit()
        
        # 3. Recharger l'objet avec ses relations pour la réponse Pydantic
        # En asynchrone, SQLAlchemy ne charge pas les relations automatiquement (Lazy Loading désactivé)
        result = await db.execute(
            select(models.Order)
            .options(
                selectinload(models.Order.delivery_location),
                selectinload(models.Order.seller) # Optionnel: si vous voulez afficher le vendeur
            )
            .filter(models.Order.id == db_order.id)
        )
        return result.scalars().first()
        
    except Exception as e:
        await db.rollback()
        # Log l'erreur réelle en interne pour le debug
        print(f"DEBUG ERROR: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Erreur lors de la création de la commande : {str(e)}"
        )

@router.get("/", response_model=List[schemas.OrderOut])
async def list_orders(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """
    Liste les commandes avec pagination. 
    Charge automatiquement les données de localisation associées.
    """
    result = await db.execute(
        select(models.Order)
        .options(selectinload(models.Order.delivery_location))
        .offset(skip)
        .limit(limit)
        .order_by(models.Order.created_at.desc())
    )
    return result.scalars().all()

@router.get("/{order_id}", response_model=schemas.OrderOut)
async def get_order(order_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Récupère les détails d'une commande spécifique par son ID.
    """
    result = await db.execute(
        select(models.Order)
        .options(selectinload(models.Order.delivery_location))
        .filter(models.Order.id == order_id)
    )
    order = result.scalars().first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Commande non trouvée"
        )
    return order

@router.patch("/{order_id}/status", response_model=schemas.OrderOut)
async def update_order_status(
    order_id: UUID, 
    new_status: models.OrderStatus, 
    db: AsyncSession = Depends(get_db)
):
    """
    Met à jour le statut d'une commande (ex: passage de CREATED à WAITING_FOR_BATCH).
    """
    result = await db.execute(select(models.Order).filter(models.Order.id == order_id))
    order = result.scalars().first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    
    order.status = new_status
    await db.commit()
    
    # Recharger avec relations pour la sortie
    result = await db.execute(
        select(models.Order)
        .options(selectinload(models.Order.delivery_location))
        .filter(models.Order.id == order_id)
    )
    return result.scalars().first()


@router.post("/{order_id}/verify-otp")
async def verify_delivery_otp(order_id: uuid.UUID, otp: str, db: AsyncSession = Depends(get_db)):
    order = await db.get(Order, order_id)
    if order.otp != otp:
        raise HTTPException(status_code=400, detail="Code OTP invalide")
    
    order.status = OrderStatus.DELIVERED
    # Logique de transfert d'argent ici : 
    # Diminuer la dette du livreur -> Augmenter la balance du vendeur
    await db.commit()
    return {"message": "Livraison confirmée avec succès"}
