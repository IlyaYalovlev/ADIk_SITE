import os
from typing import Optional
from fastapi import HTTPException, status
from jwt.exceptions import ExpiredSignatureError
from fastapi import Header
from jwt import decode as jwt_decode
from fastapi import FastAPI, Depends, HTTPException, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from . import schemas, crud
from .auth import get_current_user, create_access_token
from .crud import get_popular_products, update_customer, update_seller, update_stock, get_mens_shoes, get_womens_shoes, get_kids_shoes, get_user_by_id, get_user_by_email
from .database import get_db
from .schemas import UserDetails

app = FastAPI()

# Получаем абсолютный путь к директории static
static_dir = os.path.join(os.path.dirname(__file__), "static")

# Монтируем директорию static
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Подключаем Jinja2 templates
templates = Jinja2Templates(directory="app/templates")

# Конфигурация для fastapi-login
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Маршрут для отображения формы авторизации
@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Обработка данных авторизации
@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, email)
    if user.check_password(password):
        access_token = create_access_token(data={"sub": str(user.id)})
        return JSONResponse(status_code=200, content={"access_token": access_token})
    else:
        return JSONResponse(status_code=401, content={"error": "Неверные учетные данные"})

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
        return JSONResponse(content={"id": user.id, "first_name": user.first_name, "last_name": user.last_name})
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="JWT token has expired")

# Обновление маршрута для главной страницы
@app.get("/", response_class=HTMLResponse)
@app.post("/", response_class=HTMLResponse)
async def read_index(request: Request, authorization: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    user = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        user = await get_current_user(token)
    products = await get_popular_products(db)
    return templates.TemplateResponse("index.html", {"request": request, "products": products})

# Обновление маршрута для профиля пользователя
@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request, user=Depends(get_current_user)):
    if user.user_type == 'customer':
        return templates.TemplateResponse("profile_customer.html", {"request": request, "user": user})
    elif user.user_type == 'seller':
        return templates.TemplateResponse("profile_seller.html", {"request": request, "user": user})

# Маршрут для мужской обуви
@app.get("/mens-shoes", response_class=HTMLResponse)
@app.get("/mens-shoes/{page}", response_class=HTMLResponse)
async def mens_shoes(request: Request, page: int = 1, db: AsyncSession = Depends(get_db)):
    per_page = 24 # количество товаров на одной странице
    products, total = await get_mens_shoes(db, page, per_page)
    total_pages = (total + per_page - 1) // per_page # вычисляем общее количество страниц
    return templates.TemplateResponse("mens_shoes.html", {
        "request": request,
        "products": products,
        "page": page,
        "total_pages": total_pages
    })

# Маршрут для женской обуви
@app.get("/womens-shoes", response_class=HTMLResponse)
@app.get("/womens-shoes/{page}", response_class=HTMLResponse)
async def womens_shoes(request: Request, page: int = 1, db: AsyncSession = Depends(get_db)):
    per_page = 24 # количество товаров на одной странице
    products, total = await get_womens_shoes(db, page, per_page)
    total_pages = (total + per_page - 1) // per_page # вычисляем общее количество страниц
    return templates.TemplateResponse("womens_shoes.html", {
        "request": request,
        "products": products,
        "page": page,
        "total_pages": total_pages
    })

# Маршрут для детской обуви
@app.get("/kids-shoes", response_class=HTMLResponse)
@app.get("/kids-shoes/{page}", response_class=HTMLResponse)
async def kids_shoes(request: Request, page: int = 1, db: AsyncSession = Depends(get_db)):
    per_page = 24 # количество товаров на одной странице
    products, total = await get_kids_shoes(db, page, per_page)
    total_pages = (total + per_page - 1) // per_page # вычисляем общее количество страниц
    return templates.TemplateResponse("kids_shoes.html", {
        "request": request,
        "products": products,
        "page": page,
        "total_pages": total_pages
    })

# Маршрут для отображения формы восстановления пароля
@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_form(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})

# Маршрут для отображения формы регистрации
@app.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

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

# Создание новой покупки
@app.post("/purchases/", response_model=schemas.Purchase)
async def create_purchase(purchase: schemas.PurchaseCreate, db: AsyncSession = Depends(get_db)):
    await update_customer(db, purchase)
    await update_seller(db, purchase)
    await update_stock(db, purchase)
    return await crud.create_purchase(db, purchase)

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