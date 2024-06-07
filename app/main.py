import os
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.requests import Request

from . import models, schemas, crud
from .crud import get_popular_products, update_customer, update_seller, update_stock, get_mens_shoes, get_kids_shoes, \
    get_womens_shoes
from .database import engine, get_db, Base, AsyncSessionLocal

app = FastAPI()

# Получаем абсолютный путь к директории static
static_dir = os.path.join(os.path.dirname(__file__), "static")

# Монтируем директорию static
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Определяем endpoint для обслуживания favicon
@app.get("/favicon.ico")
async def favicon():
    return FileResponse("app/static/favicon.ico")


# Создание таблиц в базе данных
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Подключаем Jinja2 templates и статические файлы
templates = Jinja2Templates(directory="app/templates")

# Зависимость для получения сессии БД
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Маршрут для главной страницы
@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request, db: AsyncSession = Depends(get_db)):
    products = await get_popular_products(db)
    return templates.TemplateResponse("index.html", {"request": request, "products": products})

@app.get("/mens-shoes", include_in_schema=False)
async def redirect_to_mens_shoes():
    return RedirectResponse(url="/mens-shoes/1")
# Маршрут для страницы мужской обуви с поддержкой пагинации
@app.get("/mens-shoes/{page}", response_class=HTMLResponse, name="read_mens_shoes")
async def read_mens_shoes(request: Request, db: AsyncSession = Depends(get_db), page: int = 1):
    per_page = 24
    mens_shoes, total = await get_mens_shoes(db, page, per_page)
    total_pages = (total + per_page - 1) // per_page
    return templates.TemplateResponse("mens_shoes.html", {
        "request": request,
        "products": mens_shoes,
        "page": page,
        "total_pages": total_pages
    })

@app.get("/womens-shoes", include_in_schema=False)
async def redirect_to_womens_shoes():
    return RedirectResponse(url="/womens-shoes/1")
# Маршрут для страницы женской обуви с поддержкой пагинации
@app.get("/womens-shoes/{page}", response_class=HTMLResponse, name="read_womens_shoes")
async def read_womens_shoes(request: Request, db: AsyncSession = Depends(get_db), page: int = 1):
    per_page = 24
    mens_shoes, total = await get_womens_shoes(db, page, per_page)
    total_pages = (total + per_page - 1) // per_page
    return templates.TemplateResponse("womens_shoes.html", {
        "request": request,
        "products": mens_shoes,
        "page": page,
        "total_pages": total_pages
    })
@app.get("/kids-shoes", include_in_schema=False)
async def redirect_to_kids_shoes():
    return RedirectResponse(url="/kids-shoes/1")
# Маршрут для страницы детской обуви с поддержкой пагинации
@app.get("/kids-shoes/{page}", response_class=HTMLResponse, name="read_kids_shoes")
async def read_kids_shoes(request: Request, db: AsyncSession = Depends(get_db), page: int = 1):
    per_page = 24
    mens_shoes, total = await get_kids_shoes(db, page, per_page)
    total_pages = (total + per_page - 1) // per_page
    return templates.TemplateResponse("kids_shoes.html", {
        "request": request,
        "products": mens_shoes,
        "page": page,
        "total_pages": total_pages
    })

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

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("path/to/your/favicon.ico")

# Customers
@app.post("/customers/", response_model=schemas.Customer)
async def create_customer(customer: schemas.CustomerCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_customer(db, customer)

@app.get("/customers/{customer_id}", response_model=schemas.Customer)
async def read_customer(customer_id: int, db: AsyncSession = Depends(get_db)):
    db_customer = await crud.get_customer(db, customer_id)
    if db_customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return db_customer

@app.get("/customers/", response_model=list[schemas.Customer])
async def read_customers(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)):
    return await crud.get_customers(db, skip=skip, limit=limit)

# Sellers
@app.post("/sellers/", response_model=schemas.Seller)
async def create_seller(seller: schemas.SellerCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_seller(db, seller)

@app.get("/sellers/{seller_id}", response_model=schemas.Seller)
async def read_seller(seller_id: int, db: AsyncSession = Depends(get_db)):
    db_seller = await crud.get_seller(db, seller_id)
    if db_seller is None:
        raise HTTPException(status_code=404, detail="Seller not found")
    return db_seller

@app.get("/sellers/", response_model=list[schemas.Seller])
async def read_sellers(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)):
    return await crud.get_sellers(db, skip=skip, limit=limit)

# Stock
@app.post("/stock/", response_model=schemas.Stock)
async def create_stock(stock: schemas.StockCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_stock_item(db, stock)

@app.get("/stock/{stock_id}", response_model=schemas.Stock)
async def read_stock(stock_id: int, db: AsyncSession = Depends(get_db)):
    db_stock = await crud.get_stock_item(db, stock_id)
    if db_stock is None:
        raise HTTPException(status_code=404, detail="Stock item not found")
    return db_stock

@app.get("/stock/", response_model=list[schemas.Stock])
async def read_stock_items(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)):
    return await crud.get_stock_items(db, skip=skip, limit=limit)

# Purchases
@app.post("/purchases/", response_model=schemas.Purchase)
async def create_purchase(purchase: schemas.PurchaseCreate, db: AsyncSession = Depends(get_db)):
    await update_customer(db, purchase)
    await update_seller(db, purchase)
    await update_stock(db, purchase)
    return await crud.create_purchase(db, purchase)


@app.get("/purchases/{purchase_id}", response_model=schemas.Purchase)
async def read_purchase(purchase_id: int, db: AsyncSession = Depends(get_db)):
    db_purchase = await crud.get_purchase(db, purchase_id)
    if db_purchase is None:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return db_purchase

@app.get("/purchases/", response_model=list[schemas.Purchase])
async def read_purchases(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)):
    return await crud.get_purchases(db, skip=skip, limit=limit)


