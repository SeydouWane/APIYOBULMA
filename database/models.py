import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import String, Boolean, DateTime, Float, ForeignKey, Enum as SqlEnum, ARRAY, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

# --- I. ENUMS ---

class Role(str, PyEnum):
    ADMIN = "ADMIN"
    SELLER = "SELLER"
    CLIENT = "CLIENT"
    DELIVERY_AGENT = "DELIVERY_AGENT"

class DeliveryStatus(str, PyEnum):
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
    CANCELED = "CANCELED"

class PaymentStatus(str, PyEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"

class AccountRestriction(str, PyEnum):
    NONE = "NONE"
    LIMITED = "LIMITED"
    BLOCKED = "BLOCKED"

class DeliveryType(str, PyEnum):
    EXPRESS = "EXPRESS"
    GROUPAGE = "GROUPAGE"
    STANDARD = "STANDARD"

class PackageVolumeCategory(str, PyEnum):
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"
    XL = "XL"

# --- II. CORE MODELS ---

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    password: Mapped[str] = mapped_column(String(255))
    
    role: Mapped[Role] = mapped_column(SqlEnum(Role, name="role_enum"), nullable=False)
    restriction: Mapped[AccountRestriction] = mapped_column(
        SqlEnum(AccountRestriction, name="restriction_enum"), default=AccountRestriction.NONE
    )

    # Profil Livreur / Agent
    profile_photo_url: Mapped[Optional[str]] = mapped_column(String(500))
    vehicle_photo_url: Mapped[Optional[str]] = mapped_column(String(500))
    identity_document_number: Mapped[Optional[str]] = mapped_column(String(50))
    identity_document_url: Mapped[Optional[str]] = mapped_column(String(500))
    vehicle_registration_number: Mapped[Optional[str]] = mapped_column(String(50))
    vehicle_registration_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    languages: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)

    # Profil Client / Conformité
    accepted_terms_of_use: Mapped[bool] = mapped_column(Boolean, default=False)
    accepted_privacy_policy: Mapped[bool] = mapped_column(Boolean, default=False)
    terms_accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Localisation temps réel (Livreur)
    current_location_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("geo_locations.id"))
    current_location: Mapped[Optional["GeoLocation"]] = relationship("GeoLocation", foreign_keys=[current_location_id])

    # Relations
    seller_deliveries: Mapped[List["Delivery"]] = relationship("Delivery", foreign_keys="Delivery.seller_id", back_populates="seller")
    client_deliveries: Mapped[List["Delivery"]] = relationship("Delivery", foreign_keys="Delivery.client_id", back_populates="client")
    batches: Mapped[List["Batch"]] = relationship("Batch", back_populates="delivery_agent")
    account_balance: Mapped[Optional["AccountBalance"]] = relationship("AccountBalance", back_populates="user", uselist=False)
    debt_records: Mapped[List["DebtRecord"]] = relationship("DebtRecord", back_populates="debtor")

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


class Delivery(Base):
    __tablename__ = "deliveries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    seller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    delivery_agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id"), 
        comment="Direct agent for EXPRESS. Groupage uses agent from Batch."
    )

    seller: Mapped["User"] = relationship("User", foreign_keys=[seller_id], back_populates="seller_deliveries")
    client: Mapped[Optional["User"]] = relationship("User", foreign_keys=[client_id], back_populates="client_deliveries")
    delivery_agent: Mapped[Optional["User"]] = relationship("User", foreign_keys=[delivery_agent_id])

    client_name: Mapped[str] = mapped_column(String(200))
    client_phone: Mapped[str] = mapped_column(String(20))
    preferred_languages: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)

    delivery_location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("geo_locations.id"))
    delivery_location: Mapped["GeoLocation"] = relationship("GeoLocation")
    
    delivery_type: Mapped[DeliveryType] = mapped_column(SqlEnum(DeliveryType, name="delivery_type_enum"))
    content_nature: Mapped[str] = mapped_column(String(100))
    package_photo_url: Mapped[Optional[str]] = mapped_column(String(500))
    package_description: Mapped[str] = mapped_column(String(500))
    package_weight_kg: Mapped[float] = mapped_column(Float)
    volume_category: Mapped[PackageVolumeCategory] = mapped_column(SqlEnum(PackageVolumeCategory, name="volume_enum"))
    declared_value_fcfa: Mapped[Optional[int]] = mapped_column(Integer)
    
    otp: Mapped[str] = mapped_column(String(10))
    tracking_link: Mapped[str] = mapped_column(String(255))
    status: Mapped[DeliveryStatus] = mapped_column(SqlEnum(DeliveryStatus, name="delivery_status_enum"), default=DeliveryStatus.CREATED)

    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("batches.id"))
    batch: Mapped[Optional["Batch"]] = relationship("Batch", back_populates="deliveries")

    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="delivery")
    notifications: Mapped[List["Notification"]] = relationship("Notification", back_populates="delivery")
    debt_records: Mapped[List["DebtRecord"]] = relationship("DebtRecord", back_populates="delivery")

    estimated_delivery_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    eta_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    area_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[BatchStatus] = mapped_column(SqlEnum(BatchStatus, name="batch_status_enum"), default=BatchStatus.CREATED)

    delivery_agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    delivery_agent: Mapped[Optional["User"]] = relationship("User", back_populates="batches")

    deliveries: Mapped[List["Delivery"]] = relationship("Delivery", back_populates="batch")
    route_steps: Mapped[List["RouteStep"]] = relationship("RouteStep", back_populates="batch")

    max_orders: Mapped[int] = mapped_column(default=5)
    total_distance_meters: Mapped[Optional[float]] = mapped_column(Float)
    delivery_fee: Mapped[float] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# --- III. FINANCIAL MODELS ---

class PaymentMethod(Base):
    __tablename__ = "payment_methods"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True) # WAVE, CASH
    label: Mapped[str] = mapped_column(String(50))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_online_confirmation: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class PaymentActor(Base):
    __tablename__ = "payment_actors"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True) # SELLER, CLIENT, PLATFORM
    description: Mapped[str] = mapped_column(String(255))

class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    delivery_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("deliveries.id"))
    payment_method_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payment_methods.id"))
    
    paid_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payment_actors.id"))
    received_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payment_actors.id"))
    collected_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("payment_actors.id"))

    amount_total: Mapped[float] = mapped_column(Float)
    transaction_reference: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[PaymentStatus] = mapped_column(SqlEnum(PaymentStatus, name="payment_status_enum"), default=PaymentStatus.PENDING)

    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    delivery: Mapped["Delivery"] = relationship("Delivery", back_populates="payments")
    payment_method: Mapped["PaymentMethod"] = relationship("PaymentMethod")
    paid_by: Mapped["PaymentActor"] = relationship("PaymentActor", foreign_keys=[paid_by_id])
    received_by: Mapped["PaymentActor"] = relationship("PaymentActor", foreign_keys=[received_by_id])
    collected_by: Mapped[Optional["PaymentActor"]] = relationship("PaymentActor", foreign_keys=[collected_by_id])
    splits: Mapped[List["PaymentSplit"]] = relationship("PaymentSplit", back_populates="payment")

class PaymentPurpose(Base):
    __tablename__ = "payment_purposes"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True) # DELIVERY_FEE, ITEM_PRICE
    description: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class PaymentSplit(Base):
    __tablename__ = "payment_splits"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payments.id"))
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payment_actors.id"))
    purpose_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payment_purposes.id"))
    
    amount: Mapped[float] = mapped_column(Float)
    settled: Mapped[bool] = mapped_column(Boolean, default=False)
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    payment: Mapped["Payment"] = relationship("Payment", back_populates="splits")
    actor: Mapped["PaymentActor"] = relationship("PaymentActor")
    purpose: Mapped["PaymentPurpose"] = relationship("PaymentPurpose")

class CommissionRule(Base):
    __tablename__ = "commission_rules"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payer_role: Mapped[Role] = mapped_column(SqlEnum(Role, name="comm_role_enum"))
    percentage: Mapped[Optional[float]] = mapped_column(Float)
    fixed_amount: Mapped[Optional[float]] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AccountBalance(Base):
    __tablename__ = "account_balances"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    available_balance: Mapped[float] = mapped_column(Float, default=0.0)
    debt_balance: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user: Mapped["User"] = relationship("User", back_populates="account_balance")

class DebtRecord(Base):
    __tablename__ = "debt_records"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    debtor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    delivery_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("deliveries.id"))
    
    amount: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(100)) # ex: PLATFORM_COMMISSION
    settled: Mapped[bool] = mapped_column(Boolean, default=False)
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    debtor: Mapped["User"] = relationship("User", back_populates="debt_records")
    delivery: Mapped["Delivery"] = relationship("Delivery", back_populates="debt_records")

# --- IV. LOGISTICS & NOTIFICATIONS ---

class RouteStep(Base):
    __tablename__ = "route_steps"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("batches.id"))
    delivery_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("deliveries.id"))
    distance_meters: Mapped[float] = mapped_column(Float)

    batch: Mapped["Batch"] = relationship("Batch", back_populates="route_steps")
    delivery: Mapped["Delivery"] = relationship("Delivery")

class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    delivery_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("deliveries.id"))
    recipient_phone: Mapped[str] = mapped_column(String(20))
    type: Mapped[str] = mapped_column(String(50)) # SMS, PUSH, EMAIL
    message: Mapped[str] = mapped_column(String(1000))
    sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    delivery: Mapped["Delivery"] = relationship("Delivery", back_populates="notifications")
