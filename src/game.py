from fastapi import APIRouter, HTTPException
from nose import with_setup

from backend.src.database import async_session
from sqlalchemy import text
from backend.src.schemas import GameCreate, GetDeveloperGames

game_router = APIRouter()


@game_router.post("/register")
async def register_game(game: GameCreate):
    async with (async_session() as session):
        # Проверка наличия игры с таким же названием
        existing_game_query = text("SELECT COUNT(*) FROM game WHERE title = :title")
        result = await session.execute(existing_game_query, {"title": game.title})
        (count,) = result.fetchone()
        if count > 0:
            raise HTTPException(status_code=400, detail="Игра с таким названием уже существует.")
        query = text("SELECT add_new_game(:title, :rating, :platforms, :releaseDate, :description, :genre, :user_id)")
        await session.execute(query, {"title": game.title, "rating": game.rating, "platforms": game.platforms,
                                      "releaseDate": game.releaseDate, "description": game.description, "genre": game.genre,
                                      "user_id": game.user_id})
        await session.commit()

        return {"message": "Игра успешно зарегистрирована."}

@game_router.post("/get-developer-games")
async def get_developer_games(game: GetDeveloperGames):
    async with async_session() as session:
        query = await session.execute(text("select get_games_by_user(:user_id)"), {"user_id": game.user_id})
        rows = query.fetchall()
        if not rows:
            raise HTTPException(status_code=400, detail="Пользователь не найден")

        games = [
            {
                "id": row._mapping["get_games_by_user"][0],
                "title": row._mapping["get_games_by_user"][1],
                "genre": row._mapping["get_games_by_user"][2],
                "rating": row._mapping["get_games_by_user"][3],
                "platform": row._mapping["get_games_by_user"][4],
                "release_date": row._mapping["get_games_by_user"][5],
                "description": row._mapping["get_games_by_user"][6],
            }
            for row in rows
        ]
        return games

@game_router.get("/get-all-games")
async def get_all_games():
    async with async_session() as session:
        query = await session.execute(text("""
                    SELECT g.id, g.title, genre.name, g.rating, g.platforms, g.releasedate, g.description, d.name
                    FROM game g
                    JOIN genre ON g.genreid = genre.id
                    JOIN developer d ON g.developerid = d.id
                """))
        rows = query.fetchall()
        if not rows:
            raise HTTPException(status_code=400, detail="Игры не найдены")
        games = [
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
        return games

@game_router.get("/get-all-genres")
async def get_all_genres():
    async with async_session() as session:
        query = await session.execute(text("""
                    select * from genre
                """))
        rows = query.fetchall()
        if not rows:
            raise HTTPException(status_code=400, detail="Игры не найдены")
        genres = [
            {
                "id": row[0],
                "name": row[1]
            }
            for row in rows
        ]
        return genres


