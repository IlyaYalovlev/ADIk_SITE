import asyncio
import random
import smtplib

import aiosmtplib
from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import BaseModel, EmailStr
from decimal import Decimal
from faker import Faker
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app import schemas, crud
from app.database import get_db_session, get_db
from app.crud import create_stock_item, get_users, create_user, get_products, \
    get_stock_items, get_customers, get_user_by_id, get_sellers, update_customer, update_seller, update_stock, \
    get_user_by_email, send_email
from app.main import create_purchase
from fastapi_login import LoginManager
import os
import smtplib
from email.mime.text import MIMEText
from email.header import Header




SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

manager = LoginManager(SECRET_KEY, token_url='/login', use_cookie=False)
from app.models import Users

fake = Faker()

load_dotenv('app/parcer.env')

# async def send_email(email: str, msg_text: str):
#
#     login = os.getenv('EMAIL')
#     password = os.getenv('PASSWORD')
#     print(login, password)
#
#     msg = MIMEText(f'{msg_text}', 'plain', 'utf-8')
#     msg['Subject'] = Header('Adik_store', 'utf-8')
#     msg['From'] = login
#     msg['To'] = email
#
#     smtp_server = 'smtp.yandex.ru'
#     smtp_port = 587
#
#     try:
#         await aiosmtplib.send(
#             msg,
#             hostname=smtp_server,
#             port=smtp_port,
#             start_tls=True,
#             username=login,
#             password=password,
#         )
#         print("Email sent successfully")
#     except Exception as e:
#         print(f"Failed to send email: {e}")

async def create_random_sellers_and_stock():
    stock_data = []
    async with get_db_session() as session:
        sellers = await get_sellers(session)
        products = await get_products(session)
        for _ in range(1000):
            product = random.choice(products)
            db_seller = random.choice(sellers)
            price = float(product.price) if product.price and product.price != 'None' else 100.0
            stock_data_temp = schemas.StockCreate(
                product_id=product.product_id,
                seller_id=db_seller.id,
                size = round(random.uniform(6.0, 14.0) / 0.5) * 0.5,
                quantity=random.randint(1, 50),
                price=Decimal(price),
                discount_price=round(random.uniform(10, price), 2) if price > 10 else Decimal(0.0)
            )
            stock_data.append(stock_data_temp)

    async with get_db_session() as session:
        for stock_data_temp in stock_data:
            await create_stock_item(session, stock_data_temp)

async def create_random_customers_and_purchases():
    purchase_data = []
    async with get_db_session() as session:
        stock_items = await get_stock_items(session)
        customers = await get_customers(session)
        for _ in range(100):
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
        await create_purchase(purchase_data_temp, session)


async def check_stock_items():
    async with get_db_session() as session:
        stock_items = await get_stock_items(session, 0, 10000)
        items_to_delete = []
        for item in stock_items:
            print(item.quantity)
            if item.quantity < 1:
                await session.delete(item)
        print(stock_items)
        # Фиксируем изменения в базе данных
        await session.commit()


async def add_random_passwords():
    user_passwords = {}

    async with get_db_session() as session:
        users = await session.execute(select(Users))
        users = users.scalars().all()
        for user in users:
            random_password = fake.password()
            user.set_password(random_password)
            print(f"User: {user.email}, Password: {random_password}")
            user_passwords[user.email] = random_password
        await session.commit()

    # Сохранение паролей в файл
    with open("passwords.txt", "w") as f:
        f.write("Users Passwords:\n")
        for email, password in user_passwords.items():
            f.write(f"Email: {email}, Password: {password}\n")

async def check_passy():

    async with get_db_session() as session:
        email = 'xsingleton@example.net'
        user = await get_user_by_email(session, email)
        if user:
            print(user.check_password('_%%2Mi9DO3'))
        else:
            print("User not found")

if __name__ == "__main__":
    #asyncio.run(send_email('yak9os@gmail.com', 'соси жопу'))
    #asyncio.run(create_random_sellers_and_stock())
    #asyncio.run(create_random_customers_and_purchases())
    #asyncio.run(add_random_passwords())
    #asyncio.run(check_passy())
    #asyncio.run(check_stock_items())
