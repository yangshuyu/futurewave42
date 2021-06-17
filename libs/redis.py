import redis
from flask import current_app, has_app_context

from config import load_config

if has_app_context():
    host = current_app.config.get("REDIS_HOST")
    port = current_app.config.get("REDIS_PORT")
    db = current_app.config.get("REDIS_DB")

else:
    config = load_config()
    host = config.REDIS_HOST
    port = config.REDIS_PORT
    db = config.REDIS_DB


pool = redis.ConnectionPool(host=host, port=port, db=db, decode_responses=True)
redis_client = redis.Redis(connection_pool=pool)

