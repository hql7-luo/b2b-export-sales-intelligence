"""Regression coverage for forward-only workflow relationship migrations."""

from __future__ import annotations

import sqlite3

import pytest

from database.connection import get_connection
from database.migrations import (
    SETTINGS_MIGRATION,
    WORKFLOW_RELATIONSHIP_MIGRATION,
    apply_migrations,
)


LEGACY_SCHEMA_SQL = """
CREATE TABLE customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL
);
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL
);
CREATE TABLE inquiries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    raw_text TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
);
CREATE TABLE quotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    product_name TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
);
CREATE TABLE follow_ups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);
CREATE TABLE activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    activity_type TEXT NOT NULL,
    description TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);
"""


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }


def test_workflow_relationship_migration_is_idempotent_and_preserves_legacy_data(
    tmp_path,
) -> None:
    db_path = tmp_path / "legacy.db"
    connection = get_connection(db_path)
    try:
        connection.executescript(LEGACY_SCHEMA_SQL)
        customer_id = connection.execute(
            "INSERT INTO customers (company_name) VALUES (?)",
            ("Fictional Legacy Trading",),
        ).lastrowid
        product_id = connection.execute(
            "INSERT INTO products (product_name) VALUES (?)",
            ("Fictional Legacy Notebook",),
        ).lastrowid
        inquiry_id = connection.execute(
            "INSERT INTO inquiries (customer_id, raw_text) VALUES (?, ?)",
            (customer_id, "Legacy fictional inquiry"),
        ).lastrowid
        connection.commit()
    finally:
        connection.close()

    first = apply_migrations(db_path)
    second = apply_migrations(db_path)

    assert first == [WORKFLOW_RELATIONSHIP_MIGRATION, SETTINGS_MIGRATION]
    assert second == []

    connection = get_connection(db_path)
    try:
        assert "matched_product_id" in _columns(connection, "inquiries")
        assert {"inquiry_id", "product_id", "specification", "destination"} <= _columns(
            connection, "quotations"
        )
        assert {"inquiry_id", "quotation_id"} <= _columns(
            connection, "follow_ups"
        )
        assert {"inquiry_id", "quotation_id"} <= _columns(
            connection, "activities"
        )
        legacy = connection.execute(
            "SELECT customer_id, raw_text FROM inquiries WHERE id = ?",
            (inquiry_id,),
        ).fetchone()
        assert dict(legacy) == {
            "customer_id": customer_id,
            "raw_text": "Legacy fictional inquiry",
        }
        assert connection.execute(
            "SELECT product_name FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()["product_name"] == "Fictional Legacy Notebook"
        assert connection.execute(
            "SELECT COUNT(*) AS count FROM schema_migrations"
        ).fetchone()["count"] == 2
        assert connection.execute(
            "SELECT setting_value FROM app_settings "
            "WHERE setting_key = 'default_exchange_rate'"
        ).fetchone()["setting_value"] == "7.20"
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        connection.close()


def test_workflow_relationship_migration_creates_each_index_once(tmp_path) -> None:
    db_path = tmp_path / "legacy_indexes.db"
    connection = get_connection(db_path)
    try:
        connection.executescript(LEGACY_SCHEMA_SQL)
        connection.commit()
    finally:
        connection.close()

    apply_migrations(db_path)
    apply_migrations(db_path)

    connection = get_connection(db_path)
    try:
        index_names = [
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'index' AND name LIKE 'idx_%_workflow_%'"
            ).fetchall()
        ]
    finally:
        connection.close()

    assert len(index_names) == len(set(index_names)) == 7


@pytest.mark.parametrize("configured_rate", ["nan", "inf", "-inf", "0", "invalid"])
def test_invalid_environment_exchange_rate_uses_safe_default(
    tmp_path, monkeypatch, configured_rate
) -> None:
    from database.init_db import initialize_database
    from database.repository import get_setting

    monkeypatch.setenv("DEFAULT_EXCHANGE_RATE", configured_rate)
    db_path = tmp_path / "invalid-rate.db"
    initialize_database(db_path)

    assert get_setting("default_exchange_rate", db_path=db_path) == "7.20"
