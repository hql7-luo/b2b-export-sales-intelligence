from __future__ import annotations

from datetime import date

from database.repository import create_customers_batch, get_customer
from services.excel_service import import_customer_file
from services.followup import follow_up_advice, follow_up_priority, generate_follow_up_message


def test_overdue_high_grade_lead_has_higher_priority() -> None:
    high = follow_up_priority("A", "2026-07-10", date(2026, 7, 16))
    low = follow_up_priority("C", "2026-07-15", date(2026, 7, 16))
    assert high > low


def test_stage_advice_is_actionable() -> None:
    advice = follow_up_advice("Quoted")
    assert "2" in advice
    assert "quotation" in advice.lower()


def test_generated_message_mentions_fictional_customer_need() -> None:
    message = generate_follow_up_message(
        contact_name="Demo Buyer",
        stage="Sample",
        product_interest="custom greeting cards",
    )
    assert "Demo Buyer" in message
    assert "custom greeting cards" in message
    assert len(message) < 800


def test_invalid_legacy_follow_up_date_does_not_crash_priority() -> None:
    assert follow_up_priority("B", "not-a-date", date(2026, 7, 16)) == 30


def test_minimal_csv_customer_can_generate_follow_up_message(db_path) -> None:
    rows = import_customer_file(
        b"Company Name\nMinimal Fictional Buyer\n",
        "customers.csv",
    )
    customer_id = create_customers_batch(rows, db_path=db_path)[0]
    customer = get_customer(customer_id, db_path=db_path)

    message = generate_follow_up_message(
        customer.get("contact_name"),
        customer.get("current_stage"),
        customer.get("product_interest"),
    )

    assert message.startswith("Hi there,")
    assert "your sourcing project" in message
