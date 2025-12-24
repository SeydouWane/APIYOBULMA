import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from sqlalchemy.orm import selectinload

# Importation des nouveaux noms de modèles et statuts
from database.models import Delivery, Batch, DeliveryStatus, BatchStatus, GeoLocation, DeliveryType

class DispatchOptimizer:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def auto_batch_deliveries(self, area_name: str, max_orders: int = 5) -> Optional[Batch]:
        """
        Regroupe les livraisons de type GROUPAGE en attente dans une zone spécifique 
        dans un nouveau Batch.
        """
        # 1. Rechercher les livraisons éligibles
        query = (
            select(Delivery)
            .join(Delivery.delivery_location)
            .filter(
                and_(
                    Delivery.status == DeliveryStatus.WAITING_FOR_BATCH,
                    Delivery.batch_id == None,
                    Delivery.delivery_type == DeliveryType.GROUPAGE,
                    GeoLocation.area == area_name
                )
            )
            .limit(max_orders)
            .options(selectinload(Delivery.delivery_location))
        )
        
        result = await self.db.execute(query)
        pending_deliveries = result.scalars().all()

        if not pending_deliveries:
            return None

        # 2. Créer le nouveau Batch
        new_batch = Batch(
            area_name=area_name,
            status=BatchStatus.CREATED,
            max_orders=max_orders,
            delivery_fee=1500.0, # Prix de base groupage
        )
        
        self.db.add(new_batch)
        await self.db.flush() 

        # 3. Lier les livraisons et mettre à jour les statuts
        for delivery in pending_deliveries:
            delivery.batch_id = new_batch.id
            delivery.status = DeliveryStatus.BATCHED
        
        try:
            await self.db.commit()
            
            # Rechargement avec la relation 'deliveries'
            final_result = await self.db.execute(
                select(Batch)
                .filter(Batch.id == new_batch.id)
                .options(selectinload(Batch.deliveries))
            )
            return final_result.scalars().first()
        except Exception as e:
            await self.db.rollback()
            raise e

    async def assign_batch_to_agent(self, batch_id: uuid.UUID, agent_id: uuid.UUID) -> Batch:
        """
        Assigne un batch à un livreur et propage l'agent_id à toutes les livraisons.
        """
        query = (
            select(Batch)
            .filter(Batch.id == batch_id)
            .options(selectinload(Batch.deliveries))
        )
        result = await self.db.execute(query)
        batch = result.scalars().first()

        if not batch:
            raise ValueError("Batch introuvable")

        # Mise à jour du batch
        batch.delivery_agent_id = agent_id
        batch.status = BatchStatus.ASSIGNED
        
        # Propagation aux livraisons du batch
        for delivery in batch.deliveries:
            delivery.delivery_agent_id = agent_id
            delivery.status = DeliveryStatus.ASSIGNED_TO_DELIVERY_AGENT

        try:
            await self.db.commit()
            await self.db.refresh(batch)
            return batch
        except Exception as e:
            await self.db.rollback()
            raise e

    async def get_optimal_route(self, batch_id: uuid.UUID):
        """
        Future implémentation : Algorithme TSP (Traveling Salesman Problem)
        pour trier les livraisons du batch par proximité géographique.
        """
        pass
