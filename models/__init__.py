from __future__ import annotations

import os
from typing import AsyncGenerator

from sqlalchemy import MetaData, text, event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy import create_engine  

# ---- ENV / settings ----------------------------------------------------------
ENV = os.environ.get("ENVIRONMENT", os.environ.get("ENVIRONTMENT"))
if ENV != "prod":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

from settings import (
    DB_USER,
    DB_PASS,
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DEFAULT_SCHEMA,
)

# ---- Database URLs -----------------------------------------------------------
DATABASE_URL_ASYNC = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
DATABASE_URL_SYNC  = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"  # >>> NEW

# ---- SQLAlchemy base with default schema ------------------------------------
metadata = MetaData(schema=DEFAULT_SCHEMA)
Base = declarative_base(metadata=metadata)

# ---- Async Engine & Sessions -------------------------------------------------
engine = create_async_engine(
    DATABASE_URL_ASYNC,
    pool_size=10,
    max_overflow=5,
    pool_recycle=1800,
    pool_timeout=30,
    echo=False,
    future=True,
)

async_session = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
    class_=AsyncSession,
)

scheduler_session = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
    class_=AsyncSession,
)

# >>> NEW: Sync Engine & SessionLocal (untuk worker sinkron / background task FastAPI)
sync_engine = create_engine(
    DATABASE_URL_SYNC,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False)

@event.listens_for(engine.sync_engine, "connect")
def _set_search_path_async(dbapi_conn, _):
    try:
        cur = dbapi_conn.cursor()
        cur.execute(f'SET search_path TO "{DEFAULT_SCHEMA}", public')
        cur.close()
    except Exception:
        pass

@event.listens_for(sync_engine, "connect")
def _set_search_path_sync(dbapi_conn, _):
    try:
        cur = dbapi_conn.cursor()
        cur.execute(f'SET search_path TO "{DEFAULT_SCHEMA}", public')
        cur.close()
    except Exception:
        pass

# ---- Helpers startup ---------------------------------------------------------
async def ensure_schema_and_extensions() -> None:
    async with engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{DEFAULT_SCHEMA}";'))
        for ext in ('"uuid-ossp"', "pg_trgm", "vector"):
            try:
                await conn.execute(text(f"CREATE EXTENSION IF NOT EXISTS {ext};"))
            except Exception:
                pass

async def create_all() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ---- FastAPI dependency (async) ---------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
        except SQLAlchemyError:
            await session.rollback()
            raise

async def ensure_schema_and_extensions() -> None:
    async with engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{DEFAULT_SCHEMA}";'))

        for ext in ('"uuid-ossp"', "pg_trgm", "vector"):
            try:
                await conn.execute(text(f"CREATE EXTENSION IF NOT EXISTS {ext};"))
            except Exception:
                pass
        try:
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_rag_docs_embedding_hnsw
                ON rag_docs USING hnsw (embedding);
            """))
        except Exception:
            pass
        
from .Job import Job
from .RagDoc import RagDoc
from .Result import Result
from .Upload import Upload

__all__ = [
    "Base",
    "engine",
    "async_session",
    "scheduler_session",
    "get_db",
    "ensure_schema_and_extensions",
    "create_all",
    "sync_engine",
    "SessionLocal",
    # models:
    "Job",
    "RagDoc",
    "Result",
    "Upload",
]
