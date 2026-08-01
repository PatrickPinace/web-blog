from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address)

login_manager.login_view = "admin.login"
login_manager.login_message = "Zaloguj się, aby zobaczyć tę stronę."
login_manager.login_message_category = "info"
