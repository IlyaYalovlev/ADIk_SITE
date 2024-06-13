from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from decimal import Decimal
from passlib.hash import bcrypt


class Users(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    user_type = Column(String, nullable=False)  # 'customer' или 'seller'
    first_name = Column(String, index=True)
    last_name = Column(String, index=True)
    total_orders_value = Column(Numeric(10, 2), default=0.0)

    created_at = Column(TIMESTAMP, server_default=func.now())

    def set_password(self, password):
        self.password_hash = bcrypt.hash(password)

    def check_password(self, password):
        return bcrypt.verify(password, self.password_hash)


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
    stock = relationship("Stock", back_populates="purchases")


class Product(Base):
    __tablename__ = 'adidas_products'

    product_id = Column(String, primary_key=True, index=True)
    brand = Column(String)
    category = Column(String)
    model_name = Column(String)
    color = Column(String)
    price = Column(String)
    discount = Column(String)
    image_side_url = Column(String)
    image_top_url = Column(String)
    image_34_url = Column(String)
    gender = Column(String)

    stocks = relationship('Stock', back_populates='product')
