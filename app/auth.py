from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from fastapi_login import LoginManager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.hash import bcrypt
from app.models import Customer, Seller
from app.database import get_db

SECRET = "your-secret-key"
manager = LoginManager(SECRET, token_url='/login', use_cookie=True)


@manager.user_loader
async def load_user(email: str, db: AsyncSession = Depends(get_db)):
    query = select(Customer).filter(Customer.email == email)
    result = await db.execute(query)
    customer = result.scalar_one_or_none()
    if customer:
        return customer

    query = select(Seller).filter(Seller.email == email)
    result = await db.execute(query)
    seller = result.scalar_one_or_none()
    if seller:
        return seller



