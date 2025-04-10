import pandas as pd
from fastapi import APIRouter
from fastapi.responses import FileResponse
from sqlalchemy import text
from src.database import async_session
import os
import logging
from sklearn.linear_model import LinearRegression

analytics_router = APIRouter()

REPORT_FILE = "advanced_analytics_report.xlsx"

logger = logging.getLogger(__name__)



@analytics_router.post("/report/create", summary="Создать продвинутый аналитический отчет")
async def create_report():
    try:
        logger.info("Начало создания продвинутого отчета")

        async with async_session() as session:
            logger.info("Сессия с базой данных установлена")

            # Получаем данные из базы данных
            user_query = await session.execute(text("SELECT * FROM users"))
            users = user_query.fetchall()

            subscriptions_query = await session.execute(text("SELECT * FROM subscriptions"))
            subscriptions = subscriptions_query.fetchall()

            games_query = await session.execute(text("SELECT id, title, developerid, genreid, rating, platforms, releasedate, description FROM game"))
            games = games_query.fetchall()

            events_query = await session.execute(text(""" 
                SELECT game_event.id, game_event.gameid, game_event.eventtypeid, game_event.starttime,
                       game_event.endtime, game_event.description, game_event.rewards, game_event.user_id,
                       event_type.title AS event_title
                FROM game_event
                JOIN event_type ON game_event.eventtypeid = event_type.id
            """))
            events = events_query.fetchall()

            # Проверка на наличие данных
            if not users or not subscriptions or not games or not events:
                logger.error("Один или несколько запросов вернули пустой результат.")
                return {"error": "Один или несколько запросов вернули пустой результат."}

            # Преобразуем данные в DataFrame для анализа
            users_df = pd.DataFrame(users, columns=["id", "username", "email", "password_hash", "registration_date", "last_enter_date", "isdeveloper"])
            subscriptions_df = pd.DataFrame(subscriptions, columns=["userid", "gameid"])

            games_columns = ["id", "title", "developerid", "genreid", "rating", "platforms", "releasedate", "description"]
            if len(games[0]) == len(games_columns):
                games_df = pd.DataFrame(games, columns=games_columns)
            else:
                logger.error(f"Ошибка данных игр: ожидаемые {len(games_columns)}, получено {len(games[0])}")
                return {"error": "Ошибка данных игр"}

            events_columns = [
                "id", "gameid", "eventtypeid", "starttime", "endtime",
                "description", "rewards", "user_id", "event_title"
            ]

            if len(events) > 0 and len(events[0]) != len(events_columns):
                logger.error(f"Ошибка данных событий: ожидаемые {len(events_columns)}, получено {len(events[0])}")
                return {"error": f"Ошибка данных событий: ожидаемые {len(events_columns)}, получено {len(events[0])}"}

            events_df = pd.DataFrame(events, columns=events_columns)

            if "id" in games_df.columns and "title" in games_df.columns:
                subscriptions_df = subscriptions_df.merge(games_df[["id", "title"]], left_on="gameid", right_on="id", how="left").rename(columns={"title": "game_title"})
                events_df = events_df.merge(games_df[["id", "title"]], left_on="gameid", right_on="id", how="left").rename(columns={"title": "game_title"})
            else:
                logger.error("Отсутствуют столбцы 'id' или 'title' в данных игр.")
                return {"error": "Ошибка при обработке данных игр"}

            # Анализ активности пользователей
            users_df["last_enter_date"] = pd.to_datetime(users_df["last_enter_date"])
            users_df["registration_date"] = pd.to_datetime(users_df["registration_date"])
            users_df["active_duration"] = (users_df["last_enter_date"] - users_df["registration_date"]).dt.days

            active_users = users_df[users_df["active_duration"] > 30]
            active_users_forecast = None
            if not active_users.empty:
                X = active_users[["active_duration"]].values
                y = active_users["active_duration"].shift(-1).fillna(active_users["active_duration"])
                model = LinearRegression()
                model.fit(X, y)
                active_users["predicted_active_duration"] = model.predict(X)
                active_users_forecast = active_users[["username", "predicted_active_duration"]]
                logger.info(f"Среднее предсказание: {active_users['predicted_active_duration'].mean()} дней")
            else:
                logger.warning("Нет активных пользователей для анализа.")

            game_subscriptions = subscriptions_df.groupby("gameid").size().reset_index(name="subscription_count")
            game_data = pd.merge(games_df, game_subscriptions, left_on="id", right_on="gameid", how="left").fillna(0)
            genre_subscriptions = game_data.groupby("genreid")[["subscription_count"]].sum().reset_index()

            game_data["predicted_subscription_count"] = 0.0
            X_subscriptions = game_data[["rating"]].values
            y_subscriptions = game_data["subscription_count"].shift(-1).fillna(game_data["subscription_count"])
            model_subscriptions = LinearRegression()
            model_subscriptions.fit(X_subscriptions, y_subscriptions)
            game_data["predicted_subscription_count"] = model_subscriptions.predict(X_subscriptions)

            event_participation = events_df.groupby(["eventtypeid", "event_title"]).size().reset_index(name="event_participation_count")
            event_participation["avg_event_participation"] = event_participation["event_participation_count"].mean()

            X_event = event_participation[["event_participation_count"]].values
            y_event = event_participation["event_participation_count"].shift(-1).fillna(event_participation["event_participation_count"])
            model_event = LinearRegression()
            model_event.fit(X_event, y_event)
            event_participation["predicted_event_participation"] = model_event.predict(X_event)

            # Создаем отчет
            with pd.ExcelWriter(REPORT_FILE, engine='openpyxl') as writer:
                if active_users_forecast is not None:
                    active_users_forecast.to_excel(writer, sheet_name="Активность пользователей", index=False)
                genre_subscriptions.to_excel(writer, sheet_name="Подписки по жанрам", index=False)
                game_data[["title", "predicted_subscription_count"]].to_excel(writer, sheet_name="Подписки на игры", index=False)
                event_participation.to_excel(writer, sheet_name="Вовлеченность событий", index=False)

                # Изменяем ширину колонок
                workbook = writer.book
                for sheet in workbook.sheetnames:
                    worksheet = workbook[sheet]
                    for column in worksheet.columns:
                        max_length = 0
                        column = [cell for cell in column]
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(cell.value)
                            except:
                                pass
                        adjusted_width = (max_length + 2)
                        worksheet.column_dimensions[column[0].column_letter].width = adjusted_width

            logger.info(f"Отчет сохранен в {REPORT_FILE}")
        return {"message": "Отчет успешно создан", "file": REPORT_FILE}

    except Exception as e:
        logger.error(f"Ошибка при создании отчета: {e}")
        return {"error": f"Не удалось создать отчет: {e}"}


@analytics_router.get("/report/download", summary="Скачать отчет")
async def download_report():
    if os.path.exists(REPORT_FILE):
        return FileResponse(REPORT_FILE, filename="advanced_analytics_report.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    return {"error": "Отчет не найден"}