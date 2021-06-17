from flask import Flask, jsonify
from flask_cors import CORS

from futurewave42 import BLUEPRINTS
from config import load_config
from futurewave42.ext import (db, migrate, redis_store, cache, report_db, celery)


def create_app(app_name='api', blueprints=None):
    app = Flask(app_name)
    config = load_config()
    app.config.from_object(config)

    if blueprints is None:
        blueprints = BLUEPRINTS
    blueprints_resister(app, blueprints)
    extensions_load(app)
    return app


def blueprints_resister(app, blueprints):
    for bp in blueprints:
        app.register_blueprint(bp)


def extensions_load(app):
    db.init_app(app)
    migrate.init_app(app, db)
    redis_store.init_app(app)
    celery.init_app(app)
    cache.init_app(app)

    CORS(app, resources={r"*": {"origins": "*", "expose_headers": "X-Total"}})

