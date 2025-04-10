import random
from email.mime.text import MIMEText
from operator import truediv

from src.database import async_session
from passlib.context import CryptContext
import os
from dotenv import load_dotenv
import smtplib
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
from sqlalchemy import text

pwd_context = CryptContext(schemes=['bcrypt'], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(input_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(input_password, hashed_password)

load_dotenv()

login = os.getenv("login")
password = os.getenv("password")

def send_email(html, emails):
    message = MIMEText(html, "html")
    obj_msg = smtplib.SMTP(host="smtp.gmail.com", port=587)
    obj_msg.starttls()
    try:
        obj_msg.login(user=login, password=password)
        obj_msg.sendmail(login, emails, message.as_string())
    except:
        print("error")

SQL_QUERY = """ WITH deleted_game_event AS ( DELETE FROM game_event WHERE endtime < CURRENT_TIMESTAMP RETURNING id ) DELETE FROM notification WHERE gameeventid IN (SELECT id FROM deleted_game_event); """
async def delete_old_events():
    async with (async_session() as session):
        await session.execute(text(SQL_QUERY))
        await session.commit()

async def start_scheduler():
    scheduler = AsyncIOScheduler()
    loop = asyncio.get_event_loop()
    scheduler.add_job(lambda: loop.create_task(delete_old_events()), "interval", minutes=30)
    scheduler.start()


def generate_verification_code():
    return f"{random.randint(1000, 9999)}"

async def save_confirmation_code(email, code):
    async with async_session() as session:
        is_email_in_db = await verify_email_in_code(email)
        if is_email_in_db:
            await session.execute(
                text("""
                    UPDATE verification_code
                    SET code = :code
                    WHERE email = :email
                """),
                {"code": code, "email": email}
            )
        else:
            await session.execute(
                text("""
                    INSERT INTO verification_code (email, code)
                    VALUES (:email, :code)
                """),
                {"email": email, "code": code}
            )
        await session.commit()



async def verify_confirmation_code(email, code):
    async with async_session() as session:
        response = await session.execute(text("""
            select code from verification_code 
            where email = :email
        """), {"email": email})
        db_code = response.fetchone()
    return db_code[0] == code


async def verify_email_in_code(email):
    async with async_session() as session:
        query = await session.execute(
            text("SELECT email FROM verification_code WHERE email = :email"),
            {"email": email}
        )
        user = query.fetchone()
        return user is not None



