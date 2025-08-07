from celery import Celery

from src.config import get_settings

settings = get_settings()
default = Celery("default", broker=settings.redis_url, backend=settings.redis_url)
