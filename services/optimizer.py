from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
import uuid

from database.models import Order, Batch, OrderStatus, BatchStatus
from models.schemas import BatchCreate

class DispatchOptimizer:
    def __init__(self, db: Session):
        self.db = db

    def auto_batch_orders(self, area_name: str, max_orders: int = 5) -> Optional[Batch]:
        """
        Récupère les commandes en attente dans une zone spécifique 
        et les regroupe dans un nouveau Batch.
        """
        pending_orders = (
            self.db.query(Order)
            .join(Order.delivery_location)
            .filter(
                and_(
                    Order.status == OrderStatus.WAITING_FOR_BATCH,
                    Order.batch_id == None,
                    Order.delivery_location.has(area=area_name)
                )
            )
            .limit(max_orders)
            .all()
        )

        if not pending_orders:
            return None

        new_batch = Batch(
            area_name=area_name,
            status=BatchStatus.CREATED,
            max_orders=max_orders,
            delivery_fee=2000.0,  
        )
        self.db.add(new_batch)
        self.db.flush() 

        for order in pending_orders:
            order.batch_id = new_batch.id
            order.status = OrderStatus.BATCHED
        
        try:
            self.db.commit()
            self.db.refresh(new_batch)
            return new_batch
        except Exception as e:
            self.db.rollback()
            raise e

    def calculate_route_efficiency(self, batch_id: uuid.UUID):
        """
        Logique future : Utiliser une API comme Google Maps ou OSRM 
        pour calculer l'ordre optimal des RouteSteps.
        """
        batch = self.db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            return None
            
        # Ici on pourrait implémenter l'algorithme du voyageur de commerce (TSP)
        # pour ordonner les commandes dans le batch afin de minimiser la distance.
        pass

    def assign_batch_to_agent(self, batch_id: uuid.UUID, agent_id: uuid.UUID) -> Batch:
        """
        Assigne un batch à un livreur disponible.
        """
        batch = self.db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise ValueError("Batch introuvable")

        batch.delivery_agent_id = agent_id
        batch.status = BatchStatus.ASSIGNED
        
        for order in batch.orders:
            order.delivery_agent_id = agent_id
            order.status = OrderStatus.ASSIGNED_TO_DELIVERY_AGENT

        self.db.commit()
        self.db.refresh(batch)
        return batch