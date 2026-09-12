from fastapi import APIRouter

from app.api.v1.routers import activity, auth, gameweeks, leagues, matches, notifications, profile, rankings, ws

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(leagues.router)
api_router.include_router(gameweeks.router)
api_router.include_router(matches.router)
api_router.include_router(rankings.router)
api_router.include_router(profile.router)
api_router.include_router(notifications.router)
api_router.include_router(activity.router)
api_router.include_router(ws.router)
