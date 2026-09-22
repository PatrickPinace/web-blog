import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("TEST_DATABASE_URL", "sqlite://")

import pytest  # noqa: E402
from argon2 import PasswordHasher  # noqa: E402

from app import create_app  # noqa: E402
from app.extensions import db as _db  # noqa: E402
from app.models import User  # noqa: E402

ADMIN_PASSWORD = "correct-horse-battery-staple"


@pytest.fixture
def app():
    application = create_app("testing")
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def db(app):
    return _db


@pytest.fixture
def admin(db):
    user = User(
        username="admin",
        password_hash=PasswordHasher().hash(ADMIN_PASSWORD),
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client, admin):
    client.post(
        "/admin/login",
        data={"username": admin.username, "password": ADMIN_PASSWORD},
    )
    return client


@pytest.fixture
def demo_user(db):
    user = User(
        username="demo",
        password_hash=PasswordHasher().hash(ADMIN_PASSWORD),
        is_demo=True,
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def demo_client(client, demo_user):
    client.post(
        "/admin/login",
        data={"username": demo_user.username, "password": ADMIN_PASSWORD},
    )
    return client
