from fastapi import APIRouter, HTTPException

from backend.src.database import async_session
from sqlalchemy import text
from backend.src.utils import hash_password, verify_password, send_email, generate_verification_code, \
    save_confirmation_code, verify_confirmation_code
from backend.src.schemas import UserCreate, LoginUser, DeveloperCreate, Subscribe, VerifyCode, ResetPassword

users_router = APIRouter()
verification_code = 0

@users_router.post("/register")
async def register_user(user: UserCreate):
    async with async_session() as session:
        hashed_password = hash_password(user.password)
        query = text("INSERT INTO Users (username, email, password_hash, isdeveloper) VALUES (:username, :email, :password_hash, :isdeveloper)")
        await session.execute(query, {"username": user.UserName, "email": user.Email, "password_hash": hashed_password, "isdeveloper": user.isDeveloper})
        await session.commit()
        return {"message": "Пользователь успешно зарегистрирован."}

@users_router.post("/login")
async def login_user(request: LoginUser):
    async with async_session() as session:
        query = await session.execute(text("SELECT * FROM Users WHERE email = :email"), {"email": request.Email})
        user = query.fetchone()
        if not user or not verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=400, detail="Invalid email or password")
        await session.execute(text("select set_new_enter_date(:email)"), {"email": request.Email})
        await session.commit()
        return {"message": "Login successful"}

@users_router.post("/developer_register")
async def register_developer(developer: DeveloperCreate):
    async with async_session() as session:
        hashed_password = hash_password(developer.password)
        query = text("SELECT add_new_developer(:username, :email, :password_hash, :isdeveloper, :companyName, :country, :foundationDate, :Url);")
        await session.execute(query, {"username": developer.UserName, "email": developer.Email, "password_hash": hashed_password, "isdeveloper": developer.isDeveloper,
                                      "companyName": developer.companyName, "country": developer.country, "foundationDate": developer.foundationDate, "Url": developer.Url})
        await session.commit()
        return {"message": "Пользователь(разработчик) успешно зарегистрирован."}

@users_router.get("/get-user-info/{email}")
async def get_user_info(email: str):
    async with async_session() as session:
        query = await session.execute(text("SELECT * FROM users WHERE email = :email"), {"email": email})
        user = query.fetchone()
        if not user:
            raise HTTPException(status_code=400, detail="Пользователь не найден")
        return {
        "id": user.id,
        "email": user.email,
        "name": user.username,
        "isDeveloper": user.isdeveloper}

@users_router.post("/subscribe")
async def subscribe(sub: Subscribe):
    async  with async_session() as session:
        query = await session.execute(text("""
            INSERT INTO subscriptions(userid, gameid)
            VALUES
            (:userid, :gameid)        
        """), {"userid": sub.user_id, "gameid":sub.game_id})
        await session.commit()
        return {"message": "Подписка на игру совершена."}

@users_router.post("/unsubscribe")
async def subscribe(sub: Subscribe):
    async  with async_session() as session:
        query = await session.execute(text("""
            delete from subscriptions
            where userid = :userid and gameid = :gameid;      
        """), {"userid": sub.user_id, "gameid": sub.game_id})
        await session.commit()
        return {"message": "Подписка удалена."}

@users_router.get("/get-user-subscriptions/{user_id}")
async def get_user_subscriptions(user_id: int):
    async with async_session() as session:
        query = await session.execute(text("""
            select g.id, g.title, genre.name, g.rating, g.platforms, g.releasedate, g.description, d.name from subscriptions s
            join game g on s.gameid = g.id
            join genre on g.genreid = genre.id
            join developer d on g.developerid = d.id
            where s.userid = :userid;
        """), {"userid": user_id})
        rows = query.fetchall()
        if not rows:
            raise HTTPException(status_code=400, detail="No any subscribes")
        subs = [
            {
                "id": row[0],
                "title": row[1],
                "genre": row[2],
                "rating": row[3],
                "platform": row[4],
                "release_date": row[5],
                "description": row[6],
                "developer": row[7]
            }
            for row in rows
        ]
        return subs


async def get_game_subscriptions(game_id: int):
    async with async_session() as session:
        query = await session.execute(text("""
            select u.email from subscriptions s
            join users u on s.userid = u.id
            where s.gameid = :gameid;
                """), {"gameid": game_id})
        rows = query.fetchall()
        if not rows:
            raise HTTPException(status_code=400, detail="No any subscribes")
        emails = [row[0] for row in rows]
        return emails

@users_router.get("/send-verification-code/{email}")
async def send_verification_code(email: str):
    try:
        code = generate_verification_code()
        await save_confirmation_code(email, code)
        code_html = f"""
                <html>
                    <body>
                        <h1>Ваш код для подтверждения</h1>
                        <p>{code}</p>
                        <p>Не разглашайте его никому!</p>
                    </body>
                </html>
                """
        send_email(code_html, email)
    except:
        raise HTTPException(status_code=500, detail="Код не отправился!")
    return {"message": "Код отправлен!"}

@users_router.post("/verify-code")
async def verify_code(verify_data: VerifyCode):
    try:
        result = await verify_confirmation_code(verify_data.Email, verify_data.code)
    except:
        raise HTTPException(status_code=500, detail="что-то пошло не так!")
    return result


@users_router.get("/verify-email/{email}")
async def verify_email(email: str):
    async with async_session() as session:
        query = await session.execute(text("SELECT email FROM Users WHERE email = :email"), {"email": email})
        user = query.fetchone()
        if not user:
            raise HTTPException(status_code=400, detail="Invalid email")
        await session.commit()
        return {"message": "Correct email"}


@users_router.post("/reset-password")
async def reset_password(data: ResetPassword):
    async with async_session() as session:
        hashed_password = hash_password(data.newPassword)
        await session.execute(text("""
            UPDATE users 
            set password_hash = :password_hash
            where email = :email
        """), {"password_hash": hashed_password, "email": data.email})
        await session.commit()
        return {"message": "password is updated"}