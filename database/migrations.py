"""Forward-only, idempotent SQLite migrations for persisted workflow links."""

from __future__ import annotations

from pathlib import Path

from database.connection import get_connection


WORKFLOW_RELATIONSHIP_MIGRATION = "001_workflow_relationships"

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
        if WORKFLOW_RELATIONSHIP_MIGRATION not in completed:
            connection.execute("BEGIN IMMEDIATE")
            _apply_workflow_relationships(connection)
            violations = connection.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RuntimeError(
                    "foreign key validation failed after workflow migration"
                )
            connection.execute(
                "INSERT INTO schema_migrations (migration_id) VALUES (?)",
                (WORKFLOW_RELATIONSHIP_MIGRATION,),
            )
            applied.append(WORKFLOW_RELATIONSHIP_MIGRATION)
        connection.commit()
        return applied
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


__all__ = [
    "WORKFLOW_RELATIONSHIP_MIGRATION",
    "WORKFLOW_COLUMNS",
    "WORKFLOW_INDEXES",
    "apply_migrations",
]
