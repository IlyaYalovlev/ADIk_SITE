import uuid
from decimal import Decimal

from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, TIMESTAMP, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from passlib.hash import bcrypt

class Users(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    user_type = Column(String, nullable=False) # 'customer' или 'seller'
    first_name = Column(String, index=True)
    last_name = Column(String, index=True)
    total_orders_value = Column(Numeric(10, 2), default=0.0)
    created_at = Column(TIMESTAMP, server_default=func.now())
    is_active = Column(Boolean, default=False)


    stocks = relationship("Stock", back_populates="seller", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = bcrypt.hash(password)

    def check_password(self, password):
        return bcrypt.verify(password, self.password_hash)

    def activate(self):
        self.is_active = True

    async def update_total_orders_value(self, db, amount):
        if self.total_orders_value is None:
            self.total_orders_value = Decimal('0.00')
        self.total_orders_value += Decimal(amount)
        db.add(self)
        await db.commit()
        await db.refresh(self)

class Stock(Base):
    __tablename__ = 'stock'
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String, ForeignKey('adidas_products.product_id'))
    seller_id = Column(Integer, ForeignKey('users.id'))
    size = Column(Numeric(10, 2))
    quantity = Column(Integer)
    price = Column(Numeric(10, 2))
    discount_price = Column(Numeric(10, 2))
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    product = relationship("Product", back_populates="stocks")
    seller = relationship("Users", back_populates="stocks")
    purchases = relationship("Purchase", back_populates="stock")
    cart_items = relationship("CartItem", back_populates="stock")

    def set_discount_price(self, discount_price):
        self.discount_price = discount_price

    def set_quantity(self, quantity):
        self.quantity = quantity

    async def decrease_quantity(self, db, amount):
        self.quantity -= amount
        if self.quantity <= 0:
            await db.delete(self)
        else:
            db.add(self)
        await db.commit()
        await db.refresh(self)

    async def update_quantity(self, db, quantity):
        self.set_quantity(quantity)
        db.add(self)
        await db.commit()
        await db.refresh(self)

class Purchase(Base):
    __tablename__ = 'purchases'
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey('users.id'))
    product_id = Column(String, ForeignKey('adidas_products.product_id'))
    stock_id = Column(Integer, ForeignKey('stock.id'))
    seller_id = Column(Integer, ForeignKey('users.id'))
    quantity = Column(Integer)
    total_price = Column(Numeric(10, 2))
    purchase_date = Column(TIMESTAMP, server_default=func.now())
    status = Column(String, default="paid")
    tracking_number = Column(String)

    stock = relationship("Stock", back_populates="purchases")
    customer = relationship("Users", foreign_keys=[customer_id])
    seller = relationship("Users", foreign_keys=[seller_id])
    delivery_details = relationship("DeliveryDetails", uselist=False, back_populates="purchase")

    def set_status(self, new_status):
        self.status = new_status

    def set_track(self, tracking_number):
        self.tracking_number = tracking_number if tracking_number != "undefined" else None


class Product(Base):
    __tablename__ = 'adidas_products'
    product_id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    brand = Column(String)
    category = Column(String)
    model_name = Column(String)
    color = Column(String, default=None)
    price = Column(String)
    discount = Column(String)
    image_side_url = Column(String)
    image_top_url = Column(String)
    image_34_url = Column(String)
    gender = Column(String)
    is_active = Column(Boolean, default=False)

    stocks = relationship('Stock', back_populates='product')

    async def update_activation_status(self, db, is_active):
        self.is_active = is_active
        db.add(self)
        await db.commit()
        await db.refresh(self)

class Cart(Base):
    __tablename__ = 'carts'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    session_id = Column(String, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

class CartItem(Base):
    __tablename__ = 'cart_items'
    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey('carts.id'))
    stock_id = Column(Integer, ForeignKey('stock.id'))
    quantity = Column(Integer, default=1)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    cart = relationship("Cart", back_populates="items")
    stock = relationship("Stock", back_populates="cart_items")

    def set_quantity(self, quantity):
        self.quantity = quantity

    async def remove(self, db):
        await db.delete(self)
        await db.commit()

class DeliveryDetails(Base):
    __tablename__ = 'delivery_details'
    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey('purchases.id'))
    city = Column(String, nullable=False)
    street = Column(String, nullable=False)
    house_number = Column(String, nullable=False)
    apartment_number = Column(String)
    recipient_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    purchase = relationship("Purchase", back_populates="delivery_details")