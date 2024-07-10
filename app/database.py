from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import MetaData
from contextlib import asynccontextmanager
from config import DATABASE_URL as DATABASE_URL1

# Получаем URL базы данных из конфигурационного файла
DATABASE_URL = DATABASE_URL1

# Создаем метаданные
metadata = MetaData()

# Создаем базовый класс для моделей, используя созданные метаданные
Base = declarative_base(metadata=metadata)

# Создаем асинхронный движок базы данных с параметрами пула соединений
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
)

# Создаем фабрику сессий для асинхронного использования с базой данных
AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession
)

# Контекстный менеджер для работы с сессиями базы данных
@asynccontextmanager
async def get_db_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# Асинхронный генератор для получения сессии базы данных
async def get_db():
    async with get_db_session() as session:
        yield session
