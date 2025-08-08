from redis import Redis
from src.config import get_settings

settings = get_settings()
redis_conn = Redis(host=settings.redis_host, port=settings.redis_port, db=settings.redis_db)
