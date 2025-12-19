from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from .db import Base
import uuid
import datetime
from models.schemas import OrderStatus

class OrderDB(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    seller_id = Column(String, nullable=False)
    client_name = Column(String, nullable=False)
    client_phone = Column(String, nullable=False)
    quartier = Column(String, nullable=False)
    address = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    otp = Column(String(4), nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.EN_ATTENTE)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
