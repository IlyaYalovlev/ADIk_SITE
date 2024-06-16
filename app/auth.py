from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from fastapi_login import LoginManager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.hash import bcrypt

from app import crud
from app.database import get_db
from datetime import datetime, timedelta
import jwt

from app.models import Users

SECRET = "your-secret-key"
manager = LoginManager(SECRET, token_url='/login', use_cookie=True)

# Конфигурация для JWT
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(manager)):
    credentials_exception = HTTPException(
        status_code=HTTPException.status_code,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.JWTError:
        raise credentials_exception
    async with get_db() as db:
        user = await crud.get_user_by_id(db, user_id)
        if user is None:
            raise credentials_exception
        return user