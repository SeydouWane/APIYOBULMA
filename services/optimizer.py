import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from sqlalchemy.orm import selectinload

from database.models import Order, Batch, OrderStatus, BatchStatus, GeoLocation, DeliveryType

class DispatchOptimizer:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def auto_batch_orders(self, area_name: str, max_orders: int = 5) -> Optional[Batch]:
        """
        Regroupe les commandes de type GROUPAGE en attente dans une zone spécifique 
        dans un nouveau Batch.
        """
        # 1. Rechercher les commandes éligibles :
        # - Statut: WAITING_FOR_BATCH
        # - Pas encore de batch_id
        # - Zone géographique correspondante
        # - TYPE: GROUPAGE uniquement (L'EXPRESS ne se batche pas)
        query = (
            select(Order)
            .join(Order.delivery_location)
            .filter(
                and_(
                    Order.status == OrderStatus.WAITING_FOR_BATCH,
                    Order.batch_id == None,
                    Order.delivery_type == DeliveryType.GROUPAGE,
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
        # La delivery_fee pourrait être calculée ici selon la distance cumulée
        new_batch = Batch(
            area_name=area_name,
            status=BatchStatus.CREATED,
            max_orders=max_orders,
            delivery_fee=1500.0, # Prix de base groupage (exemple)
        )
        
        self.db.add(new_batch)
        await self.db.flush() # Pour obtenir new_batch.id

        # 3. Lier les commandes et mettre à jour les statuts
        for order in pending_orders:
            order.batch_id = new_batch.id
            order.status = OrderStatus.BATCHED
        
        try:
            await self.db.commit()
            
            # Rechargement complet avec les relations pour le retour API
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
        Assigne un batch à un livreur et propage l'agent_id à toutes les commandes.
        """
        query = (
            select(Batch)
            .filter(Batch.id == batch_id)
            .options(selectinload(Batch.orders))
        )
        result = await self.db.execute(query)
        batch = result.scalars().first()

        if not batch:
            raise ValueError("Batch introuvable")

        # Mise à jour du batch
        batch.delivery_agent_id = agent_id
        batch.status = BatchStatus.ASSIGNED
        
        # Propagation aux commandes du batch
        for order in batch.orders:
            order.delivery_agent_id = agent_id
            order.status = OrderStatus.ASSIGNED_TO_DELIVERY_AGENT

        try:
            await self.db.commit()
            # On refresh pour synchroniser l'état de l'objet
            await self.db.refresh(batch)
            return batch
        except Exception as e:
            await self.db.rollback()
            raise e

    async def get_optimal_route(self, batch_id: uuid.UUID):
        """
        Future implémentation : 
        Calculer l'ordre des RouteSteps en utilisant les coordonnées lat/long 
        des GeoLocations de chaque Order dans le Batch.
        """
        # 1. Récupérer les lat/long de toutes les commandes du batch
        # 2. Appliquer un algorithme de tri spatial (ex: Nearest Neighbor ou TSP solver)
        # 3. Créer ou mettre à jour les entrées dans RouteStep
        pass
