from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from sqlalchemy.orm import selectinload
import uuid
from typing import List, Optional

from database.models import Order, Batch, OrderStatus, BatchStatus, GeoLocation

class DispatchOptimizer:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def auto_batch_orders(self, area_name: str, max_orders: int = 5) -> Optional[Batch]:
        """
        Récupère les commandes en attente dans une zone spécifique 
        et les regroupe dans un nouveau Batch (Version Asynchrone).
        """
        # 1. Rechercher les commandes éligibles
        # On utilise selectinload pour charger la localisation de chaque commande
        query = (
            select(Order)
            .join(Order.delivery_location)
            .filter(
                and_(
                    Order.status == OrderStatus.WAITING_FOR_BATCH,
                    Order.batch_id == None,
                    GeoLocation.area == area_name
                )
            )
            .limit(max_orders)
            .options(selectinload(Order.delivery_location))
        )
        
        result = await self.db.execute(query)
        pending_orders = result.scalars().all()

        if not pending_orders:
            return None

        # 2. Créer le nouveau Batch
        new_batch = Batch(
            area_name=area_name,
            status=BatchStatus.CREATED,
            max_orders=max_orders,
            delivery_fee=2000.0, # À rendre dynamique plus tard selon la zone
        )
        
        self.db.add(new_batch)
        await self.db.flush() # Pour obtenir l'ID du batch sans commiter

        # 3. Lier les commandes au batch
        for order in pending_orders:
            order.batch_id = new_batch.id
            order.status = OrderStatus.BATCHED
        
        try:
            await self.db.commit()
            # On recharge le batch avec ses commandes pour le retour
            final_result = await self.db.execute(
                select(Batch)
                .filter(Batch.id == new_batch.id)
                .options(selectinload(Batch.orders))
            )
            return final_result.scalars().first()
        except Exception as e:
            await self.db.rollback()
            raise e

    async def assign_batch_to_agent(self, batch_id: uuid.UUID, agent_id: uuid.UUID) -> Batch:
        """
        Assigne un batch à un livreur et met à jour toutes les commandes liées.
        """
        # Charger le batch et ses commandes
        query = (
            select(Batch)
            .filter(Batch.id == batch_id)
            .options(selectinload(Batch.orders))
        )
        result = await self.db.execute(query)
        batch = result.scalars().first()

        if not batch:
            raise ValueError("Batch introuvable")

        batch.delivery_agent_id = agent_id
        batch.status = BatchStatus.ASSIGNED
        
        # Mettre à jour le statut de chaque commande individuellement
        for order in batch.orders:
            order.delivery_agent_id = agent_id
            order.status = OrderStatus.ASSIGNED_TO_DELIVERY_AGENT

        try:
            await self.db.commit()
            await self.db.refresh(batch)
            return batch
        except Exception as e:
            await self.db.rollback()
            raise e

    async def calculate_route_efficiency(self, batch_id: uuid.UUID):
        """
        Logique future : Implémenter l'algorithme du voyageur de commerce (TSP)
        pour ordonner les points de livraison de manière optimale.
        """
        pass
