import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()

    if not url:
        instance = BASE_DIR / "instance"
        instance.mkdir(exist_ok=True)
        db_path = (instance / "app.db").as_posix()
        return f"sqlite:///{db_path}"

    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TASKS_PER_PAGE = int(os.getenv("TASKS_PER_PAGE", "10"))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class DevConfig(Config):
    DEBUG = True


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret"


class ProdConfig(Config):
    DEBUG = False


CONFIGS = {
    "development": DevConfig,
    "testing": TestConfig,
    "production": ProdConfig,
}


def get_config():
    name = os.getenv("APP_ENV", "development")
    return CONFIGS.get(name, DevConfig)