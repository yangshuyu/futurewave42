import datetime
import os

from celery.schedules import crontab

from config.default import Config


class DevelopmentConfig(Config):
    DEBUG = True

    SIGNATURE = True

    # SERVER
    SERVER_SCHEME = 'http'
    SERVER_DOMAIN = 'localhost:5000'

    CDN_DOMAIN = 'http://localhost:8081/files/'

    # SQL
    PSQL_USER = ''
    PSQL_PASSWORD = ''
    PSQL_PORT = '5432'
    PSQL_DATABASE = 'futurewave42'
    PSQL_HOST = 'localhost'

    SQLALCHEMY_DATABASE_URI = \
        "postgresql://{}:{}@{}:{}/{}".format(
            PSQL_USER, PSQL_PASSWORD, PSQL_HOST, PSQL_PORT, PSQL_DATABASE)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    # SQLALCHEMY_DATABASE_URI = 'postgresql://yangshuyu:yangshuyu@127.0.0.1:5432/dc_dev'

    # flask_cache
    CACHE_TYPE = 'redis'
    CACHE_REDIS_HOST = '127.0.0.1'
    CACHE_REDIS_PORT = '6379'
    CACHE_REDIS_DB = '3'

    SECRET_KEY = "futurewave"

    # redis
    REDIS_HOST = '127.0.0.1'
    REDIS_PORT = 6379
    REDIS_DB = 0

    BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 604800}
    CELERY_ENABLE_UTC = False
    CELERY_IMPORTS = (
    )
    CELERYBEAT_SCHEDULE = {
        # 'train_models': {
        #     'task': 'train_models',
        #     'schedule': crontab(hour=15, minute=59)
        # },
    }
    CELERY_BROKER_URL = 'redis://{}:6379/2'.format(REDIS_HOST)
    CELERY_RESULT_BACKEND = 'redis://{}:6379/2'.format(REDIS_HOST)
