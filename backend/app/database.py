from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from ml.config import PROJECT_ROOT


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    database_url: str = Field(default="",
        validation_alias=AliasChoices("ADMIN_DATABASE_URL", "DATABASE_URL")
    )
    database_url_file: str = Field(default="", validation_alias=AliasChoices("ADMIN_DATABASE_URL_FILE", "DATABASE_URL_FILE"))


class Base(DeclarativeBase):
    pass


def database_url() -> str:
    settings = DatabaseSettings()
    if settings.database_url_file:
        try:
            with open(settings.database_url_file, encoding="utf-8") as stream:
                value = stream.read().strip()
        except OSError as error:
            raise RuntimeError("The database URL secret file could not be read") from error
    else:
        value = settings.database_url.strip()
    if not value:
        raise RuntimeError("A database URL or database URL secret file is required")
    return value


def create_database_engine(url: str | None = None):
    resolved = url or database_url()
    is_sqlite = resolved.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {"connect_timeout": 5}
    engine_options: dict[str, object] = {
        "connect_args": connect_args,
        "pool_pre_ping": True,
    }
    if not is_sqlite:
        engine_options["pool_timeout"] = 5
    engine = create_engine(resolved, **engine_options)
    if is_sqlite:
        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


engine = create_database_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
