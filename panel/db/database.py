import os
import configparser

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

cfg = configparser.ConfigParser()
cfg.read("panel.cfg")


def _setting(option: str, env_var: str, default: str) -> str:
    """cfg-файл задаёт дефолты, переменные окружения (docker-compose) их перекрывают."""
    return os.environ.get(env_var, cfg.get("database", option, fallback=default))


DB_HOST = _setting("host", "DB_HOST", "db")
DB_PORT = _setting("port", "DB_PORT", "5432")
DB_NAME = _setting("name", "DB_NAME", "gaikovert")
DB_USER = _setting("user", "DB_USER", "gaikovert")
DB_PASSWORD = _setting("password", "DB_PASSWORD", "gaikovert")

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
