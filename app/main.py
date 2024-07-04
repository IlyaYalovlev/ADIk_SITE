import json
import os
import uuid
from datetime import datetime

import aiofiles
from decimal import Decimal
from typing import Optional, List, Dict, Any

import stripe
from fastapi import HTTPException, status, UploadFile, File, Cookie
from jwt.exceptions import ExpiredSignatureError
from fastapi import Header
from jwt import decode as jwt_decode
from fastapi import FastAPI, Depends, HTTPException, Form, Request,  Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.functions import user
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from fastapi import Response
from config import SECRET, API_KEY
from . import schemas, crud
from .auth import create_access_token, get_current_user_id, generate_confirmation_token, confirm_token
from .crud import get_popular_products, update_customer, update_seller, update_stock, get_mens_shoes, get_womens_shoes, \
    get_kids_shoes, get_user_by_id, get_user_by_email, get_customer_purchases, get_seller_sales, get_seller_products, \
    get_products, paginate_products, save_image, get_cart_items_total_quantity_by_cart_id, get_cart_items_by_cart_id, \
    get_product_id_by_stock_id, get_stock_item, create_purchase, create_purchase_full, get_purchase
from .database import get_db
from .models import Users, Product, Stock, Cart, CartItem, Purchase
from .schemas import UserDetails, StockUpdateRequest, AddToCartRequest, UpdateCartRequest, PaymentRequest, OrderDetails, \
    CreateCheckoutSessionRequest, ProductQuantityUpdateSchema, ProductActivationSchema, SaleUpdateSchema
from passlib.hash import bcrypt
from app.tasks.tasks import send_email




app = FastAPI()

stripe.api_key = API_KEY

# Настройка маршрута для статических файлов
app.mount("/static", StaticFiles(directory="static"), name="static")

# Получаем абсолютный путь к директории static
static_dir = os.path.join(os.path.dirname(__file__), "static")

# Монтируем директорию static
app.mount("/static", StaticFiles(directory=static_dir), name="static")



# Подключаем Jinja2 templates
templates = Jinja2Templates(directory="app/templates")



SECRET_KEY = SECRET
ALGORITHM = "HS256"



# Маршрут для отображения формы авторизации
@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Обработка данных авторизации
@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, email)
    if user and user.check_password(password) and user.is_active and user.user_type == 'admin':
        access_token = create_access_token(data={"sub": str(user.id)})
        return JSONResponse(status_code=200, content={"access_token": access_token, "redirect_url": "/admin"})
    elif user and user.check_password(password) and user.is_active:
        access_token = create_access_token(data={"sub": str(user.id)})
        return JSONResponse(status_code=200, content={"access_token": access_token, "redirect_url": "/"})
    else:
        return JSONResponse(status_code=401, content={"error": "Неверные учетные данные"})


@app.post("/change-password")
async def change_password(request: Request, old_password: str = Form(...), new_password: str = Form(...), db: AsyncSession = Depends(get_db)):
    authorization = request.headers.get('Authorization')
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header")

    token = authorization.split(" ")[1]
    try:
        payload = jwt_decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        user = await get_user_by_id(db, user_id)

        if not user.check_password(old_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Old password is incorrect")

        user.set_password(new_password)
        db.add(user)
        await db.commit()

        return JSONResponse(status_code=status.HTTP_200_OK, content={"detail": "Password changed successfully"})
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="JWT token has expired")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.get("/user-info", response_model=UserDetails)
async def read_user_info(request: Request, db: AsyncSession = Depends(get_db)):
    headers = request.headers
    authorization = headers.get('authorization')
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header")

    token = authorization.split(" ")[1]
    try:
        payload = jwt_decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        user = await get_user_by_id(db, user_id)

        # Create a new token with a refreshed expiration time
        new_token = create_access_token(data={"sub": str(user_id)})

        return JSONResponse(content={
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "user_type": user.user_type,
            "access_token": new_token
        })
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="JWT token has expired")




# Обновление маршрута для главной страницы
@app.get("/", response_class=HTMLResponse)
@app.post("/", response_class=HTMLResponse)
async def read_index(request: Request, authorization: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    products = await get_popular_products(db)
    return templates.TemplateResponse("index.html", {"request": request, "products": products})


def decimal_to_float(data):
    if isinstance(data, dict):
        return {k: decimal_to_float(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [decimal_to_float(v) for v in data]
    elif isinstance(data, Decimal):
        return float(data)
    elif isinstance(data, datetime):
        return data.isoformat()
    else:
        return data

# Обновление маршрута для профиля продавца
@app.get("/profile_seller/{user_id}", response_class=HTMLResponse)
async def profile_seller(user_id: int, request: Request):
    return templates.TemplateResponse("profile_seller.html", {"request": request})
@app.get("/api/profile_seller/{user_id}", response_class=JSONResponse)
async def api_profile_seller(user_id: int, db: AsyncSession = Depends(get_db), authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "Missing or invalid Authorization header"})

    token = authorization.split(" ")[1]
    current_user_id = get_current_user_id(token)

    if current_user_id is None or current_user_id != user_id:
        return JSONResponse(status_code=403, content={"detail": "Unauthorized access"})

    try:
        user = await get_user_by_id(db, user_id)
        if user.user_type != 'seller':
            return JSONResponse(status_code=403, content={"detail": "Unauthorized access"})

        # Get seller sales and products
        sales = await get_seller_sales(user_id, db)
        products = await get_seller_products(user_id, db)
        print(*products)
        response_data = {
            "user": {
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "total_orders_value": user.total_orders_value
            },
            "sales": sales,
            "products": products
        }

        response_data = decimal_to_float(response_data)

        return JSONResponse(content=response_data)
    except ExpiredSignatureError:
        return JSONResponse(status_code=401, content={"detail": "JWT token has expired"})

@app.post("/update-sale", response_class=JSONResponse)
async def update_sale(data: SaleUpdateSchema, db: AsyncSession = Depends(get_db), authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.split(" ")[1]
    current_user_id = get_current_user_id(token)

    if current_user_id is None:
        raise HTTPException(status_code=403, detail="Unauthorized access")

    sale = await get_purchase(db, data.sale_id)
    if sale is None:
        raise HTTPException(status_code=404, detail="Sale not found")

    status_map = {
        "paid": "Оплачен",
        "in_progress": "Получен",
        "shipping": "Отправлен",
        "delivered": "Доставлен"
    }

    sale.status = status_map.get(data.status, data.status)
    sale.tracking_number = data.tracking_number if data.tracking_number != "undefined" else None
    db.add(sale)
    await db.commit()

    return JSONResponse(status_code=200, content={"detail": "Sale updated successfully"})


# Обновление маршрута для профиля покупателя
@app.get("/profile_customer/{user_id}", response_class=HTMLResponse)
async def profile_customer(user_id: int, request: Request):
    return templates.TemplateResponse("profile_customer.html", {"request": request})

@app.get("/api/profile_customer/{user_id}", response_class=JSONResponse)
async def api_profile_customer(user_id: int, db: AsyncSession = Depends(get_db), authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "Missing or invalid Authorization header"})

    token = authorization.split(" ")[1]
    current_user_id = get_current_user_id(token)

    if current_user_id is None or current_user_id != user_id:
        return JSONResponse(status_code=403, content={"detail": "Unauthorized access"})

    try:
        user = await get_user_by_id(db, user_id)
        if user.user_type != 'customer':
            return JSONResponse(status_code=403, content={"detail": "Unauthorized access"})

        # Get customer purchases
        purchases = await get_customer_purchases(user_id, db)
        response_data = {
            "user": {
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "total_orders_value": user.total_orders_value
            },
            "purchases": purchases
        }

        response_data = decimal_to_float(response_data)

        return JSONResponse(status_code=200, content=response_data)

    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Маршрут для мужской обуви
@app.get("/mens-shoes", response_class=HTMLResponse)
@app.get("/mens-shoes/{page}", response_class=HTMLResponse)
async def mens_shoes(request: Request, page: int = 1, db: AsyncSession = Depends(get_db), min_price: float = Query(None), max_price: float = Query(None), sizes: str = Query(None), sort: str = Query(None)):
    per_page = 28  # количество товаров на одной странице
    size_list = list(map(float, sizes.split(','))) if sizes else []
    products = await get_mens_shoes(db, page, per_page, min_price, max_price, size_list, sort)
    paginated_products, total_pages = await paginate_products(products, page, per_page)
    return templates.TemplateResponse("mens_shoes.html", {
        "request": request,
        "products": paginated_products,
        "page": page,
        "total_pages": total_pages,
        "min_price": min_price,
        "max_price": max_price,
        "sizes": sizes,
        "sort": sort
    })

# Маршрут для женской обуви
@app.get("/womens-shoes", response_class=HTMLResponse)
@app.get("/womens-shoes/{page}", response_class=HTMLResponse)
async def womens_shoes(request: Request, page: int = 1, db: AsyncSession = Depends(get_db), min_price: float = Query(None), max_price: float = Query(None), sizes: str = Query(None), sort: str = Query(None)):
    per_page = 28  # количество товаров на одной странице
    size_list = list(map(float, sizes.split(','))) if sizes else []
    products = await get_womens_shoes(db, page, per_page, min_price, max_price, size_list, sort)
    paginated_products, total_pages = await paginate_products(products, page, per_page)
    return templates.TemplateResponse("womens_shoes.html", {
        "request": request,
        "products": paginated_products,
        "page": page,
        "total_pages": total_pages,
        "min_price": min_price,
        "max_price": max_price,
        "sizes": sizes,
        "sort": sort
    })

# Маршрут для детской обуви
@app.get("/kids-shoes", response_class=HTMLResponse)
@app.get("/kids-shoes/{page}", response_class=HTMLResponse)
async def kids_shoes(request: Request, page: int = 1, db: AsyncSession = Depends(get_db), min_price: float = Query(None), max_price: float = Query(None), sizes: str = Query(None), sort: str = Query(None)):
    per_page = 28  # количество товаров на одной странице
    size_list = list(map(float, sizes.split(','))) if sizes else []
    products = await get_kids_shoes(db, page, per_page, min_price, max_price, size_list, sort)
    paginated_products, total_pages = await paginate_products(products, page, per_page)
    return templates.TemplateResponse("kids_shoes.html", {
        "request": request,
        "products": paginated_products,
        "page": page,
        "total_pages": total_pages,
        "min_price": min_price,
        "max_price": max_price,
        "sizes": sizes,
        "sort": sort
    })


# Маршрут для отображения формы восстановления пароля
@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_form(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})


# Маршрут для обработки формы восстановления пароля
@app.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password(request: Request, email: str = Form(...), db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, email)
    if user:
        token = generate_confirmation_token(email)
        reset_url = f"http://127.0.0.1:8000/reset-password/{token}"
        msg_text = f"Перейдите по следующей ссылке для смены вашего пароля: {reset_url}"
        send_email.delay(email, msg_text)
    return templates.TemplateResponse("forgot_password_confirmation.html", {"request": request})


# Маршрут для отображения формы смены пароля
@app.get("/reset-password/{token}", response_class=HTMLResponse)
async def reset_password_form(request: Request, token: str):
    return templates.TemplateResponse("reset_password.html", {"request": request, "token": token})


@app.post("/reset-password/{token}", response_class=HTMLResponse)
async def reset_password(request: Request, token: str, new_password: str = Form(...), confirm_password: str = Form(...),
                         db: AsyncSession = Depends(get_db)):
    if new_password != confirm_password:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": "Пароли не совпадают"})

    if not any(char.isupper() for char in new_password) and not any(char in "!@#$%^&*" for char in new_password):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"detail": "Пароль должен содержать хотя бы одну заглавную букву или символ"})

    email = confirm_token(token)
    if not email:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"detail": "Недействительная или просроченная ссылка"})

    user = await get_user_by_email(db, email)
    if not user:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": "Пользователь не найден"})

    user.set_password(new_password)


    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

# Маршрут для отображения формы регистрации
@app.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})
@app.post("/register")
async def register_user(
        first_name: str = Form(...),
        last_name: str = Form(...),
        email: str = Form(...),
        phone: str = Form(...),
        password: str = Form(...),
        confirm_password: str = Form(...),
        role: str = Form(...),
        db: AsyncSession = Depends(get_db)
):
    if password != confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пароли не совпадают")

    email_exists = await db.execute(select(Users).where(Users.email == email))
    email_exists = email_exists.scalars().first()
    if email_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email уже зарегистрирован")

    phone_exists = await db.execute(select(Users).where(Users.phone == phone))
    phone_exists = phone_exists.scalars().first()
    if phone_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Телефон уже зарегистрирован")

    hashed_password = bcrypt.hash(password)
    new_user = Users(
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        password_hash=hashed_password,
        user_type=role,
        is_active=False  # Пользователь не активен до подтверждения почты
    )
    db.add(new_user)
    await db.commit()

    token = generate_confirmation_token(email)
    confirm_url = f"http://127.0.0.1:8000/confirm/{token}"
    msg_text = f"Пройдите по следующей ссылке для подтверждения вашей почты: {confirm_url}"
    send_email.delay(email, msg_text)

    return {"message": "Перейдите в почту для завершения регистрации"}

@app.get("/confirm/{token}", response_class=HTMLResponse)
async def confirm_email(token: str, db: AsyncSession = Depends(get_db)):
    email = confirm_token(token)
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недействительная или просроченная ссылка")

    user = await db.execute(select(Users).where(Users.email == email))
    user = user.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь не найден")

    user.is_active = True
    db.add(user)
    await db.commit()

    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

# Маршрут для отображения покупателей
@app.get("/customers", response_class=HTMLResponse)
async def read_customers(request: Request, db: AsyncSession = Depends(get_db)):
    customers = await crud.get_customers(db)
    return templates.TemplateResponse("customers.html", {"request": request, "customers": customers})

# Маршрут для отображения продавцов
@app.get("/sellers", response_class=HTMLResponse)
async def read_sellers(request: Request, db: AsyncSession = Depends(get_db)):
    sellers = await crud.get_sellers(db)
    return templates.TemplateResponse("sellers.html", {"request": request, "sellers": sellers})

# Маршрут для отображения покупок
@app.get("/purchases", response_class=HTMLResponse)
async def read_purchases(request: Request, db: AsyncSession = Depends(get_db)):
    purchases = await crud.get_purchases(db)
    return templates.TemplateResponse("purchases.html", {"request": request, "purchases": purchases})



# Создание нового товара на складе
@app.post("/stock/", response_model=schemas.Stock)
async def create_stock(stock: schemas.StockCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_stock_item(db, stock)

# Получение информации о товаре на складе по ID
@app.get("/stock/{stock_id}", response_model=schemas.Stock)
async def read_stock(stock_id: int, db: AsyncSession = Depends(get_db)):
    db_stock = await crud.get_stock_item(db, stock_id)
    if db_stock is None:
        raise HTTPException(status_code=404, detail="Stock item not found")
    return db_stock

# Получение списка товаров на складе с поддержкой пагинации
@app.get("/stock/", response_model=list[schemas.Stock])
async def read_stock_items(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)):
    return await crud.get_stock_items(db, skip=skip, limit=limit)


# Получение информации о покупке по ID
@app.get("/purchases/{purchase_id}", response_model=schemas.Purchase)
async def read_purchase(purchase_id: int, db: AsyncSession = Depends(get_db)):
    db_purchase = await crud.get_purchase(db, purchase_id)
    if db_purchase is None:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return db_purchase

# Получение списка покупок с поддержкой пагинации
@app.get("/purchases/", response_model=list[schemas.Purchase])
async def read_purchases(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)):
    return await crud.get_purchases(db, skip=skip, limit=limit)

# Определяем endpoint для обслуживания favicon
@app.get("/favicon.ico")
async def favicon():
    return FileResponse("app/static/favicon.ico")


@app.get("/product/{product_id}", response_class=HTMLResponse)
async def product_page(request: Request, product_id: str, db: AsyncSession = Depends(get_db)):
    # Получаем информацию о продукте
    product = await db.execute(select(Product).where(Product.product_id == product_id))
    product = product.scalars().first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Получаем информацию о наличии продукта у продавцов
    stocks = await db.execute(
        select(Stock)
        .options(joinedload(Stock.seller))
        .where(Stock.product_id == product_id)
    )
    stocks = stocks.scalars().all()

    # Вычисляем скидку для каждого товара
    stock_list = []
    for stock in stocks:
        discount = round((1 - stock.discount_price / stock.price) * 100, 2) if stock.price else 0
        stock_list.append({
            "seller": f"{stock.seller.first_name} {stock.seller.last_name}",
            "size": stock.size,
            "price": stock.price,
            "discount_price": stock.discount_price,
            "discount": discount,
            "quantity": stock.quantity,
            "stock_id": stock.id
        })
    return templates.TemplateResponse("product.html", {
        "request": request,
        "product": product,
        "stocks": stock_list,
        "category": product.gender
    })



@app.get("/new-product", response_class=HTMLResponse)
async def new_product_form(request: Request, db: AsyncSession = Depends(get_db)):
    products = await get_products(db)
    product_list = [{"model_name": product.model_name, "image_side_url": product.image_side_url, "product_id": product.product_id, "price":product.price} for product in products]
    return templates.TemplateResponse("new_product.html", {"request": request, "products": product_list})




@app.post("/new-product", response_class=HTMLResponse)
async def add_new_product(
    request: Request,
    db: AsyncSession = Depends(get_db),
    model_name: str = Form(...),
    product_id: str = Form(...),
    sizes: List[str] = Form(...),
    quantities: List[str] = Form(...),
    price: float = Form(...),
    authorization: Optional[str] = Header(None)
):
    if not authorization or not authorization.startswith("Bearer "):
        return RedirectResponse(url="/login", status_code=307)

    token = authorization.split(" ")[1]

    try:
        payload = jwt_decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        user = await get_user_by_id(db, user_id)
        if not user or user.user_type != "seller":
            return RedirectResponse(url="/login", status_code=307)
    except ExpiredSignatureError:
        return RedirectResponse(url="/login", status_code=307)
    except Exception:
        return RedirectResponse(url="/login", status_code=307)

    product = await db.execute(select(Product).where(Product.product_id == product_id))
    product = product.scalars().first()
    if not product:
        return RedirectResponse(url="/create_product", status_code=307)

    if len(sizes) != len(quantities):
        return RedirectResponse(url="/new-product", status_code=400)

    for size, quantity in zip(sizes, quantities):
        new_stock = Stock(
            product_id=product.product_id,
            seller_id=user_id,
            size=float(size),
            quantity=int(quantity),
            price=product.price,  # Use the product price
            discount_price=price  # Initially no discount
        )
        db.add(new_stock)
    await db.commit()

    products = await get_products(db)
    product_list = [{"model_name": product.model_name} for product in products]
    return templates.TemplateResponse("new_product.html", {"request": request, "products": product_list, "message": "Product added successfully!"})

@app.get("/create_product", response_class=HTMLResponse)
async def create_product(request: Request):
    return templates.TemplateResponse("create_product.html", {"request": request})



@app.post("/create_product", response_class=HTMLResponse)
async def create_product_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    collection: str = Form(...),
    model_name: str = Form(...),
    recommended_price: float = Form(...),
    gender: str = Form(...),
    side_view: UploadFile = File(...),
    top_view: UploadFile = File(...),
    three_quarter_view: UploadFile = File(...),
    authorization: Optional[str] = Header(None)
):
    if not authorization or not authorization.startswith("Bearer "):
        return RedirectResponse(url="/login", status_code=307)

    token = authorization.split(" ")[1]
    try:
        payload = jwt_decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        user = await get_user_by_id(db, user_id)
        if not user or user.user_type != "seller":
            return RedirectResponse(url="/login", status_code=307)
    except ExpiredSignatureError:
        return RedirectResponse(url="/login", status_code=307)
    except Exception:
        return RedirectResponse(url="/login", status_code=307)

    # Save images
    side_view_url = await save_image(side_view, 'static/uploads')
    top_view_url = await save_image(top_view, 'static/uploads')
    three_quarter_view_url = await save_image(three_quarter_view, 'static/uploads')
    if gender.lower() == 'мужские':
        gender = 'M'
    elif gender.lower() == 'женские':
        gender = 'W'
    elif gender.lower() == 'унисекс':
            gender = 'U'
    elif gender.lower() == 'детские':
        gender = 'K'
    new_product = Product(
        brand=collection,
        model_name=model_name,
        price=str(recommended_price),
        discount=str(recommended_price),
        image_side_url=side_view_url,
        image_top_url=top_view_url,
        image_34_url=three_quarter_view_url,
        gender=gender
    )
    db.add(new_product)
    await db.commit()

    return templates.TemplateResponse("create_product.html", {"request": request, "message": "Product created successfully!"})

@app.post("/update-products", response_class=JSONResponse)
async def update_products(request: StockUpdateRequest, db: AsyncSession = Depends(get_db), authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "Missing or invalid Authorization header"})

    token = authorization.split(" ")[1]
    current_user_id = get_current_user_id(token)

    try:
        for product in request.products:
            print(f"Updating stock: {product.stock_id} with price: {product.price} and stock: {product.stock}")
            stmt = select(Stock).where(Stock.id == product.stock_id, Stock.seller_id == current_user_id)
            result = await db.execute(stmt)
            stock_entry = result.scalar_one_or_none()

            if stock_entry:
                stock_entry.discount_price = product.price
                stock_entry.quantity = product.stock
                db.add(stock_entry)
            else:
                print(f"No stock entry found for stock_id: {product.stock_id} and seller_id: {current_user_id}")

        await db.commit()
        return JSONResponse(content={"message": "Products updated successfully"})
    except Exception as e:
        await db.rollback()
        return JSONResponse(status_code=500, content={"detail": str(e)})



@app.get("/search-suggestions", response_class=JSONResponse)
async def search_suggestions(query: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Product)
        .join(Stock, Product.product_id == Stock.product_id)
        .where(Product.model_name.ilike(f"%{query.lower()}%"))
        .where(Stock.quantity > 0)
    )
    products = result.scalars().all()
    suggestions = [{"model_name": product.model_name} for product in products]
    return JSONResponse(content=suggestions)

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, query: str, db: AsyncSession = Depends(get_db)):
    subquery = (
        select(
            Stock.product_id,
            func.min(Stock.discount_price).label('min_discount_price')
        )
        .join(Product, Product.product_id == Stock.product_id)
        .where(Product.model_name.ilike(f"%{query.lower()}%"))
        .where(Stock.quantity > 0)
        .group_by(Stock.product_id)
        .subquery()
    )

    result = await db.execute(
        select(Product, Stock)
        .join(Stock, Product.product_id == Stock.product_id)
        .join(subquery, and_(
            Stock.product_id == subquery.c.product_id,
            Stock.discount_price == subquery.c.min_discount_price
        ))
    )
    products_and_stocks = result.unique().fetchall()

    # Создание списка продуктов с объединенными данными
    products = []
    for product, stock in products_and_stocks:
        products.append({
            "product_id": product.product_id,
            "model_name": product.model_name,
            "image_side_url": product.image_side_url,
            "image_top_url": product.image_top_url,
            "image_34_url": product.image_34_url,
            "price": stock.price,
            "discount_price": stock.discount_price
        })

    return templates.TemplateResponse("search.html", {"request": request, "products": products, "query": query})


@app.post("/cart", response_class=JSONResponse)
async def create_or_get_cart(request: Request, db: AsyncSession = Depends(get_db), user_id: Optional[int] = None,
                             session_id: Optional[str] = None):

    data = await request.json()
    user_id = data.get('user_id')
    session_id = data.get('session_id')

    if user_id:
        cart = await db.execute(select(Cart).where(Cart.user_id == user_id))
    else:
        cart = await db.execute(select(Cart).where(Cart.session_id == session_id))

    cart = cart.scalars().first()

    if not cart:
        new_cart = Cart(user_id=user_id, session_id=session_id)
        db.add(new_cart)
        await db.commit()
        cart = new_cart  # Ensure cart is assigned if it's newly created

    total_items = await get_cart_items_total_quantity_by_cart_id(cart.id, db)
    return JSONResponse(status_code=200, content={"cart_id": cart.id, "total_items": total_items})


@app.post("/cart/items", response_class=JSONResponse)
async def add_to_cart(request: AddToCartRequest, db: AsyncSession = Depends(get_db)):
    if request.user_id:
        cart = (await db.execute(select(Cart).where(Cart.user_id == request.user_id))).scalars().first()
    else:
        cart = (await db.execute(select(Cart).where(Cart.session_id == request.session_id))).scalars().first()

    if not cart:
        cart = Cart(user_id=request.user_id, session_id=request.session_id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart)

    total_items = await get_cart_items_total_quantity_by_cart_id(cart.id, db)

    # Check if CartItem with the same cart_id and stock_id exists
    existing_cart_item = (await db.execute(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.stock_id == request.stock_id)
    )).scalars().first()

    if existing_cart_item:
        # If exists, update quantity
        existing_cart_item.quantity += request.quantity
        total_items += request.quantity
    else:
        # If not exists, create a new CartItem
        cart_item = CartItem(cart_id=cart.id, stock_id=request.stock_id, quantity=request.quantity)
        db.add(cart_item)
        total_items += request.quantity

    await db.commit()

    return JSONResponse(status_code=200, content={"total_items": total_items})


@app.post("/cart/items/update", response_class=JSONResponse)
async def update_cart_item(request: UpdateCartRequest, db: AsyncSession = Depends(get_db)):

    cart_item = (await db.execute(select(CartItem).where(CartItem.id == request.cartitem_id))).scalars().first()
    if not cart_item:
        raise HTTPException(status_code=404, detail="CartItem not found")

    if request.quantity == 0:
        await db.delete(cart_item)
    else:
        cart_item.quantity = request.quantity
        db.add(cart_item)

    await db.commit()
    return JSONResponse(status_code=200, content={"detail": "Quantity updated"})


@app.post("/cart/items/details", response_class=JSONResponse)
async def get_cart_items(request: Request, user_id: Optional[int] = None, session_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    data = await request.json()
    user_id = data.get('user_id')
    session_id = data.get('session_id')

    if user_id:
        cart = (await db.execute(select(Cart).where(Cart.user_id == user_id))).scalars().first()
    else:
        cart = (await db.execute(select(Cart).where(Cart.session_id == session_id))).scalars().first()


    if not cart:
        return JSONResponse(status_code=200, content={"items": [], "total": 0})

    items = []
    total = 0
    cart_items = await get_cart_items_by_cart_id(cart.id, db)
    for item in cart_items:
        stock = (await db.execute(select(Stock).where(Stock.id == item.stock_id))).scalars().first()
        product = (await db.execute(select(Product).where(Product.product_id == stock.product_id))).scalars().first()

        item_data = {
            "cartitem_id": item.id,
            "product_name": product.model_name,
            "quantity": item.quantity,
            "price": stock.discount_price,
            "total_price": item.quantity * stock.discount_price,
            "image_url": product.image_side_url,
            "size": stock.size
        }
        items.append(item_data)
        total += item.quantity * stock.discount_price

    response_content = {"items": items, "total": total}
    response_content = decimal_to_float(response_content)

    return JSONResponse(status_code=200, content=response_content)


@app.get("/order", response_class=HTMLResponse)
async def create_product(request: Request):
    return templates.TemplateResponse("order.html", {"request": request})

@app.post("/create-checkout-session")
async def create_checkout_session(request: CreateCheckoutSessionRequest):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": request.currency,
                        "product_data": {
                            "name": "Total Order",
                        },
                        "unit_amount": request.amount,
                    },
                    "quantity": 1,
                },
            ],
            mode="payment",
            success_url="http://127.0.0.1:8000/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="http://127.0.0.1:8000/cancel?error={ERROR_CODE}",
            metadata={
                "user_id": request.user_id,
                "delivery_details": request.delivery_details.json()  # Сохраняем данные доставки в metadata
            }
        )
        return {"id": session.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/success", response_class=HTMLResponse)
async def payment_success(request: Request, session_id: str = Query(...), db: AsyncSession = Depends(get_db)):
    try:
        # Получение данных сессии Stripe
        stripe_session = stripe.checkout.Session.retrieve(session_id)
        user_id = stripe_session.metadata['user_id']

        # Получение payment_intent_id
        payment_intent_id = stripe_session.payment_intent

        # Извлечение данных доставки из metadata
        delivery_details = schemas.DeliveryDetailsCreate.parse_raw(stripe_session.metadata['delivery_details'])

        # Проверка и создание заказа
        await create_purchase_full(schemas.OrderDetails(
            user_id=user_id,
            payment_intent_id=payment_intent_id,
            delivery_details=delivery_details
        ), db)
        user_id = int(user_id)
        user = await get_user_by_id(db, int(user_id))
        email = user.email
        msg_text = f"Ваш заказ успешно офрмлен, пордробную информацию вы сможете найти в личном кабинете. \n В блажйшее время с вами свяжется оператор для уточнинеия деталей доставки.\n\n\n\n Всегда с вами Adik_Store!"
        send_email.delay(email, msg_text)
        return templates.TemplateResponse("success.html", {"request": request})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/cancel")
async def payment_cancel(error: str = Query(None)):
    # Логика для обработки отмены платежа
    return RedirectResponse(url=f"/order?error={error}")


@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/api/admin", response_class=JSONResponse)
async def api_admin(db: AsyncSession = Depends(get_db), authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.split(" ")[1]
    current_user_id = get_current_user_id(token)



    if current_user_id is None:
        raise HTTPException(status_code=403, detail="Unauthorized access")

    user = await db.execute(select(Users).where(Users.id == current_user_id))
    user = user.scalar_one_or_none()

    if user is None or user.user_type != 'admin':
        raise HTTPException(status_code=403, detail="Unauthorized access")

    all_products_query = await db.execute(
        select(Stock).options(joinedload(Stock.product), joinedload(Stock.seller))
    )
    all_products = all_products_query.scalars().all()

    new_products_query = await db.execute(
        select(Product).where(Product.is_active == False)
    )
    new_products = new_products_query.scalars().all()

    transactions_query = await db.execute(select(Purchase))
    transactions = transactions_query.scalars().all()
    response_data = {
        "all_products": [
            {
                "stock_id": stock.id,
                "model_name": stock.product.model_name,
                "seller_email": stock.seller.email,
                "price": stock.price,
                "discount_price": stock.discount_price,
                "quantity": stock.quantity,
            }
            for stock in all_products
        ],
        "new_products": [
            {
                "product_id": product.product_id,
                "model_name": product.model_name,
                "image_side_url": product.image_side_url,
                "image_top_url": product.image_top_url,
                "image_34_url": product.image_34_url,
                "price": product.price,
            }
            for product in new_products
        ],
        "transactions": [
            {
                "customer_id": purchase.customer_id,
                "seller_id": purchase.seller_id,
                "purchase_date": purchase.purchase_date,
                "status": purchase.status,
                "tracking_number": purchase.tracking_number,
            }
            for purchase in transactions
        ]
    }
    response_data = decimal_to_float(response_data)
    return JSONResponse(content=response_data)

@app.post("/update-stock", response_class=JSONResponse)
async def update_stock(update_data: ProductQuantityUpdateSchema, db: AsyncSession = Depends(get_db), authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.split(" ")[1]
    current_user_id = get_current_user_id(token)

    if current_user_id is None:
        raise HTTPException(status_code=403, detail="Unauthorized access")

    user = await db.execute(select(Users).where(Users.id == current_user_id))
    user = user.scalar_one_or_none()

    if user is None or user.user_type != 'admin':
        raise HTTPException(status_code=403, detail="Unauthorized access")

    stock = await db.execute(select(Stock).where(Stock.id == update_data.stock_id))
    stock = stock.scalar_one_or_none()
    if stock:
        stock.quantity = update_data.quantity
        db.add(stock)
        await db.commit()
        return JSONResponse(status_code=200, content={"detail": "Stock updated successfully"})
    else:
        raise HTTPException(status_code=404, detail="Stock not found")

@app.post("/activate-product", response_class=JSONResponse)
async def activate_product(data: ProductActivationSchema, db: AsyncSession = Depends(get_db), authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.split(" ")[1]
    current_user_id = get_current_user_id(token)

    if current_user_id is None:
        raise HTTPException(status_code=403, detail="Unauthorized access")

    user = await db.execute(select(Users).where(Users.id == current_user_id))
    user = user.scalar_one_or_none()

    if user is None or user.user_type != 'admin':
        raise HTTPException(status_code=403, detail="Unauthorized access")

    product = await db.execute(select(Product).where(Product.product_id == data.product_id))
    product = product.scalar_one_or_none()

    if data.is_active:
        product.is_active = data.is_active
        db.add(product)
        await db.commit()
    else:
        await db.delete(product)
        await db.commit()

    return JSONResponse(status_code=200, content={"detail": "Product activation status updated successfully"})
