from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class OrderStatus(str, Enum):
    EN_ATTENTE = "en_attente"
    GROUPÉ = "groupe"
    EN_COURS = "en_cours"
    LIVRÉ = "livre"

class OrderCreate(BaseModel):
    client_name: str
    client_phone: str
    quartier: str
    latitude: float
    longitude: float
    description: str

class OrderResponse(OrderCreate):
    id: str
    seller_id: str
    otp: str
    status: OrderStatus
    created_at: datetime