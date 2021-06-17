from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_redis import FlaskRedis
from flask_caching import Cache
from flask_celery import Celery


db = SQLAlchemy(
    session_options={"autoflush": False, "autocommit": False})
report_db = SQLAlchemy(
    session_options={"autoflush": False, "autocommit": False})
migrate = Migrate(compare_type=True)
redis_store = FlaskRedis()
celery = Celery()
cache = Cache()

