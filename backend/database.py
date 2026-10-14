from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

from .config import settings


engine_kwargs = {"echo": False, "future": True, "pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_recycle"] = 3600

engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = scoped_session(
    sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    with engine.begin() as conn:
        if "email" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(200)"))
        if "two_factor_enabled" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN two_factor_enabled BOOLEAN DEFAULT 1 NOT NULL"))
        if "failed_login_attempts" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0 NOT NULL"))
        if "lockout_until" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN lockout_until DATETIME"))
