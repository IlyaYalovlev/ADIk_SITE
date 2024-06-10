from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from . import models, schemas
from decimal import Decimal

from .database import get_db
from .models import Stock, Product, Customer, Seller


# Customers
async def get_customer(db: AsyncSession, customer_id: int):
    result = await db.execute(select(models.Customer).filter(models.Customer.id == customer_id))
    return result.scalars().first()

async def get_customers(db: AsyncSession, skip: int = 0, limit: int = 10):
    result = await db.execute(select(models.Customer).offset(skip).limit(limit))
    return result.scalars().all()

async def create_customer(db: AsyncSession, customer: schemas.CustomerCreate):
    db_customer = models.Customer(**customer.dict())
    db.add(db_customer)
    await db.commit()
    await db.refresh(db_customer)
    return db_customer

# Sellers
async def get_seller(db: AsyncSession, seller_id: int):
    result = await db.execute(select(models.Seller).filter(models.Seller.id == seller_id))
    return result.scalars().first()

async def get_sellers(db: AsyncSession, skip: int = 0, limit: int = 10):
    result = await db.execute(select(models.Seller).offset(skip).limit(limit))
    return result.scalars().all()

async def create_seller(db: AsyncSession, seller: schemas.SellerCreate):
    db_seller = models.Seller(**seller.dict())
    db.add(db_seller)
    await db.commit()
    await db.refresh(db_seller)
    return db_seller

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
    # Создаем запись покупки
    db_purchase = models.Purchase(**purchase.dict())
    db.add(db_purchase)
    await db.commit()
    await db.refresh(db_purchase)
    return db_purchase

async def update_customer(db: AsyncSession, purchase: schemas.PurchaseCreate):
    # Обновляем общую сумму заказов для покупателя
    db_customer = await get_customer(db, purchase.customer_id)
    db_customer.total_orders_value += Decimal(purchase.total_price)
    await db.commit()
    await db.refresh(db_customer)

async def update_seller(db: AsyncSession, purchase: schemas.PurchaseCreate):
    # Обновляем общую сумму заказов для продавца
    db_seller = await get_seller(db, purchase.seller_id)
    if db_seller.total_orders_value is None:
        db_seller.total_orders_value = Decimal('0.00')
    db_seller.total_orders_value += Decimal(purchase.total_price)
    await db.commit()
    await db.refresh(db_seller)

async def update_stock(db: AsyncSession, purchase: schemas.PurchaseCreate):
    # Обновляем общую сумму заказов для продавца
    db_stock = await get_stock_item(db, purchase.stock_id)
    db_stock.quantity -= purchase.quantity
    if db_stock.quantity == 0:
        db_stock.remove(db_stock)
    await db.commit()
    await db.refresh(db_stock)




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

    # Запрос для получения мужских кроссовок с учетом пагинации
    result = await db.execute(
        select(Stock)
        .join(Product)
        .options(selectinload(Stock.product))
        .filter(Product.gender.in_(['M', 'U']))
        .offset(offset)
        .limit(per_page)
    )
    stocks = result.scalars().all()

    # Запрос для получения общего количества мужских кроссовок
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

    # Запрос для получения мужских кроссовок с учетом пагинации
    result = await db.execute(
        select(Stock)
        .join(Product)
        .options(selectinload(Stock.product))
        .filter(Product.gender.in_(['K']))
        .offset(offset)
        .limit(per_page)
    )
    stocks = result.scalars().all()

    # Запрос для получения общего количества мужских кроссовок
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

    # Запрос для получения мужских кроссовок с учетом пагинации
    result = await db.execute(
        select(Stock)
        .join(Product)
        .options(selectinload(Stock.product))
        .filter(Product.gender.in_(['W','U']))
        .offset(offset)
        .limit(per_page)
    )
    stocks = result.scalars().all()

    # Запрос для получения общего количества мужских кроссовок
    total_query = await db.execute(
        select(func.count())
        .select_from(Stock)
        .join(Product)
        .filter(Product.gender.in_(['W','U']))
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


async def update_customer_password(session: AsyncSession, customer_id: int, password_hash: str):
    result = await session.execute(select(Customer).filter(Customer.id == customer_id))
    customer = result.scalar_one()
    customer.password_hash = password_hash
    await session.commit()

async def update_seller_password(session: AsyncSession, seller_id: int, password_hash: str):
    result = await session.execute(select(Seller).filter(Seller.id == seller_id))
    seller = result.scalar_one()
    seller.password_hash = password_hash
    await session.commit()