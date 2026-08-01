import os

from flask import Flask

from app.config import CONFIG_BY_NAME
from app.extensions import csrf, db, limiter, login_manager, migrate


def create_app(config_name=None):
    app = Flask(__name__)

    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(CONFIG_BY_NAME[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)

    from app import auth  # noqa: F401 — rejestruje login_manager.user_loader
    from app.admin import admin_bp
    from app.public import public_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    from app import cli

    cli.register(app)

    return app
