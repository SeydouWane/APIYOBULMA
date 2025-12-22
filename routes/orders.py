from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from database.db import SessionLocal
import database.models as models
import models.schemas as schemas

router = APIRouter(prefix="/orders", tags=["Orders"])

# Dépendance pour récupérer la session de base de données
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=schemas.OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(order_data: schemas.OrderCreate, db: Session = Depends(get_db)):
    """
    Crée une nouvelle commande avec sa localisation de livraison.
    """
    # 1. Créer la localisation de livraison d'abord
    db_location = models.GeoLocation(
        region=order_data.delivery_location.region,
        area=order_data.delivery_location.area,
        address=order_data.delivery_location.address,
        latitude=order_data.delivery_location.latitude,
        longitude=order_data.delivery_location.longitude
    )
    db.add(db_location)
    db.flush()  # Récupère l'ID de la localisation sans commiter la transaction

    # 2. Préparer les données de la commande
    # Génération d'un OTP simple pour l'exemple (à complexifier en prod)
    import secrets
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
        tracking_link=f"https://yobulma.com/track/{db_location.id}", # Exemple
        status=models.OrderStatus.CREATED
    )

    db.add(db_order)
    
    try:
        db.commit()
        db.refresh(db_order)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erreur lors de la création : {str(e)}")
        
    return db_order

@router.get("/", response_model=List[schemas.OrderOut])
def list_orders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Liste les commandes (avec pagination).
    """
    orders = db.query(models.Order).offset(skip).limit(limit).all()
    return orders

@router.get("/{order_id}", response_model=schemas.OrderOut)
def get_order(order_id: UUID, db: Session = Depends(get_db)):
    """
    Récupère les détails d'une commande spécifique.
    """
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    return order

@router.patch("/{order_id}/status", response_model=schemas.OrderOut)
def update_order_status(order_id: UUID, new_status: models.OrderStatus, db: Session = Depends(get_db)):
    """
    Met à jour le statut d'une commande.
    """
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    
    db_order.status = new_status
    db.commit()
    db.refresh(db_order)
    return db_order