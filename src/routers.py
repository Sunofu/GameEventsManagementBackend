from fastapi import APIRouter

from src.analytics import analytics_router
from src.report import report_router
from src.users import users_router
from src.game import game_router
from src.game_event import events_router

router = APIRouter()

router.include_router(users_router, prefix="/users", tags=["users"])
router.include_router(game_router, prefix="/game", tags=["game"])
router.include_router(events_router, prefix="/event", tags=["event"])
router.include_router(report_router, prefix="/report", tags=["report"])
router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])