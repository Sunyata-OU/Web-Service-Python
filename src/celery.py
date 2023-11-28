from celery import Celery
from src.config import Settings


default = Celery("default", broker=Settings.REDIS_URL, backend=Settings.REDIS_URL)
