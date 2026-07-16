"""Shared pytest fixtures."""

from pathlib import Path

import pytest

from database.init_db import initialize_database


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Return an isolated SQLite database for each test."""
    path = tmp_path / "test_export_sales.db"
    initialize_database(path)
    return path
