from pydantic import BaseModel, EmailStr
from typing import Optional
from decimal import Decimal

# User Schemas
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    total_orders_value: Optional[Decimal] = Decimal('0.00')

    class Config:
        orm_mode = True

class UserDetails(User):
    pass

# Stock Schemas
class StockBase(BaseModel):
    product_id: int
    seller_id: int
    quantity: int
    price: Decimal
    discount_price: Optional[Decimal] = None

class StockCreate(StockBase):
    pass

class Stock(StockBase):
    id: int

    class Config:
        orm_mode = True

# Product Schemas
class ProductBase(BaseModel):
    model_name: str
    gender: str
    image_side_url: Optional[str] = None
    image_top_url: Optional[str] = None
    image_34_url: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int

    class Config:
        orm_mode = True

# Purchase Schemas
class PurchaseBase(BaseModel):
    customer_id: int
    seller_id: int
    stock_id: int
    quantity: int
    total_price: Decimal

class PurchaseCreate(PurchaseBase):
    pass

class Purchase(PurchaseBase):
    id: int

    class Config:
        orm_mode = True
