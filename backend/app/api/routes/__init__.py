from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.brands import router as brands_router
from app.api.routes.questions import router as questions_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.stats import router as stats_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.sessions import router as sessions_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["认证"])
api_router.include_router(brands_router, prefix="/brands", tags=["品牌管理"])
api_router.include_router(questions_router, prefix="/questions", tags=["问题管理"])
api_router.include_router(tasks_router, prefix="/tasks", tags=["任务管理"])
api_router.include_router(stats_router, prefix="/stats", tags=["统计"])
api_router.include_router(analysis_router, prefix="/analysis", tags=["分析"])
api_router.include_router(sessions_router, prefix="/sessions", tags=["会话管理"])
