from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from decimal import Decimal
from pydantic_settings import BaseSettings

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

class User(UserBase):

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

class Stock(StockBase):
    id: int

    class Config:
        from_attributes = True
        protected_namespaces = ()

# Product Schemas
class ProductBase(BaseModel):
    model_name: str = Field(alias='model_name')
    gender: str
    image_side_url: Optional[str] = None
    image_top_url: Optional[str] = None
    image_34_url: Optional[str] = None
    class Config:
        protected_namespaces = ('model_',)

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int

    class Config:
        from_attributes = True
        protected_namespaces = ()

# Purchase Schemas
class PurchaseBase(BaseModel):
    customer_id: int
    seller_id: int
    stock_id: int
    quantity: int
    total_price: Decimal

class PurchaseCreate(BaseModel):
    customer_id: int
    product_id: str
    stock_id: int
    seller_id: int
    quantity: int
    total_price: Decimal

    class Config:
        from_attributes = True

class Purchase(PurchaseCreate):
    id: int
    purchase_date: datetime

    class Config:
        from_attributes: True


class UserDetails(BaseModel):
    id: int
    first_name: str
    last_name: str
    user_type: str

