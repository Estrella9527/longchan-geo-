"""
Celery application configuration for async task execution.
"""
from celery import Celery
from app.core.config import settings

celery_app = Celery("longchan_geo")

celery_app.conf.update(
    broker_url=settings.CELERY_BROKER_URL,
    result_backend=settings.CELERY_RESULT_BACKEND,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
)

celery_app.autodiscover_tasks(
    ["app.tasks"],
    related_name=None,
)
# Force import to ensure registration
import app.tasks.execute_task  # noqa: F401
import app.tasks.browser_tasks  # noqa: F401
