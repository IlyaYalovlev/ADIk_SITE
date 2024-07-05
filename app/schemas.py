from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, conint
from typing import Optional, List
from decimal import Decimal



# User Schemas
class UserBase(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    user_type: str
    phone: str
    total_orders_value: Decimal
    created_at: datetime

    class Config:
        from_attributes = True
        protected_namespaces = ()

class UserCreate(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone: str
    user_type: str
    total_orders_value: Optional[Decimal] = Decimal('0.00')

    class Config:
        from_attributes = True
        protected_namespaces = ()



# Stock Schemas
class StockBase(BaseModel):
    product_id: str
    seller_id: int
    quantity: int
    size: float
    price: Decimal
    discount_price: Optional[Decimal] = None

class StockCreate(StockBase):
    pass



# Purchase Schemas

class PurchaseCreate(BaseModel):
    customer_id: int
    product_id: str
    stock_id: int
    seller_id: int
    quantity: int
    total_price: Decimal

    class Config:
        from_attributes = True




class UserDetails(BaseModel):
    id: int
    first_name: str
    last_name: str
    user_type: str

class StockUpdate(BaseModel):
    stock_id: int
    product_id: str
    price: float
    stock: int

class StockUpdateRequest(BaseModel):
    products: List[StockUpdate]

class StockBase(BaseModel):
    product_id: str
    seller_id: int
    size: float
    price: float
    discount_price: float

    class Config:
        from_attributes = True

class AddToCartRequest(BaseModel):
    stock_id: int
    quantity: int
    user_id: Optional[int] = None
    session_id: Optional[str] = None

class UpdateCartRequest(BaseModel):
    cartitem_id: int
    quantity: int


class DeliveryDetailsCreate(BaseModel):
    customer_id: int
    city: str
    street: str
    house_number: str
    apartment_number: Optional[str]
    recipient_name: str
    phone: str

    class Config:
        orm_mode = True

class DeliveryDetailsС(BaseModel):
    purchase_id: int
    city: str
    street: str
    house_number: str
    apartment_number: Optional[str]
    recipient_name: str
    phone: str

    class Config:
        orm_mode = True

class PaymentRequest(BaseModel):
    amount: int
    currency: str
    payment_method: str  # Токен источника платежа

class OrderDetails(BaseModel):
    user_id: int
    payment_intent_id: str
    delivery_details: DeliveryDetailsCreate

class CreateCheckoutSessionRequest(BaseModel):
    amount: int
    currency: str
    user_id: int
    delivery_details: DeliveryDetailsCreate


class ProductQuantityUpdateSchema(BaseModel):
    stock_id: int
    quantity: conint(gt=0)

class ProductActivationSchema(BaseModel):
    product_id: str
    is_active: bool

class SaleUpdateSchema(BaseModel):
    sale_id: int = Field(..., description="Идентификатор сделки")
    status: str = Field(..., description="Новый статус сделки")
    tracking_number: Optional[str] = Field(None, description="Трек-номер")

    class Config:
        schema_extra = {
            "example": {
                "sale_id": 123,
                "status": "Отправлен",
                "tracking_number": "TRACK123456789"
            }
        }

class DeliveryDetailsSchema(BaseModel):
    city: str
    street: str
    house_number: str
    apartment_number: str
    recipient_name: str
    phone: str