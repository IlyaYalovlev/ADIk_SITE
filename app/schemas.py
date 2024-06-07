from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal

class CustomerBase(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None

class CustomerCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str

    class Config:
        from_attributes = True

class Customer(CustomerBase):
    id: int
    total_orders_value: float
    created_at: datetime

    class Config:
        from_attributes = True

class SellerBase(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    phone: str
    total_orders_value: Decimal
    created_at: datetime

    class Config:
        from_attributes = True

class SellerCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str
    total_orders_value: Decimal = Decimal('0.00')

    class Config:
        from_attributes = True

class Seller(SellerBase):
    id: int
    total_orders_value: float
    created_at: datetime

    class Config:
        from_attributes = True

class StockBase(BaseModel):
    product_id: str
    seller_id: int
    size: float
    quantity: int
    price: float
    discount_price: Optional[float] = None

class StockCreate(BaseModel):
    product_id: str
    seller_id: int
    size: float
    quantity: int
    price: float
    discount_price: float

    class Config:
        from_attributes = True

class Stock(StockBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PurchaseBase(BaseModel):
    id: int
    customer_id: int
    product_id: str
    stock_id: int
    seller_id: int
    quantity: int
    total_price: Decimal
    purchase_date: datetime

    class Config:
        from_attributes = True

class PurchaseCreate(BaseModel):
    customer_id: int
    product_id: str
    stock_id: int
    seller_id: int
    quantity: int
    total_price: Decimal

    class Config:
        from_attributes = True

class Purchase(PurchaseBase):
    id: int
    purchase_date: datetime

    class Config:
        from_attributes: True
