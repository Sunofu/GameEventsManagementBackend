from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import MetaData, text
from src.config import DATABASE_URL
import asyncio

engine = create_async_engine(DATABASE_URL, echo=True)
metadata = MetaData()

async_session = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)

async def get_tables():
    async with async_session() as session:
        result = await session.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        )
        tables = [row for row in result.scalars()]
        return tables

async def test_database_connection():
    tables = await get_tables()
    print(f"Таблицы в базе данных: {tables}")

async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session

if __name__ == "__main__":
    asyncio.run(test_database_connection())
