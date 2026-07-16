"""SQLite connection helpers used by the application and tests."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "export_sales_intelligence.db"


def resolve_database_path(
    db_path: str | Path | None = None,
) -> Path:
    """Resolve an explicit path or the optional workspace environment override."""
    if db_path is not None:
        return Path(db_path)
    configured = str(os.getenv("DATABASE_PATH") or "").strip()
    if not configured:
        return DEFAULT_DB_PATH
    path = Path(configured).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Create a configured SQLite connection.

    ``db_path`` is injectable so tests and scripts never need to modify the
    application database.
    """
    path = resolve_database_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    is_default_database = path.resolve() == DEFAULT_DB_PATH.resolve()
    if is_default_database:
        path.parent.chmod(0o700)
    connection = sqlite3.connect(path, timeout=10)
    if is_default_database:
        path.chmod(0o600)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def database_connection(
    db_path: str | Path | None = None,
) -> Iterator[sqlite3.Connection]:
    """Yield a connection and always close it after the operation."""
    connection = get_connection(db_path)
    try:
        yield connection
    finally:
        connection.close()
