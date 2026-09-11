from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from raven.core.config import get_settings


def get_engine():
    database_url = get_settings().database_url
    if not database_url:
        raise RuntimeError("RAVEN_DATABASE_URL is required for database access")
    return create_engine(database_url, pool_pre_ping=True)


def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
