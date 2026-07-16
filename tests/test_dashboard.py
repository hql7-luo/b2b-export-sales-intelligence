from __future__ import annotations

from datetime import date

from database.seed_data import seed_demo_data
from services.dashboard import dashboard_snapshot


def test_dashboard_snapshot_aggregates_seed_data(db_path) -> None:
    seed_demo_data(db_path)
    snapshot = dashboard_snapshot(db_path, today=date(2026, 7, 16))

    assert snapshot["metrics"]["total_customers"] == 20
    assert sum(snapshot["grades"].values()) == 20
    assert snapshot["metrics"]["quoted_customers"] == 8
    assert snapshot["metrics"]["expected_sales"] > 0
    assert sum(row["value"] for row in snapshot["countries"]) == 20
    assert all(snapshot["grades"][grade] > 0 for grade in "ABCD")
    assert len(snapshot["funnel"]) == 8


def test_dashboard_empty_database_is_safe(db_path) -> None:
    snapshot = dashboard_snapshot(db_path, today=date(2026, 7, 16))

    assert snapshot["metrics"]["total_customers"] == 0
    assert snapshot["metrics"]["expected_sales"] == 0
    assert snapshot["follow_ups"] == []
