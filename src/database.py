import os
from dotenv import load_dotenv
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from pydantic_settings import BaseSettings


load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the .env file")

Base = declarative_base()


class RunConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class ApiPrefix(BaseModel):
    prefix: str = "/api"


class Settings(BaseSettings):
    run: RunConfig = RunConfig()
    api: ApiPrefix = ApiPrefix()


settings = Settings()

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import MetaData, text
from config import DATABASE_URL
import asyncio


# Создаем асинхронный движок
engine = create_async_engine(DATABASE_URL, echo=True)
metadata = MetaData()

# Создаем фабрику асинхронной сессии
async_session = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,  # Передаем движок первым аргументом
    class_=AsyncSession
)


# Асинхронная функция для получения всех таблиц в схеме public
async def get_tables():
    async with async_session() as session:
        # Выполняем запрос на получение всех таблиц из схемы public
        result = await session.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        )
        tables = [row for row in result.scalars()]
        return tables


# Асинхронная функция для тестирования подключения и получения таблиц
async def test_database_connection():
    # Получаем список таблиц
    tables = await get_tables()
    print(f"Таблицы в базе данных: {tables}")


# Асинхронная зависимость для получения сессии
async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


if __name__ == "__main__":
    asyncio.run(test_database_connection())