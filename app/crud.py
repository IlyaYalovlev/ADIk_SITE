from email.header import Header
from email.mime.text import MIMEText
from .config import PASSWORD, EMAIL
import aiosmtplib
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from . import models, schemas
from decimal import Decimal
from .models import Stock, Product, Users, Purchase



# User CRUD operations
async def create_user(db: AsyncSession, user: schemas.UserCreate):
    db_user = models.Users(**user.dict())
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def get_user_by_id(db: AsyncSession, user_id: int):
    result = await db.execute(select(models.Users).filter(models.Users.id == user_id))
    return result.scalars().first()

async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(models.Users).filter(models.Users.email == email))
    return result.scalars().first()

async def get_users(db: AsyncSession, skip: int = 0, limit: int = 10):
    result = await db.execute(select(models.Users).offset(skip).limit(limit))
    return result.scalars().all()

async def update_user_password(db: AsyncSession, user_id: int, new_password: str):
    db_user = await get_user_by_id(db, user_id)
    if db_user:
        db_user.set_password(new_password)
        await db.commit()
        await db.refresh(db_user)
    else:
        raise HTTPException(status_code=404, detail="User not found")

# Stock
async def get_stock_item(db: AsyncSession, stock_id: int):
    result = await db.execute(select(models.Stock).filter(models.Stock.id == stock_id))
    return result.scalars().first()

async def get_stock_items(db: AsyncSession, skip: int = 0, limit: int = 10):
    result = await db.execute(select(models.Stock).offset(skip).limit(limit))
    return result.scalars().all()

async def create_stock_item(db: AsyncSession, stock: schemas.StockCreate):
    db_stock = models.Stock(**stock.dict())
    db.add(db_stock)
    await db.commit()
    await db.refresh(db_stock)
    return db_stock

# Purchases
async def get_purchase(db: AsyncSession, purchase_id: int):
    result = await db.execute(select(models.Purchase).filter(models.Purchase.id == purchase_id))
    return result.scalars().first()

async def get_purchases(db: AsyncSession, skip: int = 0, limit: int = 10):
    result = await db.execute(select(models.Purchase).offset(skip).limit(limit))
    return result.scalars().all()

async def create_purchase(db: AsyncSession, purchase: schemas.PurchaseCreate):
    db_purchase = models.Purchase(**purchase.dict())
    db.add(db_purchase)
    await db.commit()
    await db.refresh(db_purchase)
    return db_purchase

async def update_customer(db: AsyncSession, purchase: schemas.PurchaseCreate):
    db_customer = await get_user_by_id(db, purchase.customer_id)
    if db_customer:
        db_customer.total_orders_value += Decimal(purchase.total_price)
        await db.commit()
        await db.refresh(db_customer)
    else:
        raise HTTPException(status_code=404, detail="Customer not found")

async def update_seller(db: AsyncSession, purchase: schemas.PurchaseCreate):
    db_seller = await get_user_by_id(db, purchase.seller_id)
    if db_seller:
        if db_seller.total_orders_value is None:
            db_seller.total_orders_value = Decimal('0.00')
        db_seller.total_orders_value += Decimal(purchase.total_price)
        await db.commit()
        await db.refresh(db_seller)
    else:
        raise HTTPException(status_code=404, detail="Seller not found")

async def update_stock(db: AsyncSession, purchase: schemas.PurchaseCreate):
    db_stock = await get_stock_item(db, purchase.stock_id)
    if db_stock:
        db_stock.quantity -= purchase.quantity
        if db_stock.quantity == 0:
            await db.delete(db_stock)
        await db.commit()
        await db.refresh(db_stock)
    else:
        raise HTTPException(status_code=404, detail="Stock item not found")

async def get_popular_products(db: AsyncSession):
    result = await db.execute(
        select(models.Stock)
        .options(selectinload(models.Stock.product), selectinload(models.Stock.seller))
        .order_by(models.Stock.quantity.desc())
        .limit(24)
    )
    stocks = result.scalars().all()
    products = []
    for stock in stocks:
        product_data = {
            "image_side_url": stock.product.image_side_url,
            "image_top_url": stock.product.image_top_url,
            "image_34_url": stock.product.image_34_url,
            "model_name": stock.product.model_name,
            "price": stock.price,
            "discount_price": stock.discount_price,
            "discount": round((1 - stock.discount_price / stock.price) * 100, 2) if stock.price else 0,
        }
        products.append(product_data)
    return products

async def get_mens_shoes(db: AsyncSession, page: int, per_page: int):
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Stock)
        .join(Product)
        .options(selectinload(Stock.product))
        .filter(Product.gender.in_(['M', 'U']))
        .offset(offset)
        .limit(per_page)
    )
    stocks = result.scalars().all()
    total_query = await db.execute(
        select(func.count())
        .select_from(Stock)
        .join(Product)
        .filter(Product.gender.in_(['M', 'U']))
    )
    total = total_query.scalar_one()
    products = []
    for stock in stocks:
        product_data = {
            "image_side_url": stock.product.image_side_url,
            "image_top_url": stock.product.image_top_url,
            "image_34_url": stock.product.image_34_url,
            "model_name": stock.product.model_name,
            "price": stock.price,
            "discount_price": stock.discount_price,
            "discount": round((1 - stock.discount_price / stock.price) * 100, 2) if stock.price else 0,
        }
        products.append(product_data)
    return products, total

async def get_kids_shoes(db: AsyncSession, page: int, per_page: int):
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Stock)
        .join(Product)
        .options(selectinload(Stock.product))
        .filter(Product.gender.in_(['K']))
        .offset(offset)
        .limit(per_page)
    )
    stocks = result.scalars().all()
    total_query = await db.execute(
        select(func.count())
        .select_from(Stock)
        .join(Product)
        .filter(Product.gender.in_(['K']))
    )
    total = total_query.scalar_one()
    products = []
    for stock in stocks:
        product_data = {
            "image_side_url": stock.product.image_side_url,
            "image_top_url": stock.product.image_top_url,
            "image_34_url": stock.product.image_34_url,
            "model_name": stock.product.model_name,
            "price": stock.price,
            "discount_price": stock.discount_price,
            "discount": round((1 - stock.discount_price / stock.price) * 100, 2) if stock.price else 0,
        }
        products.append(product_data)
    return products, total

async def get_womens_shoes(db: AsyncSession, page: int, per_page: int):
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Stock)
        .join(Product)
        .options(selectinload(Stock.product))
        .filter(Product.gender.in_(['W', 'U']))
        .offset(offset)
        .limit(per_page)
    )
    stocks = result.scalars().all()
    total_query = await db.execute(
        select(func.count())
        .select_from(Stock)
        .join(Product)
        .filter(Product.gender.in_(['W', 'U']))
    )
    total = total_query.scalar_one()
    products = []
    for stock in stocks:
        product_data = {
            "image_side_url": stock.product.image_side_url,
            "image_top_url": stock.product.image_top_url,
            "image_34_url": stock.product.image_34_url,
            "model_name": stock.product.model_name,
            "price": stock.price,
            "discount_price": stock.discount_price,
            "discount": round((1 - stock.discount_price / stock.price) * 100, 2) if stock.price else 0,
        }
        products.append(product_data)
    return products, total

async def get_products(session: AsyncSession):
    result = await session.execute(select(models.Product))
    products = result.scalars().all()
    return products

async def get_customers(session: AsyncSession):
    result = await session.execute(select(Users).where(Users.user_type == 'customer'))
    return result.scalars().all()

async def get_sellers(session: AsyncSession):
    result = await session.execute(select(Users).where(Users.user_type == 'seller'))
    return result.scalars().all()


async def get_customer_purchases(user_id: int, db: AsyncSession):
    result = await db.execute(
        select(Purchase)
        .options(joinedload(Purchase.stock).joinedload(Stock.product))
        .where(Purchase.customer_id == user_id)
    )
    purchases = result.scalars().all()
    purchase_list = []
    for purchase in purchases:
        purchase_data = {
            "date": purchase.purchase_date.strftime("%Y-%m-%d %H:%M:%S"),  # форматирование даты и времени
            "product_name": purchase.stock.product.model_name,  # название продукта
            "total_price": purchase.total_price  # стоимость
        }
        purchase_list.append(purchase_data)
    return purchase_list

async def get_seller_sales(user_id: int, db: AsyncSession):
    result = await db.execute(
        select(Purchase)
        .options(joinedload(Purchase.stock).joinedload(Stock.product))
        .where(Purchase.seller_id == user_id)
    )
    sales = result.scalars().all()
    sales_list = []
    for sale in sales:
        sale_data = {
            "date": sale.purchase_date.strftime("%Y-%m-%d %H:%M:%S"),  # форматирование даты и времени
            "product_name": sale.stock.product.model_name,  # название продукта
            "total_price": sale.total_price,  # стоимость
            "quantity": sale.quantity
        }
        sales_list.append(sale_data)
    return sales_list

async def get_seller_products(user_id: int, db: AsyncSession):
    result = await db.execute(
        select(Stock)
        .options(joinedload(Stock.product))
        .where(Stock.seller_id == user_id)
    )
    products = result.scalars().all()
    product_list = []
    for product in products:
        product_data = {
            "name": product.product.model_name,
            "price": product.discount_price,
            "size": product.size,
            "stock": product.quantity
        }
        product_list.append(product_data)
    return product_list


async def send_email(email: str, msg_text: str):
    login = EMAIL
    password = PASSWORD
    msg = MIMEText(f'{msg_text}', 'plain', 'utf-8')
    msg['Subject'] = Header('Adik_store', 'utf-8')
    msg['From'] = login
    msg['To'] = email

    smtp_server = 'smtp.yandex.ru'
    smtp_port = 587

    try:
        await aiosmtplib.send(
            msg,
            hostname=smtp_server,
            port=smtp_port,
            start_tls=True,
            username=login,
            password=password,
        )
        print("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email: {e}")
