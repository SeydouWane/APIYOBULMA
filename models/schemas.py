from pydantic import BaseModel, EmailStr, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from database.models import Role, OrderStatus, BatchStatus

# --- I. GEOLOCATION SCHEMAS ---

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


# --- II. USER SCHEMAS ---

class UserBase(BaseModel):
    first_name: str
    last_name: str
    phone_number: str
    email: Optional[EmailStr] = None
    role: Role

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    identity_document_number: Optional[str] = None
    vehicle_registration_number: Optional[str] = None

class UserOut(UserBase):
    id: UUID
    identity_document_url: Optional[str] = None
    vehicle_registration_url: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# --- III. ORDER SCHEMAS ---

class OrderBase(BaseModel):
    client_name: str
    client_phone: str
    package_description: str
    package_weight_kg: float
    status: OrderStatus = OrderStatus.CREATED

class OrderCreate(OrderBase):
    seller_id: UUID
    client_id: Optional[UUID] = None
    delivery_location: GeoLocationCreate

class OrderOut(OrderBase):
    id: UUID
    seller_id: UUID
    delivery_location: GeoLocationOut
    tracking_link: str
    otp: str # À masquer éventuellement selon les permissions
    batch_id: Optional[UUID] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# --- IV. BATCH SCHEMAS ---

class BatchBase(BaseModel):
    area_name: str
    status: BatchStatus = BatchStatus.CREATED
    max_orders: int = 5
    delivery_fee: float

class BatchCreate(BatchBase):
    pass

class BatchOut(BatchBase):
    id: UUID
    delivery_agent_id: Optional[UUID] = None
    total_distance_meters: Optional[float] = None
    # On peut inclure la liste des commandes simplifiées
    orders: List[OrderOut] = []
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# --- V. PAYMENT SCHEMAS ---

class PaymentMethodOut(BaseModel):
    id: UUID
    code: str
    label: str
    active: bool
    
    model_config = ConfigDict(from_attributes=True)

class PaymentInfoCreate(BaseModel):
    order_id: UUID
    payment_method_id: UUID
    paid_by_id: UUID
    received_by_id: UUID
    amount: float

class PaymentInfoOut(BaseModel):
    id: UUID
    amount: float
    transaction_reference: Optional[str] = None
    status: str
    paid_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# --- VI. ROUTE & NOTIFICATION ---

class RouteStepOut(BaseModel):
    id: UUID
    order_id: UUID
    distance_meters: float
    
    model_config = ConfigDict(from_attributes=True)

class NotificationOut(BaseModel):
    id: UUID
    type: str
    message: str
    sent: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)