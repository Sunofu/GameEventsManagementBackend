from fastapi import APIRouter, HTTPException

from backend.src.database import async_session
from sqlalchemy import text
from backend.src.schemas import GameEventCreate, GetDeveloperGames, DeleteEvent
from backend.src.users import get_game_subscriptions
from backend.src.utils import send_email

events_router = APIRouter()

@events_router.post("/register")
async def register_game(game_event: GameEventCreate):
    async with (async_session() as session):
        query = text("SELECT add_game_event(:game_id, :event_type_title, :start_time, :end_time, :description, :rewards, :user_id)")
        await session.execute(query, {"game_id": game_event.game_id, "event_type_title": game_event.event_type_title, "start_time": game_event.start_time,
                                      "end_time": game_event.end_time, "description": game_event.description, "rewards": game_event.rewards,
                                      "user_id": game_event.user_id})
        await session.commit()

        get_event_id_query = await session.execute(text("select id from game_event where description = :description"), {"description": game_event.description})
        row = get_event_id_query.fetchone()
        event_id = row[0]
        await session.commit()

        await session.execute(text("""
                    INSERT INTO Notification(userid, gameeventid, dispatch_time, message, type)
                    values
                    (:userid, :gameeventid, CURRENT_TIMESTAMP , 'New event!', 'new event')
                """), {"userid": game_event.user_id, "gameeventid": event_id})
        await session.commit()

        email_body = f"""
            <html>
                <body>
                    <h1>Новое событие!</h1>
                    <p>Выходит новое событие по игре</p>
                    <p>Дата начала: {game_event.start_time}</p>
                    <p>Дата окончания: {game_event.end_time}</p>
                    <p>Описание: {game_event.description}</p>
                    <p>Не пропустите!</p>
                </body>
            </html>
            """

        emails = await get_game_subscriptions(game_event.game_id)
        send_email(email_body, emails)

        return {"message": "Событие успешно зарегистрировано."}

@events_router.post("/get-user-events")
async def get_user_events(game_event: GetDeveloperGames):
    async with (async_session() as session):
        query = await session.execute(text("select get_events_by_user(:user_id)"), {"user_id": game_event.user_id})
        rows = query.fetchall()
        if not rows:
            raise HTTPException(status_code=400, detail="Пользователь не найден")

        events= [
            {
                "id": row._mapping["get_events_by_user"][0],
                "game_id": row._mapping["get_events_by_user"][1],
                "start_time": row._mapping["get_events_by_user"][2],
                "end_time": row._mapping["get_events_by_user"][3],
                "description": row._mapping["get_events_by_user"][4],
                "rewards": row._mapping["get_events_by_user"][5],
                "event_type_title": row._mapping["get_events_by_user"][6],
                "game_title": row._mapping["get_events_by_user"][7],
            }
            for row in rows
        ]
        return events

@events_router.get("/get-all-event-types")
async def get_all_event_types():
    async with async_session() as session:
        query = await session.execute(text("""
                       select*from event_type;
                   """))
        rows = query.fetchall()
        if not rows:
            raise HTTPException(status_code=400, detail="Типы событий не найдены")
        event_types = [
            {
                "id": row[0],
                "title": row[1],
                "description": row[2],
            }
            for row in rows
        ]
        return event_types

@events_router.get("/get-all-events")
async def get_all_events():
    async with async_session() as session:
        query = await session.execute(text("""
            select ge.id, g.id, ge.starttime, ge.endtime, ge.description, ge.rewards, et.title, g.title 
            from game_event ge
            join game g on ge.gameid = g.id
            join event_type et on ge.eventtypeid = et.id
                           """))
        rows = query.fetchall()
        if not rows:
            raise HTTPException(status_code=400, detail="События не найдены")
        events = [
            {
                "id": row[0],
                "game_id": row[1],
                "start_time": row[2],
                "end_time": row[3],
                "description": row[4],
                "rewards": row[5],
                "event_type_title": row[6],
                "game_title": row[7],
            }
            for row in rows
        ]
        return events

@events_router.post("/delete")
async def delete_event(event: DeleteEvent):
    async  with async_session() as session:
        await session.execute(text("""
            WITH deleted_game_event AS (
    DELETE FROM game_event
    WHERE id = :id
    RETURNING id
    )
    DELETE FROM notification
    WHERE gameeventid IN (SELECT id FROM deleted_game_event);     
        """), {"id": event.event_id})
        await session.commit()
        return {"message": "Событие удалено."}