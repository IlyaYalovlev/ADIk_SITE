import os
import uuid
from email.header import Header
from email.mime.text import MIMEText
from typing import Tuple, List
import aiofiles
import aiosmtplib
from fastapi import HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from config import EMAIL, PASSWORD
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
        .limit(50)
    )
    stocks = result.scalars().all()
    products = []
    for stock in stocks:
        product_data = {
            "product_id": stock.product.product_id,
            "image_side_url": stock.product.image_side_url,
            "image_top_url": stock.product.image_top_url,
            "image_34_url": stock.product.image_34_url,
            "model_name": stock.product.model_name,
            "price": stock.price,
            "discount_price": stock.discount_price,
            "discount": round((1 - stock.discount_price / stock.price) * 100, 2) if stock.price else 0,
        }
        products.append(product_data)
    filtered_products = []
    seen_models = set()
    for product in products:
        if product['model_name'] not in seen_models:
            filtered_products.append(product)
            seen_models.add(product['model_name'])
    paginated_products = filtered_products[:28]
    return paginated_products

async def get_mens_shoes(db: AsyncSession, page: int, per_page: int):
    result = await db.execute(
        select(Stock)
        .join(Product)
        .options(selectinload(Stock.product))
        .filter(Product.gender.in_(['M', 'U']))
    )
    stocks = result.scalars().all()
    total_query = await db.execute(
        select(func.count())
        .select_from(Stock)
        .join(Product)
        .filter(Product.gender.in_(['M', 'U']))
    )
    products = []
    for stock in stocks:
        product_data = {
            "product_id": stock.product.product_id,
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

async def get_kids_shoes(db: AsyncSession, page: int, per_page: int):
    result = await db.execute(
        select(Stock)
        .join(Product)
        .options(selectinload(Stock.product))
        .filter(Product.gender.in_(['K']))
    )
    stocks = result.scalars().all()
    total_query = await db.execute(
        select(func.count())
        .select_from(Stock)
        .join(Product)
        .filter(Product.gender.in_(['K']))
    )
    products = []
    for stock in stocks:
        product_data = {
            "product_id": stock.product.product_id,
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

async def get_womens_shoes(db: AsyncSession, page: int, per_page: int):
    result = await db.execute(
        select(Stock)
        .join(Product)
        .options(selectinload(Stock.product))
        .filter(Product.gender.in_(['W', 'U']))
    )
    stocks = result.scalars().all()
    total_query = await db.execute(
        select(func.count())
        .select_from(Stock)
        .join(Product)
        .filter(Product.gender.in_(['W', 'U']))
    )
    products = []
    for stock in stocks:
        product_data = {
            "product_id": stock.product.product_id,
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
        .where(Stock.quantity > 0)
    )
    products = result.scalars().all()
    product_list = []
    for product in products:
        product_data = {
            "stock_id": product.id,
            "product_id": product.product_id,
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


async def paginate_products(products: List, page: int, per_page: int) -> Tuple[List, int]:
    """
    Фильтрует товары, оставляя по одному товару с уникальными model_name,
    и выполняет пагинацию.

    :param products: Список товаров
    :param page: Номер текущей страницы
    :param per_page: Количество товаров на странице
    :return: Отфильтрованный и пагинированный список товаров и общее количество страниц
    """
    # Фильтрация товаров, чтобы оставался только один товар с одинаковым product.model_name
    filtered_products = []
    seen_models = set()
    for product in products:
        print(product['model_name'])
        if product['model_name'] not in seen_models:
            filtered_products.append(product)
            seen_models.add(product['model_name'])

    # Обновляем общее количество товаров и страниц после фильтрации
    total_filtered = len(filtered_products)
    total_pages = (total_filtered + per_page - 1) // per_page

    # Обрезаем список товаров для текущей страницы
    start = (page - 1) * per_page
    end = start + per_page
    paginated_products = filtered_products[start:end]
    print(total_filtered)
    return paginated_products, total_pages


async def save_image(file: UploadFile, folder: str) -> str:
    if not os.path.exists(folder):
        os.makedirs(folder)
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(folder, unique_filename)

    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)

    return f"/static/uploads/{unique_filename}"