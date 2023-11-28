from redis import Redis
from src.config import Settings

redis_conn = Redis(host=Settings.REDIS_HOST, port=Settings.REDIS_PORT, db=Settings.REDIS_DB)
