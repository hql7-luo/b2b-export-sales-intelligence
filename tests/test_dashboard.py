from __future__ import annotations

from datetime import date

from database.seed_data import seed_demo_data
from services.dashboard import dashboard_snapshot


def test_dashboard_snapshot_aggregates_seed_data(db_path) -> None:
    seed_demo_data(db_path)
    snapshot = dashboard_snapshot(db_path, today=date(2026, 7, 16))

    assert snapshot["metrics"]["total_customers"] == 20
    assert sum(snapshot["lead_quality"].values()) == 20
    assert snapshot["metrics"]["inquiry_to_quote_conversion"] == 80.0
    assert snapshot["metrics"]["quotation_to_won_conversion"] == 12.5
    assert snapshot["metrics"]["overdue_follow_ups"] == 2
    assert sum(row["value"] for row in snapshot["countries"]) == 20
    assert set(snapshot["lead_quality"]) == {
        "high_potential",
        "qualified",
        "developing",
        "low_signal",
    }
    assert len(snapshot["funnel"]) == 8
    assert snapshot["demo_data_notice"] is True


def test_dashboard_empty_database_is_safe(db_path) -> None:
    snapshot = dashboard_snapshot(db_path, today=date(2026, 7, 16))

    assert snapshot["metrics"]["total_customers"] == 0
    assert snapshot["metrics"]["inquiry_to_quote_conversion"] == 0
    assert snapshot["metrics"]["quotation_to_won_conversion"] == 0
    assert sum(snapshot["lead_quality"].values()) == 0
