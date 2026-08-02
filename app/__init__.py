import os
from datetime import UTC, datetime

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

    from app import (
        auth,  # noqa: F401 — rejestruje login_manager.user_loader
        models,  # noqa: F401 — rejestruje tabele w metadata przed migracją
    )
    from app.admin import admin_bp
    from app.public import public_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    from app import cli, errors, security
    from app.utils import uploads
    from app.utils.content import read_time
    from app.utils.embeds import render_embeds

    cli.register(app)
    errors.register(app)
    uploads.configure(app)
    if not app.config.get("TESTING"):
        security.register(app)

    # Zamienia placeholdery embedów na iframe'y dopiero przy wyświetlaniu —
    # w bazie nigdy nie leży osadzony kod ramki (app/utils/embeds.py).
    app.jinja_env.filters["render_embeds"] = render_embeds
    app.jinja_env.filters["read_time"] = read_time

    @app.context_processor
    def inject_globals():
        # Rok do stopki — liczony przy renderowaniu, żeby nie zamarzł na
        # roku wdrożenia (instancja potrafi żyć miesiącami).
        return {"current_year": datetime.now(UTC).year}

    return app
