import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import String, Boolean, DateTime, Float, ForeignKey, Enum as SqlEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from .db import Base

# --- I. ENUMS ---

class Role(str, PyEnum):
    ADMIN = "ADMIN"
    SELLER = "SELLER"
    CLIENT = "CLIENT"
    DELIVERY_AGENT = "DELIVERY_AGENT"

class OrderStatus(str, PyEnum):
    CREATED = "CREATED"
    WAITING_FOR_BATCH = "WAITING_FOR_BATCH"
    BATCHED = "BATCHED"
    ASSIGNED_TO_DELIVERY_AGENT = "ASSIGNED_TO_DELIVERY_AGENT"
    IN_DELIVERY = "IN_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELED = "CANCELED"

class BatchStatus(str, PyEnum):
    CREATED = "CREATED"
    AVAILABLE = "AVAILABLE"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"

class PaymentStatus(str, PyEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"

# --- II. MODELS ---

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password: Mapped[str] = mapped_column(String(255))
    
    # Stockage sous forme de liste (PostgreSQL ARRAY) ou String selon vos besoins
    # Ici on simplifie avec un seul rôle ou une gestion via table d'association si multiple
    role: Mapped[Role] = mapped_column(SqlEnum(Role, name="role_enum"), nullable=False)

    # Profil Livreur
    identity_document_number: Mapped[Optional[str]] = mapped_column(String(50))
    identity_document_url: Mapped[Optional[str]] = mapped_column(String(500))
    vehicle_registration_number: Mapped[Optional[str]] = mapped_column(String(50))
    vehicle_registration_url: Mapped[Optional[str]] = mapped_column(String(500))

    # Profil Client
    accepted_terms_of_use: Mapped[bool] = mapped_column(Boolean, default=False)
    accepted_privacy_policy: Mapped[bool] = mapped_column(Boolean, default=False)
    terms_accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Localisation temps réel (Livreur)
    current_location_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("geo_locations.id"))
    current_location = relationship("GeoLocation", foreign_keys=[current_location_id])

    # Relations inverse
    seller_orders: Mapped[List["Order"]] = relationship("Order", foreign_keys="Order.seller_id", back_populates="seller")
    client_orders: Mapped[List["Order"]] = relationship("Order", foreign_keys="Order.client_id", back_populates="client")
    batches: Mapped[List["Batch"]] = relationship("Batch", back_populates="delivery_agent")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GeoLocation(Base):
    __tablename__ = "geo_locations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region: Mapped[str] = mapped_column(String(100))
    area: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(255))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relations Users
    seller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    delivery_agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))

    seller = relationship("User", foreign_keys=[seller_id], back_populates="seller_orders")
    client = relationship("User", foreign_keys=[client_id], back_populates="client_orders")
    delivery_agent = relationship("User", foreign_keys=[delivery_agent_id])

    # Infos Client (Directes si non inscrit)
    client_name: Mapped[str] = mapped_column(String(200))
    client_phone: Mapped[str] = mapped_column(String(20))

    # Logistique
    delivery_location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("geo_locations.id"))
    delivery_location = relationship("GeoLocation")
    
    package_description: Mapped[str] = mapped_column(String(500))
    package_weight_kg: Mapped[float] = mapped_column(Float)
    
    otp: Mapped[str] = mapped_column(String(10))
    tracking_link: Mapped[str] = mapped_column(String(255))
    status: Mapped[OrderStatus] = mapped_column(SqlEnum(OrderStatus, name="order_status_enum"), default=OrderStatus.CREATED)

    # Relation Batch
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("batches.id"))
    batch = relationship("Batch", back_populates="orders")

    # Autres relations
    payments: Mapped[List["PaymentInfo"]] = relationship("PaymentInfo", back_populates="order")
    notifications: Mapped[List["Notification"]] = relationship("Notification", back_populates="order")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    area_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[BatchStatus] = mapped_column(SqlEnum(BatchStatus, name="batch_status_enum"), default=BatchStatus.CREATED)

    delivery_agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    delivery_agent = relationship("User", back_populates="batches")

    orders: Mapped[List["Order"]] = relationship("Order", back_populates="batch")
    route_steps: Mapped[List["RouteStep"]] = relationship("RouteStep", back_populates="batch")

    max_orders: Mapped[int] = mapped_column(default=5)
    total_distance_meters: Mapped[Optional[float]] = mapped_column(Float)
    delivery_fee: Mapped[float] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True) # WAVE, OM, CASH
    label: Mapped[str] = mapped_column(String(50))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_online_confirmation: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PaymentActor(Base):
    __tablename__ = "payment_actors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True) # SELLER, CLIENT, etc.
    description: Mapped[str] = mapped_column(String(255))


class PaymentInfo(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"))
    order = relationship("Order", back_populates="payments")

    payment_method_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payment_methods.id"))
    payment_method = relationship("PaymentMethod")

    paid_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payment_actors.id"))
    paid_by = relationship("PaymentActor", foreign_keys=[paid_by_id])

    received_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payment_actors.id"))
    received_by = relationship("PaymentActor", foreign_keys=[received_by_id])

    amount: Mapped[float] = mapped_column(Float)
    transaction_reference: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[PaymentStatus] = mapped_column(
        SqlEnum(PaymentStatus, name="payment_status_enum"), 
        default=PaymentStatus.PENDING
    )

    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RouteStep(Base):
    __tablename__ = "route_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("batches.id"))
    batch = relationship("Batch", back_populates="route_steps")

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"))
    order = relationship("Order")

    distance_meters: Mapped[float] = mapped_column(Float)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"))
    order = relationship("Order", back_populates="notifications")

    recipient_phone: Mapped[str] = mapped_column(String(20))
    type: Mapped[str] = mapped_column(String(50)) # SMS, PUSH, EMAIL
    message: Mapped[str] = mapped_column(String(1000))
    sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)



