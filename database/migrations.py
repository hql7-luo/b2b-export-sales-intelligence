"""Forward-only, idempotent SQLite migrations for persisted workflow links."""

from __future__ import annotations

import os
from math import isfinite
from pathlib import Path

from database.connection import get_connection


WORKFLOW_RELATIONSHIP_MIGRATION = "001_workflow_relationships"
SETTINGS_MIGRATION = "002_workspace_settings"

WORKFLOW_COLUMNS = {
    "inquiries": {
        "matched_product_id": (
            "INTEGER REFERENCES products(id) ON DELETE SET NULL"
        ),
    },
    "quotations": {
        "inquiry_id": "INTEGER REFERENCES inquiries(id) ON DELETE SET NULL",
        "product_id": "INTEGER REFERENCES products(id) ON DELETE SET NULL",
        "specification": "TEXT",
        "destination": "TEXT",
    },
    "follow_ups": {
        "inquiry_id": "INTEGER REFERENCES inquiries(id) ON DELETE SET NULL",
        "quotation_id": "INTEGER REFERENCES quotations(id) ON DELETE SET NULL",
        "customer_stage": "TEXT",
    },
    "activities": {
        "inquiry_id": "INTEGER REFERENCES inquiries(id) ON DELETE SET NULL",
        "quotation_id": "INTEGER REFERENCES quotations(id) ON DELETE SET NULL",
    },
}

WORKFLOW_INDEXES = {
    "idx_inquiries_workflow_product": (
        "inquiries",
        "matched_product_id",
    ),
    "idx_quotations_workflow_inquiry": ("quotations", "inquiry_id"),
    "idx_quotations_workflow_product": ("quotations", "product_id"),
    "idx_follow_ups_workflow_inquiry": ("follow_ups", "inquiry_id"),
    "idx_follow_ups_workflow_quotation": ("follow_ups", "quotation_id"),
    "idx_activities_workflow_inquiry": ("activities", "inquiry_id"),
    "idx_activities_workflow_quotation": ("activities", "quotation_id"),
}


def _table_columns(connection, table: str) -> set[str]:
    return {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }


def _apply_workflow_relationships(connection) -> None:
    for table, columns in WORKFLOW_COLUMNS.items():
        existing = _table_columns(connection, table)
        for column, definition in columns.items():
            if column not in existing:
                connection.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
                )
                existing.add(column)

    for index_name, (table, column) in WORKFLOW_INDEXES.items():
        connection.execute(
            f"CREATE INDEX IF NOT EXISTS {index_name} ON {table}({column})"
        )


def _default_exchange_rate() -> str:
    value = str(os.getenv("DEFAULT_EXCHANGE_RATE", "7.20")).strip()
    try:
        rate = float(value)
        return value if isfinite(rate) and rate > 0 else "7.20"
    except ValueError:
        return "7.20"


def _apply_workspace_settings(connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        "INSERT OR IGNORE INTO app_settings (setting_key, setting_value) "
        "VALUES (?, ?)",
        ("default_exchange_rate", _default_exchange_rate()),
    )


def apply_migrations(db_path: str | Path | None = None) -> list[str]:
    """Apply missing migrations and return the migration IDs applied now."""
    connection = get_connection(db_path)
    applied: list[str] = []
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_id TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        completed = {
            row["migration_id"]
            for row in connection.execute(
                "SELECT migration_id FROM schema_migrations"
            ).fetchall()
        }
        migrations = (
            (WORKFLOW_RELATIONSHIP_MIGRATION, _apply_workflow_relationships),
            (SETTINGS_MIGRATION, _apply_workspace_settings),
        )
        pending = [
            (migration_id, migration)
            for migration_id, migration in migrations
            if migration_id not in completed
        ]
        if pending:
            connection.execute("BEGIN IMMEDIATE")
            for migration_id, migration in pending:
                migration(connection)
                connection.execute(
                    "INSERT INTO schema_migrations (migration_id) VALUES (?)",
                    (migration_id,),
                )
                applied.append(migration_id)
            violations = connection.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RuntimeError(
                    "foreign key validation failed after database migration"
                )
        connection.commit()
        return applied
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


__all__ = [
    "WORKFLOW_RELATIONSHIP_MIGRATION",
    "SETTINGS_MIGRATION",
    "WORKFLOW_COLUMNS",
    "WORKFLOW_INDEXES",
    "apply_migrations",
]
