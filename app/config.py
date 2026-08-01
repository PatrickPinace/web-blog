import os


class Config:
    SECRET_KEY = os.environ["SECRET_KEY"]
    SQLALCHEMY_DATABASE_URI = os.environ["DATABASE_URL"]
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", 5)) * 1024 * 1024

    CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL")
    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")

    # Domeny, z których wolno wstawić obrazek przez URL. Serwer nigdy nie
    # pobiera tych zasobów — adres trafia wprost do `img src`.
    ALLOWED_IMAGE_HOSTS = tuple(
        h.strip()
        for h in os.environ.get("ALLOWED_IMAGE_HOSTS", "res.cloudinary.com").split(",")
        if h.strip()
    )

    BLOG_TITLE = os.environ.get("BLOG_TITLE", "Blog")
    BLOG_DESCRIPTION = os.environ.get("BLOG_DESCRIPTION", "")
    BLOG_AUTHOR = os.environ.get("BLOG_AUTHOR", "")
    BLOG_BASE_URL = os.environ.get("BLOG_BASE_URL", "http://localhost:5000")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class DevConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProdConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://blog:blog@localhost:5432/blog_test",
    )
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


CONFIG_BY_NAME = {
    "development": DevConfig,
    "production": ProdConfig,
    "testing": TestConfig,
}
