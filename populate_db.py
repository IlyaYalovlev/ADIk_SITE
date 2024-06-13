import asyncio
import random
from decimal import Decimal
from faker import Faker
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app import models, schemas
from app.auth import get_current_user
from app.database import get_db, get_db_session
from app.crud import create_seller, create_stock_item, create_customer, create_purchase, update_customer_password, \
    update_seller_password, get_user, load_user, get_user_details, get_customer_by_user_id
from passlib.context import CryptContext
from http import HTTPStatus
from typing import Optional
from fastapi import Header
from fastapi import Depends, HTTPException
from fastapi_login import LoginManager
from app import crud
from app.database import get_db_session
from datetime import datetime, timedelta
import jwt

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

manager = LoginManager(SECRET_KEY, token_url='/login', use_cookie=False)
from app.models import Customer, Seller, Users

fake = Faker()

async def create_random_sellers_and_stock():
    seller_data = []
    for _ in range(100):
        phone_number = fake.phone_number()
        phone_number = phone_number[:15]

        seller_data_temp = schemas.SellerCreate(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.email(),
            phone=phone_number,
        )
        seller_data.append(seller_data_temp)
    async with get_db() as session:
        for seller_data_temp in seller_data:
            await create_seller(session, seller_data_temp)
    stock_data = []
    async with get_db() as session:
        sellers = await get_sellers(session)
        products = await get_products(session)
        for _ in range(100):
            product = random.choice(products)
            db_seller = random.choice(sellers)
            price = float(product.price) if product.price is not None and product.price != 'None' else 100
            stock_data_temp = schemas.StockCreate(
                product_id=product.product_id,
                seller_id=db_seller.id,
                size=round(random.uniform(8.0, 12.0), 2),
                quantity=random.randint(1, 50),
                price=price,
                discount_price=round(random.uniform(10, price), 2) if price > 10 else 0.0
            )
            stock_data.append(stock_data_temp)
    async with get_db() as session:
        for stock_data_temp in stock_data:
            await create_stock_item(session, stock_data_temp)

async def create_random_customers_and_purchases():
    customer_data = []
    for _ in range(100):
        phone_number = fake.phone_number()
        if len(phone_number) > 15:
            phone_number = phone_number[:15]

        customer_data_temp = schemas.CustomerCreate(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.email(),
            phone=phone_number,
            total_orders_value=Decimal('0.00')
        )
        customer_data.append(customer_data_temp)
    for customer_data_temp in customer_data:
        await create_customer(customer_data_temp)
    purchase_data = []
    async with get_db() as session:
        stock_items = await get_stock_items(session)
        customers = await get_customers(session)
        num_purchases = random.randint(0, 10)
        for _ in range(num_purchases):
            db_customer = random.choice(customers)
            if not stock_items:
                break

            stock_item = random.choice(stock_items)
            quantity = random.randint(1, stock_item.quantity)

            if stock_item.quantity < quantity:
                continue

            total_price = Decimal(quantity) * (stock_item.price - stock_item.discount_price)
            purchase_data_temp = schemas.PurchaseCreate(
                customer_id=db_customer.id,
                product_id=stock_item.product_id,
                stock_id=stock_item.id,
                seller_id=stock_item.seller_id,
                quantity=quantity,
                total_price=total_price
            )
            purchase_data.append(purchase_data_temp)
            stock_item.quantity -= quantity
            if stock_item.quantity == 0:
                stock_items.remove(stock_item)

    for purchase_data_temp in purchase_data:
        await create_purchase(purchase_data_temp)

async def add_random_passwords():
    customer_passwords = {}


    async with get_db_session() as session:
        users = await session.execute(select(Users))
        users = users.scalars().all()
        for user in users:
            random_password = fake.password()
            user.set_password(random_password)
            print(random_password)
            customer_passwords[user.email] = random_password


    # Сохранение паролей в файл
    with open("passwords.txt", "w") as f:
        f.write("Users Passwords:\n")
        for customer_id, password in customer_passwords.items():
            f.write(f"Customer ID: {customer_id}, Password: {password}\n")
async def check_passy():
    async with get_db_session() as session:
        email = 'davidlane@example.org'
        user = await load_user(email, session)
        #user = await get_user(session, 18)
        #user.set_password('y2^3Owdu#)')
        print(user.check_password('L^(6m6DatJ'))





if __name__ == "__main__":
    asyncio.run(create_random_sellers_and_stock())
    asyncio.run(create_random_customers_and_purchases())
    asyncio.run(add_random_passwords())



