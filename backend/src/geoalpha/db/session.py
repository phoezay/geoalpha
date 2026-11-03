"""SQLite engine and session factory."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from geoalpha.db.models import Base

_engine: Engine | None = None
_factory: sessionmaker[Session] | None = None


def init_db(db_path: Path | str) -> Engine:
    """Create (or replace) the process-wide engine and ensure tables exist."""
    global _engine, _factory
    url = "sqlite://" if str(db_path) == ":memory:" else f"sqlite:///{db_path}"
    kwargs: dict[str, object] = {"connect_args": {"check_same_thread": False}}
    if url == "sqlite://":
        from sqlalchemy.pool import StaticPool

        kwargs["poolclass"] = StaticPool
    engine = create_engine(url, **kwargs)

    @event.listens_for(engine, "connect")
    def _pragmas(dbapi_conn, _record):  # type: ignore[no-untyped-def]
        # Let SQLAlchemy own transaction boundaries (see _begin_immediate).
        dbapi_conn.isolation_level = None
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA busy_timeout=10000")
        cur.close()

    @event.listens_for(engine, "begin")
    def _begin_immediate(conn):  # type: ignore[no-untyped-def]
        # Worker threads write concurrently. A deferred transaction that reads and then writes
        # fails at once with "database is locked" (SQLite will not wait on a read->write upgrade);
        # taking the write lock up front lets busy_timeout queue writers instead.
        conn.exec_driver_sql("BEGIN IMMEDIATE")

    Base.metadata.create_all(engine)
    _engine = engine
    _factory = sessionmaker(engine, expire_on_commit=False)
    return engine


@contextmanager
def session_scope() -> Iterator[Session]:
    if _factory is None:
        raise RuntimeError("init_db() has not been called")
    session = _factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
