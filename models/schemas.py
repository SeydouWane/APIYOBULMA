from pydantic import BaseModel, EmailStr, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from database.models import (
    Role, DeliveryStatus, BatchStatus, PaymentStatus, 
    DeliveryType, PackageVolumeCategory, AccountRestriction
)

# --- I. GEOLOCATION ---
class GeoLocationBase(BaseModel):
    region: str
    area: str
    address: str
    latitude: float
    longitude: float

class GeoLocationCreate(GeoLocationBase):
    pass

class GeoLocationOut(GeoLocationBase):
    id: UUID
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- II. USER ---
class UserBase(BaseModel):
    first_name: str
    last_name: str
    phone_number: str
    email: Optional[EmailStr] = None
    role: Role

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: UUID
    profile_photo_url: Optional[str] = None
    vehicle_photo_url: Optional[str] = None
    identity_document_url: Optional[str] = None
    vehicle_registration_url: Optional[str] = None
    languages: List[str] = []
    restriction: AccountRestriction
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- III. DELIVERY (Anciennement ORDER) ---
class DeliveryBase(BaseModel):
    client_name: str
    client_phone: str
    preferred_languages: List[str] = ["fr"]
    delivery_type: DeliveryType
    content_nature: str
    package_description: str
    package_weight_kg: float
    volume_category: PackageVolumeCategory
    declared_value_fcfa: Optional[int] = None
    status: DeliveryStatus = DeliveryStatus.CREATED

class DeliveryCreate(DeliveryBase):
    seller_id: UUID
    client_id: Optional[UUID] = None
    delivery_location: GeoLocationCreate

class DeliveryOut(DeliveryBase):
    id: UUID
    seller_id: UUID
    client_id: Optional[UUID] = None
    delivery_agent_id: Optional[UUID] = None
    delivery_location: GeoLocationOut
    package_photo_url: Optional[str] = None
    tracking_link: str
    otp: str
    batch_id: Optional[UUID] = None
    estimated_delivery_time: Optional[datetime] = None
    eta_minutes: Optional[int] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- IV. BATCH ---
class BatchBase(BaseModel):
    area_name: str
    status: BatchStatus = BatchStatus.CREATED
    max_orders: int = Field(default=5, ge=1)
    delivery_fee: float

class BatchOut(BatchBase):
    id: UUID
    delivery_agent_id: Optional[UUID] = None
    total_distance_meters: Optional[float] = None
    deliveries: List[DeliveryOut] = []
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- V. PAYMENT & FINANCE ---

class PaymentMethodOut(BaseModel):
    id: UUID
    code: str
    label: str
    active: bool
    model_config = ConfigDict(from_attributes=True)

class PaymentActorOut(BaseModel):
    id: UUID
    code: str
    description: str
    model_config = ConfigDict(from_attributes=True)

class PaymentCreate(BaseModel):
    delivery_id: UUID
    payment_method_id: UUID
    amount_total: float
    paid_by_id: UUID
    received_by_id: UUID
    collected_by_id: Optional[UUID] = None
    transaction_reference: Optional[str] = None

class PaymentOut(BaseModel):
    id: UUID
    delivery_id: UUID
    payment_method_id: UUID
    amount_total: float
    transaction_reference: Optional[str] = None
    status: PaymentStatus
    paid_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PaymentSplitOut(BaseModel):
    id: UUID
    payment_id: UUID
    actor_id: UUID
    purpose_id: UUID
    amount: float
    settled: bool
    settled_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class AccountBalanceOut(BaseModel):
    user_id: UUID
    available_balance: float
    debt_balance: float
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DebtRecordOut(BaseModel):
    id: UUID
    debtor_id: UUID
    delivery_id: UUID
    amount: float
    reason: str
    settled: bool
    settled_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- VI. LOGISTICS & NOTIFICATIONS ---

class RouteStepOut(BaseModel):
    id: UUID
    batch_id: UUID
    delivery_id: UUID
    distance_meters: float
    model_config = ConfigDict(from_attributes=True)

class NotificationOut(BaseModel):
    id: UUID
    delivery_id: UUID
    recipient_phone: str
    type: str
    message: str
    sent: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- VII. AUTHENTICATION ---

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[UUID] = None
    role: Optional[str] = None

class LoginRequest(BaseModel):
    phone_number: str
    password: str

# --- VIII. FINANCIAL REQUESTS ---

class WithdrawalRequest(BaseModel):
    """Schéma pour la demande de retrait (Wave/OM)"""
    user_id: UUID
    amount: float = Field(..., gt=0, description="Le montant doit être supérieur à 0")
    provider: str  # "WAVE" ou "OM"
    phone_number: str

class WithdrawalResponse(BaseModel):
    """Schéma pour la réponse de confirmation de retrait"""
    status: str
    message: str
    new_balance: float
    transaction_id: Optional[str] = None
