from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from database.db import get_db
# Changement : Order -> Delivery, OrderStatus -> DeliveryStatus
from database.models import Delivery, Batch, DeliveryStatus, BatchStatus
from models import schemas

router = APIRouter(
    prefix="/dispatch",
    tags=["Dispatch & Logistics"]
)

@router.post("/auto-batch/{area_name}")
async def create_smart_batches(area_name: str, db: AsyncSession = Depends(get_db)):
    """
    Algorithme de groupage : récupère toutes les livraisons WAITING_FOR_BATCH 
    dans une zone et crée des batches optimisés.
    """
    # 1. Récupérer les livraisons éligibles
    # Changement : Order -> Delivery
    query = select(Delivery).where(
        Delivery.status == DeliveryStatus.WAITING_FOR_BATCH,
    )
    result = await db.execute(query)
    deliveries = result.scalars().all()

    if not deliveries:
        return {"message": f"Aucune livraison en attente pour la zone {area_name}"}

    # 2. Logique de groupage
    new_batch = Batch(
        area_name=area_name,
        status=BatchStatus.CREATED,
        delivery_fee=2000.0, 
        max_orders=5
    )
    
    db.add(new_batch)
    await db.flush() 

    for delivery in deliveries[:5]: 
        delivery.batch_id = new_batch.id
        delivery.status = DeliveryStatus.BATCHED
    
    await db.commit()
    
    # Correction du message : new_batch.deliveries au lieu de new_batch.orders
    return {
        "status": "success",
        "message": f"Batch {new_batch.id} créé avec {len(deliveries[:5])} livraisons."
    }

@router.get("/batches/available", response_model=List[schemas.BatchOut])
async def list_available_batches(db: AsyncSession = Depends(get_db)):
    """Liste les batches qui n'ont pas encore de livreur assigné."""
    query = select(Batch).where(Batch.status == BatchStatus.AVAILABLE)
    result = await db.execute(query)
    return result.scalars().all()

@router.patch("/batches/{batch_id}/assign/{agent_id}", response_model=schemas.BatchOut)
async def assign_batch_to_agent(
    batch_id: UUID, 
    agent_id: UUID, 
    db: AsyncSession = Depends(get_db)
):
    """Assigne un batch à un livreur et met à jour le statut des livraisons."""
    batch_query = await db.execute(select(Batch).where(Batch.id == batch_id))
    batch = batch_query.scalar_one_or_none()

    if not batch:
        raise HTTPException(status_code=404, detail="Batch non trouvé")

    batch.delivery_agent_id = agent_id
    batch.status = BatchStatus.ASSIGNED
    
    # Mettre à jour toutes les livraisons du batch
    # Changement : batch.orders -> batch.deliveries
    for delivery in batch.deliveries:
        delivery.status = DeliveryStatus.ASSIGNED_TO_DELIVERY_AGENT
        delivery.delivery_agent_id = agent_id

    await db.commit()
    await db.refresh(batch)
    return batch
