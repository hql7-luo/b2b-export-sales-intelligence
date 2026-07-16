"""Read-only business aggregations for the dashboard."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from database.connection import get_connection
from database.init_db import initialize_database
from utils.constants import STAGES


def _count(connection, sql: str, parameters: tuple[Any, ...] = ()) -> int:
    return int(connection.execute(sql, parameters).fetchone()[0] or 0)


def dashboard_snapshot(db_path: str | Path | None = None, today: date | None = None) -> dict[str, Any]:
    """Return one consistent dashboard snapshot from SQLite."""
    today = today or date.today()
    initialize_database(db_path)
    connection = get_connection(db_path)
    try:
        grade_rows = connection.execute(
            "SELECT lead_grade AS label, COUNT(*) AS value FROM customers GROUP BY lead_grade"
        ).fetchall()
        country_rows = connection.execute(
            "SELECT COALESCE(NULLIF(country, ''), 'Unknown') AS label, COUNT(*) AS value "
            "FROM customers GROUP BY label ORDER BY value DESC"
        ).fetchall()
        source_rows = connection.execute(
            "SELECT COALESCE(NULLIF(lead_source, ''), 'Unknown') AS label, COUNT(*) AS value "
            "FROM customers GROUP BY label ORDER BY value DESC"
        ).fetchall()
        stage_rows = connection.execute(
            "SELECT current_stage AS label, COUNT(*) AS value FROM customers GROUP BY current_stage"
        ).fetchall()
        stage_map = {row["label"]: int(row["value"]) for row in stage_rows}
        follow_rows = connection.execute(
            """SELECT id, company_name, contact_name, country, current_stage,
                      lead_grade, next_follow_up_date
               FROM customers
               WHERE next_follow_up_date IS NOT NULL AND next_follow_up_date <= ?
               ORDER BY CASE lead_grade WHEN 'A' THEN 1 WHEN 'B' THEN 2 WHEN 'C' THEN 3 ELSE 4 END,
                        next_follow_up_date ASC
               LIMIT 12""",
            ((today + timedelta(days=7)).isoformat(),),
        ).fetchall()
        metrics = {
            "total_customers": _count(connection, "SELECT COUNT(*) FROM customers"),
            "new_inquiries": _count(
                connection,
                "SELECT COUNT(*) FROM inquiries WHERE inquiry_date >= ?",
                ((today - timedelta(days=30)).isoformat(),),
            ),
            "quoted_customers": _count(
                connection, "SELECT COUNT(DISTINCT customer_id) FROM quotations WHERE customer_id IS NOT NULL"
            ),
            "sample_customers": _count(
                connection, "SELECT COUNT(*) FROM customers WHERE current_stage = ?", ("Sample",)
            ),
            "won_customers": _count(
                connection, "SELECT COUNT(*) FROM customers WHERE current_stage = ?", ("Order Confirmed",)
            ),
            "expected_sales": float(
                connection.execute(
                    "SELECT COALESCE(SUM(estimated_purchase_volume), 0) FROM customers WHERE current_stage != ?",
                    ("Lost",),
                ).fetchone()[0]
                or 0
            ),
            "overdue_follow_ups": _count(
                connection,
                "SELECT COUNT(*) FROM customers WHERE next_follow_up_date < ? AND current_stage NOT IN (?, ?)",
                (today.isoformat(), "Order Confirmed", "Lost"),
            ),
        }
        return {
            "metrics": metrics,
            "grades": {grade: next((int(row["value"]) for row in grade_rows if row["label"] == grade), 0) for grade in "ABCD"},
            "countries": [dict(row) for row in country_rows],
            "sources": [dict(row) for row in source_rows],
            "funnel": [
                {"stage": stage, "customers": stage_map.get(stage, 0)}
                for stage in STAGES
                if stage != "Lost"
            ],
            "follow_ups": [
                {**dict(row), "overdue": str(row["next_follow_up_date"]) < today.isoformat()}
                for row in follow_rows
            ],
        }
    finally:
        connection.close()
