from fastapi import APIRouter

from app.api.v1.endpoints import aeo, agent_analytics, analytics, auth, brands, capture, export, insights

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(brands.router)
api_router.include_router(analytics.router)
api_router.include_router(insights.router)
api_router.include_router(aeo.router)
api_router.include_router(agent_analytics.router)
api_router.include_router(capture.router)
api_router.include_router(export.router)
