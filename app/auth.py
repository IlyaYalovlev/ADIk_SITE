from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from fastapi_login import LoginManager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jwt import decode as jwt_decode, ExpiredSignatureError, InvalidTokenError
from app import crud
from app.database import get_db
from datetime import datetime, timedelta
import jwt
from itsdangerous import URLSafeTimedSerializer
from app.models import Users
from config import SECRET



# Конфигурация для JWT
SECRET_KEY = SECRET
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
serializer = URLSafeTimedSerializer(SECRET_KEY)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user_id(token: str) -> int:
    try:
        payload = jwt_decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload.get("sub"))
    except (ExpiredSignatureError, InvalidTokenError, KeyError):
        return None


def generate_confirmation_token(email: str):
    return serializer.dumps(email, salt='email-confirm-salt')

def confirm_token(token: str, expiration=3600):
    try:
        email = serializer.loads(token, salt='email-confirm-salt', max_age=expiration)
    except:
        return False
    return email