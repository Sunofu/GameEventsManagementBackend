import os
from dotenv import load_dotenv
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from pydantic_settings import BaseSettings


load_dotenv()

print("Loaded DATABASE_URL:", os.getenv("DATABASE_URL"))

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