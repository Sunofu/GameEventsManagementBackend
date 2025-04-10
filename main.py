import uvicorn
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import settings
from src.routers import router
from src.database import get_db, engine
from fastapi.middleware.cors import CORSMiddleware
from src.config import Base

from src.utils import start_scheduler

app = FastAPI()
app.include_router(
    router,
    prefix=settings.api.prefix,
)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await start_scheduler()


@app.get("/")
async def read_root(db: AsyncSession = Depends(get_db)):
    return {"message": "Асинхронная БД подключена!"}

origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://localhost:3001"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    uvicorn.run("main:app",
                host=settings.run.host,
                port=settings.run.port,
                reload=True,
                )
