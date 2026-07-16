"""Read-only decision metrics for sales analytics."""

from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from database.connection import get_connection
from database.init_db import initialize_database
from services.customer_intelligence import customer_portfolio
from utils.constants import STAGES


def _count(connection, sql: str, parameters: tuple[Any, ...] = ()) -> int:
    return int(connection.execute(sql, parameters).fetchone()[0] or 0)


def _percentage(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100, 1) if denominator else 0.0


def dashboard_snapshot(
    db_path: str | Path | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Return one consistent set of decision-support metrics from SQLite."""
    today = today or date.today()
    initialize_database(db_path)
    portfolio = customer_portfolio(db_path, today=today)
    quality_counts = Counter(
        customer["lead_quality_band"] for customer in portfolio
    )
    connection = get_connection(db_path)
    try:
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
        inquiry_count = _count(connection, "SELECT COUNT(*) FROM inquiries")
        quoted_inquiry_count = _count(
            connection,
            "SELECT COUNT(DISTINCT inquiry_id) FROM quotations "
            "WHERE inquiry_id IS NOT NULL",
        )
        quoted_customer_count = _count(
            connection,
            "SELECT COUNT(DISTINCT customer_id) FROM quotations "
            "WHERE customer_id IS NOT NULL",
        )
        won_quoted_customer_count = _count(
            connection,
            "SELECT COUNT(DISTINCT q.customer_id) "
            "FROM quotations q JOIN customers c ON c.id = q.customer_id "
            "WHERE c.current_stage = 'Order Confirmed'",
        )
        metrics = {
            "total_customers": _count(connection, "SELECT COUNT(*) FROM customers"),
            "overdue_follow_ups": _count(
                connection,
                "SELECT COUNT(*) FROM follow_ups f "
                "JOIN customers c ON c.id = f.customer_id "
                "WHERE f.next_follow_up_date < ? "
                "AND c.current_stage NOT IN ('Order Confirmed', 'Lost')",
                (today.isoformat(),),
            ),
            "inquiry_to_quote_conversion": _percentage(
                quoted_inquiry_count,
                inquiry_count,
            ),
            "quotation_to_won_conversion": _percentage(
                won_quoted_customer_count,
                quoted_customer_count,
            ),
        }
        return {
            "metrics": metrics,
            "lead_quality": {
                band: quality_counts.get(band, 0)
                for band in (
                    "high_potential",
                    "qualified",
                    "developing",
                    "low_signal",
                )
            },
            "countries": [dict(row) for row in country_rows],
            "sources": [dict(row) for row in source_rows],
            "funnel": [
                {"stage": stage, "customers": stage_map.get(stage, 0)}
                for stage in STAGES
                if stage != "Lost"
            ],
            "demo_data_notice": bool(
                connection.execute(
                    "SELECT 1 FROM customers "
                    "WHERE notes = 'Entirely fictional portfolio demonstration record.' "
                    "LIMIT 1"
                ).fetchone()
            ),
        }
    finally:
        connection.close()
