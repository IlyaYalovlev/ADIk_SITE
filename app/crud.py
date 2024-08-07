import os
import uuid
from datetime import datetime
from email.header import Header
from email.mime.text import MIMEText
from typing import Tuple, List
import aiofiles
import aiosmtplib
import stripe
from fastapi import HTTPException, UploadFile, Depends
from sqlalchemy import func, delete
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from config import EMAIL, PASSWORD
from . import models, schemas
from decimal import Decimal

from .database import get_db
from .models import Stock, Product, Users, Purchase, Cart, CartItem, DeliveryDetails
from .schemas import DeliveryDetailsCreate, PurchaseCreate


# User CRUD operations
async def get_user_by_id(db: AsyncSession, user_id: int):
    result = await db.execute(select(models.Users).filter(models.Users.id == user_id))
    return result.scalars().first()

async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(models.Users).filter(models.Users.email == email))
    return result.scalars().first()

async def get_user_by_phone(db: AsyncSession, phone: str):
    result = await db.execute(select(models.Users).filter(models.Users.phone == phone))
    return result.scalars().first()


# Stock CRUD operations
async def get_stock_item(db: AsyncSession, stock_id: int):
    result = await db.execute(select(models.Stock).filter(models.Stock.id == stock_id))
    return result.scalars().first()


async def create_stock_item(db: AsyncSession, stock: schemas.StockCreate):
    db_stock = models.Stock(**stock.dict())
    db.add(db_stock)
    await db.commit()
    await db.refresh(db_stock)
    return db_stock

# Purchases CRUD operations
async def get_purchase(db: AsyncSession, purchase_id: int):
    result = await db.execute(select(models.Purchase).filter(models.Purchase.id == purchase_id))
    return result.scalars().first()


async def create_purchase(db: AsyncSession, purchase: schemas.PurchaseCreate):
    db_purchase = models.Purchase(**purchase.dict())
    db.add(db_purchase)
    await db.commit()
    await db.refresh(db_purchase)
    return db_purchase

async def update_customer(db: AsyncSession, purchase: PurchaseCreate):
    db_customer = await get_user_by_id(db, purchase.customer_id)
    if db_customer:
        await db_customer.update_total_orders_value(db, purchase.total_price)
    else:
        raise HTTPException(status_code=404, detail="Customer not found")

async def update_seller(db: AsyncSession, purchase: PurchaseCreate):
    db_seller = await get_user_by_id(db, purchase.seller_id)
    if db_seller:
        await db_seller.update_total_orders_value(db, purchase.total_price)
    else:
        raise HTTPException(status_code=404, detail="Seller not found")

async def update_stock(db: AsyncSession, purchase: PurchaseCreate):
    db_stock = await get_stock_item(db, purchase.stock_id)
    if db_stock:
        await db_stock.decrease_quantity(db, purchase.quantity)
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

async def get_mens_shoes(db: AsyncSession, page: int, per_page: int, min_price: float = None, max_price: float = None, sizes: List[float] = None, sort: str = None):
    query = select(Stock).join(Product).options(selectinload(Stock.product)).filter(Product.gender.in_(['M', 'U']))
    if min_price is not None:
        query = query.filter(Stock.price >= min_price)
    if max_price is not None:
        query = query.filter(Stock.price <= max_price)
    if sizes:
        query = query.filter(Stock.size.in_(sizes))
    if sort == 'price-asc':
        query = query.order_by(Stock.price.asc())
    elif sort == 'price-desc':
        query = query.order_by(Stock.price.desc())
    elif sort == 'discount-desc':
        query = query.order_by((Stock.price - Stock.discount_price).desc())
    elif sort == 'newest':
        query = query.order_by(Stock.created_at.desc())
    result = await db.execute(query)
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

async def get_kids_shoes(db: AsyncSession, page: int, per_page: int, min_price: float = None, max_price: float = None, sizes: List[float] = None, sort: str = None):
    query = select(Stock).join(Product).options(selectinload(Stock.product)).filter(Product.gender.in_(['K']))
    if min_price is not None:
        query = query.filter(Stock.price >= min_price)
    if max_price is not None:
        query = query.filter(Stock.price <= max_price)
    if sizes:
        query = query.filter(Stock.size.in_(sizes))
    if sort == 'price-asc':
        query = query.order_by(Stock.price.asc())
    elif sort == 'price-desc':
        query = query.order_by(Stock.price.desc())
    elif sort == 'discount-desc':
        query = query.order_by((Stock.price - Stock.discount_price).desc())
    elif sort == 'newest':
        query = query.order_by(Stock.created_at.desc())
    result = await db.execute(query)
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

async def get_womens_shoes(db: AsyncSession, page: int, per_page: int, min_price: float = None, max_price: float = None, sizes: List[float] = None, sort: str = None):
    query = select(Stock).join(Product).options(selectinload(Stock.product)).filter(Product.gender.in_(['W', 'U']))
    if min_price is not None:
        query = query.filter(Stock.price >= min_price)
    if max_price is not None:
        query = query.filter(Stock.price <= max_price)
    if sizes:
        query = query.filter(Stock.size.in_(sizes))
    if sort == 'price-asc':
        query = query.order_by(Stock.price.asc())
    elif sort == 'price-desc':
        query = query.order_by(Stock.price.desc())
    elif sort == 'discount-desc':
        query = query.order_by((Stock.price - Stock.discount_price).desc())
    elif sort == 'newest':
        query = query.order_by(Stock.created_at.desc())
    result = await db.execute(query)
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
        .order_by(Purchase.purchase_date.desc())
    )
    purchases = result.scalars().all()
    purchase_list = []
    for purchase in purchases:
        purchase_data = {
            "date": purchase.purchase_date.strftime("%Y-%m-%d %H:%M:%S"),  # форматирование даты и времени
            "product_name": purchase.stock.product.model_name,  # название продукта
            "total_price": purchase.total_price,  # стоимость
            "quantity": purchase.quantity,
            "status": purchase.status,
            "tracking_number": purchase.tracking_number
        }
        purchase_list.append(purchase_data)
    return purchase_list

async def get_seller_sales(user_id: int, db: AsyncSession):
    result = await db.execute(
        select(Purchase)
        .options(joinedload(Purchase.stock).joinedload(Stock.product))
        .where(Purchase.seller_id == user_id)
        .order_by(Purchase.purchase_date.desc())
    )
    sales = result.scalars().all()
    sales_list = []
    for sale in sales:
        sale_data = {
            "id": sale.id,
            "date": sale.purchase_date.strftime("%Y-%m-%d %H:%M:%S"),  # форматирование даты и времени
            "product_name": sale.stock.product.model_name,  # название продукта
            "total_price": sale.total_price,  # стоимость
            "quantity": sale.quantity,
            "status": sale.status,
            "tracking_number": sale.tracking_number
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


async def paginate_products(products: List, page: int, per_page: int) -> Tuple[List, int]:
    """
    Фильтрует товары, оставляя по одному товару с уникальными model_name,
    и выполняет пагинацию.
    """
    # Фильтрация товаров, чтобы оставался только один товар с одинаковым product.model_name
    filtered_products = []
    seen_models = set()
    for product in products:
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

    return paginated_products, total_pages

async def save_image(file: UploadFile, folder: str) -> str:
    """
    Сохраняет изображение в указанную папку.
    """
    if not os.path.exists(folder):
        os.makedirs(folder)
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(folder, unique_filename)

    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)

    return f"/static/uploads/{unique_filename}"

async def get_cart_items_by_cart_id(cart_id: int, db: AsyncSession):
    cart_items = (await db.execute(select(CartItem).where(CartItem.cart_id == cart_id))).scalars().all()
    return cart_items

async def get_cart_items_total_quantity_by_cart_id(cart_id: int, db: AsyncSession):
    total_quantity = await db.execute(
        select(func.sum(CartItem.quantity)).where(CartItem.cart_id == cart_id)
    )
    return total_quantity.scalar() or 0

async def get_cart_items_by_user_id(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(CartItem).join(Cart).where(Cart.user_id == user_id)
    )
    return result.scalars().all()

async def create_delivery_details(db: AsyncSession, delivery_details: DeliveryDetailsCreate):
    db_delivery_details = DeliveryDetails(**delivery_details.dict())
    db.add(db_delivery_details)
    await db.commit()
    await db.refresh(db_delivery_details)
    return db_delivery_details


async def delete_cart_items_by_user_id(db: AsyncSession, user_id: int):
    cart = await db.execute(select(Cart).where(Cart.user_id == user_id))
    cart = cart.scalars().first()

    if cart:
        cart_items = await db.execute(select(CartItem).where(CartItem.cart_id == cart.id))
        cart_items = cart_items.scalars().all()

        for item in cart_items:
            await item.remove(db)

    await db.commit()

async def create_delivery_details(db: AsyncSession, delivery_details: schemas.DeliveryDetailsС):
    db_delivery = models.DeliveryDetails(**delivery_details.dict())
    db.add(db_delivery)
    await db.commit()
    await db.refresh(db_delivery)
    return db_delivery

async def get_product_id_by_stock_id(db: AsyncSession, stock_id: int):
    result = await db.execute(
        select(Stock.product_id).where(Stock.id == stock_id)
    )
    return result.scalar()

async def create_purchase_full(order_details: schemas.OrderDetails, db: AsyncSession = Depends(get_db)):
    """
    Создание полной покупки, включая обновление данных о покупателе, продавце и товаре.
    """
    user_id = order_details.user_id
    payment_intent_id = order_details.payment_intent_id
    delivery_details = order_details.delivery_details

    try:
        # Проверка платежа
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        if payment_intent.status != 'succeeded':
            raise HTTPException(status_code=400, detail="Оплата не прошла")

        # Получаем данные из корзины
        cart_items = await get_cart_items_by_user_id(db, user_id)
        if not cart_items:
            raise HTTPException(status_code=400, detail="Корзина пуста")

        # Создание заказа
        for item in cart_items:
            stock = await get_stock_item(db, item.stock_id)
            purchase_data = schemas.PurchaseCreate(
                customer_id=user_id,
                product_id=stock.product_id,
                stock_id=item.stock_id,
                seller_id=stock.seller_id,
                quantity=item.quantity,
                total_price=stock.discount_price
            )
            await update_customer(db, purchase_data)
            await update_seller(db, purchase_data)
            await update_stock(db, purchase_data)
            purchase = await create_purchase(db, purchase_data)

            # Сохранение информации о доставке
            delivery_data = schemas.DeliveryDetailsС(
                purchase_id=purchase.id,
                city=delivery_details.city,
                street=delivery_details.street,
                house_number=delivery_details.house_number,
                apartment_number=delivery_details.apartment_number,
                recipient_name=delivery_details.recipient_name,
                phone=delivery_details.phone
            )
            await create_delivery_details(db, delivery_data)

        # Удаление элементов из корзины
        await delete_cart_items_by_user_id(db, user_id)

        return {"status": "success", "detail": "Заказ успешно создан"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



async def get_product_by_id(db: AsyncSession, product_id: str):
    result = await db.execute(select(Product).where(Product.product_id == product_id))
    return result.scalars().first()


async def get_suggestions(db: AsyncSession, query: str):
    result = await db.execute(
        select(Product)
        .join(Stock, Product.product_id == Stock.product_id)
        .where(Product.model_name.ilike(f"%{query.lower()}%"))
        .where(Stock.quantity > 0)
    )
    return result.scalars().first()

async def get_cart_by_userid(db: AsyncSession, user_id: str):
    result = await db.execute(select(Cart).where(Cart.user_id == user_id))
    return result.scalars().first()

async def get_cart_by_sessionid(db: AsyncSession, session_id: str):
    result = await db.execute(select(Cart).where(Cart.session_id == session_id))
    return result.scalars().first()


async def get_delivery_details_by_purchase_id(db: AsyncSession, purchase_id: str):
    result = await db.execute(
        select(DeliveryDetails)
        .where(DeliveryDetails.purchase_id == purchase_id)
    )
    return result.scalars().first()