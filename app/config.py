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
    BLOG_DESCRIPTION = os.environ.get(
        "BLOG_DESCRIPTION",
        "Autorski blog o projektowaniu, programowaniu i rozwijaniu serwisu.",
    )
    BLOG_AUTHOR = os.environ.get("BLOG_AUTHOR", "")
    BLOG_BASE_URL = os.environ.get("BLOG_BASE_URL", "http://localhost:5000")

    # Data w stopce ("Serwis działa od..."). Statyczna, ustawiana ręcznie —
    # bez hostingu z realnym uptime nie ma czego monitorować automatycznie.
    BLOG_LIVE_SINCE = os.environ.get("BLOG_LIVE_SINCE", "")

    # Linki w stopce. Puste wartości nie renderują odnośnika, żeby nie
    # zostawiać martwych adresów ani domyślnych danych poprzedniego autora.
    BLOG_EMAIL = os.environ.get("BLOG_EMAIL", "")
    BLOG_GITHUB_URL = os.environ.get("BLOG_GITHUB_URL", "")
    BLOG_REPOSITORY_URL = os.environ.get("BLOG_REPOSITORY_URL", "")
    BLOG_PORTFOLIO_URL = os.environ.get("BLOG_PORTFOLIO_URL", "")

    # Ręcznie utrzymywana kolejność części serii o budowie bloga. Slugi są
    # rozdzielone przecinkami; niepubliczne pozycje są pomijane przez zapytanie.
    BLOG_BUILD_SERIES_SLUGS = tuple(
        slug.strip()
        for slug in os.environ.get("BLOG_BUILD_SERIES_SLUGS", "").split(",")
        if slug.strip()
    )

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
