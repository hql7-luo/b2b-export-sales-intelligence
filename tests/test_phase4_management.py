from __future__ import annotations

from datetime import date

import pytest

from database.repository import (
    create_customer,
    create_follow_up,
    create_inquiry,
    create_product,
    create_quotation,
    get_setting,
    list_products_with_match_counts,
    set_setting,
)
from database.seed_data import reset_demo_data, seed_demo_data
from services.customer_intelligence import (
    assess_customer,
    customer_portfolio,
)
from services.followup import build_follow_up_task_queue
from services.workflow import (
    build_quotation_context,
    save_quotation_for_inquiry,
    set_inquiry_matched_product,
)


def _analysis(quantity: str = "1,000") -> dict:
    return {
        "extracted_fields": {
            "product": "Fictional notebook",
            "specification": "A5 recycled paper",
            "quantity": quantity,
            "destination": "Toronto, Canada",
        },
        "confirmed_info": ["product", "specification", "quantity", "destination"],
        "missing_info": [],
        "risks": [],
        "next_questions": [],
        "completeness_score": 100,
        "suggested_reply": "Thank you for your fictional inquiry.",
    }


def test_data_completeness_and_commercial_lead_quality_are_independent() -> None:
    customer = {
        "company_name": "Complete but Early Fictional Buyer",
        "contact_name": "Demo Contact",
        "country": "Canada",
        "email": "demo@complete-early.example.com",
        "phone": "+00 555 0188",
        "lead_source": "Website",
        "product_interest": "Notebook",
        "import_frequency": "Annual",
        "estimated_purchase_volume": 0,
        "last_contact_date": "2026-07-15",
        "next_follow_up_date": "2026-07-20",
        "current_stage": "New Lead",
    }

    assessment = assess_customer(customer, today=date(2026, 7, 16))

    assert assessment["data_completeness"]["score"] >= 90
    assert assessment["lead_quality"]["band"] in {"developing", "low_signal"}
    assert assessment["lead_quality"]["score"] < 55


def test_customer_portfolio_uses_persisted_commercial_evidence(db_path) -> None:
    customer_id = create_customer(
        {
            "company_name": "Commercial Evidence Fictional Buyer",
            "country": "Canada",
            "lead_source": "Referral",
            "product_interest": "Notebooks",
            "import_frequency": "Monthly",
            "estimated_purchase_volume": 42000,
            "current_stage": "Quoted",
            "next_follow_up_date": "2026-07-18",
        },
        db_path=db_path,
    )
    product_id = create_product(
        {
            "product_name": "Commercial Evidence Fictional Notebook",
            "specification": "A5",
        },
        db_path=db_path,
    )
    inquiry_id = create_inquiry(
        customer_id=customer_id,
        raw_text="Fictional request for 1,000 A5 notebooks.",
        analysis=_analysis(),
        analysis_mode="rule",
        matched_product_id=product_id,
        db_path=db_path,
    )
    create_quotation(
        {
            "customer_id": customer_id,
            "inquiry_id": inquiry_id,
            "product_id": product_id,
            "product_name": "Commercial Evidence Fictional Notebook",
            "incoterm": "FOB",
            "quantity": 1000,
        },
        db_path=db_path,
    )

    row = customer_portfolio(db_path, today=date(2026, 7, 16))[0]

    assert row["inquiry_count"] == 1
    assert row["quotation_count"] == 1
    assert row["matched_product_count"] == 1
    assert row["lead_quality_band"] == "high_potential"
    assert row["data_completeness_score"] != row["lead_quality_score"]


def test_follow_up_task_queue_prioritizes_due_buckets_and_keeps_links() -> None:
    records = [
        {
            "id": 3,
            "customer_id": 3,
            "company_name": "Future Fictional Buyer",
            "customer_stage": "Quoted",
            "priority": "High",
            "next_follow_up_date": "2026-07-20",
            "inquiry_id": 103,
            "quotation_id": 203,
        },
        {
            "id": 1,
            "customer_id": 1,
            "company_name": "Overdue Fictional Buyer",
            "customer_stage": "Negotiation",
            "priority": "Medium",
            "next_follow_up_date": "2026-07-14",
            "inquiry_id": 101,
            "quotation_id": 201,
        },
        {
            "id": 2,
            "customer_id": 2,
            "company_name": "Today Fictional Buyer",
            "customer_stage": "Sample",
            "priority": "Low",
            "next_follow_up_date": "2026-07-16",
            "inquiry_id": 102,
            "quotation_id": 202,
        },
    ]

    queue = build_follow_up_task_queue(records, today=date(2026, 7, 16))

    assert [row["due_bucket"] for row in queue] == [
        "overdue",
        "today",
        "upcoming",
    ]
    assert queue[0]["inquiry_id"] == 101
    assert queue[0]["quotation_id"] == 201


def test_follow_up_task_queue_supports_business_filters() -> None:
    records = [
        {
            "id": 1,
            "customer_id": 1,
            "company_name": "Alpha Fictional Buyer",
            "customer_stage": "Quoted",
            "priority": "High",
            "next_follow_up_date": "2026-07-15",
            "inquiry_id": 101,
            "quotation_id": 201,
        },
        {
            "id": 2,
            "customer_id": 2,
            "company_name": "Beta Fictional Buyer",
            "customer_stage": "Sample",
            "priority": "Medium",
            "next_follow_up_date": "2026-07-19",
            "inquiry_id": 102,
            "quotation_id": 202,
        },
    ]

    queue = build_follow_up_task_queue(
        records,
        today=date(2026, 7, 16),
        customer_id=2,
        stage="Sample",
        priority="Medium",
        date_filter="next_7_days",
    )

    assert [row["id"] for row in queue] == [2]


def test_default_exchange_rate_is_persisted_and_editable(db_path) -> None:
    assert float(get_setting("default_exchange_rate", db_path=db_path)) > 0

    set_setting("default_exchange_rate", "7.35", db_path=db_path)

    assert get_setting("default_exchange_rate", db_path=db_path) == "7.35"


@pytest.mark.parametrize("invalid_rate", ["nan", "inf", "-inf", "0", "invalid"])
def test_invalid_exchange_rate_does_not_replace_persisted_setting(db_path, invalid_rate) -> None:
    previous = get_setting("default_exchange_rate", db_path=db_path)

    with pytest.raises(ValueError, match="finite and greater than zero"):
        set_setting("default_exchange_rate", invalid_rate, db_path=db_path)

    assert get_setting("default_exchange_rate", db_path=db_path) == previous


def test_product_match_counts_are_derived_from_inquiries(db_path) -> None:
    customer_id = create_customer(
        {"company_name": "Match Count Fictional Buyer"},
        db_path=db_path,
    )
    product_id = create_product(
        {"product_name": "Match Count Fictional Product"},
        db_path=db_path,
    )
    create_inquiry(
        customer_id=customer_id,
        raw_text="Fictional matched request",
        analysis=_analysis(),
        analysis_mode="rule",
        matched_product_id=product_id,
        db_path=db_path,
    )

    row = list_products_with_match_counts(db_path=db_path)[0]

    assert row["matched_inquiry_count"] == 1


def test_follow_up_repository_preserves_task_relationships(db_path) -> None:
    customer_id = create_customer(
        {"company_name": "Task Link Fictional Buyer"},
        db_path=db_path,
    )
    follow_up_id = create_follow_up(
        {
            "customer_id": customer_id,
            "inquiry_id": None,
            "quotation_id": None,
            "follow_up_date": "2026-07-16",
            "content": "Fictional follow-up record.",
            "next_follow_up_date": "2026-07-18",
            "priority": "High",
        },
        db_path=db_path,
    )

    assert follow_up_id > 0


def test_demo_seed_creates_traceable_workflow_relationships(db_path) -> None:
    seed_demo_data(db_path)

    from database.connection import get_connection

    connection = get_connection(db_path)
    try:
        linked_inquiries = connection.execute(
            "SELECT COUNT(*) FROM inquiries "
            "WHERE customer_id IS NOT NULL AND matched_product_id IS NOT NULL"
        ).fetchone()[0]
        linked_quotes = connection.execute(
            "SELECT COUNT(*) FROM quotations "
            "WHERE customer_id IS NOT NULL AND inquiry_id IS NOT NULL "
            "AND product_id IS NOT NULL"
        ).fetchone()[0]
        linked_follow_ups = connection.execute(
            "SELECT COUNT(*) FROM follow_ups "
            "WHERE customer_id IS NOT NULL AND inquiry_id IS NOT NULL"
        ).fetchone()[0]
        timeline_events = connection.execute(
            "SELECT COUNT(*) FROM activities "
            "WHERE activity_type IN ('inquiry_created', 'product_matched', "
            "'quotation_created', 'follow_up_scheduled')"
        ).fetchone()[0]
    finally:
        connection.close()

    assert linked_inquiries == 10
    assert linked_quotes == 8
    assert linked_follow_ups == 10
    assert timeline_events >= 38


def test_reset_demo_data_preserves_non_demo_user_records(db_path) -> None:
    seed_demo_data(db_path)
    user_customer_id = create_customer(
        {
            "company_name": "User Owned Fictional Test Record",
            "email": "user-owned@example.com",
        },
        db_path=db_path,
    )
    user_product_id = create_product(
        {"product_name": "User Owned Test Product"},
        db_path=db_path,
    )

    counts = reset_demo_data(db_path)

    from database.repository import get_customer, get_product

    assert counts["customers"] == 21
    assert get_customer(user_customer_id, db_path=db_path) is not None
    assert get_product(user_product_id, db_path=db_path) is not None


def test_unmatched_inquiry_can_prepare_draft_but_requires_verification_to_save(
    db_path,
) -> None:
    customer_id = create_customer(
        {"company_name": "Unmatched Quote Fictional Buyer"},
        db_path=db_path,
    )
    inquiry_id = create_inquiry(
        customer_id=customer_id,
        raw_text="Fictional request for 1,000 unusual printed items.",
        analysis=_analysis(),
        analysis_mode="rule",
        matched_product_id=None,
        db_path=db_path,
    )

    context = build_quotation_context(inquiry_id, db_path=db_path)

    assert context["product_id"] is None
    assert context["product_name"] == "Fictional notebook"
    try:
        save_quotation_for_inquiry(
            inquiry_id,
            {
                "incoterm": "FOB",
                "unit_product_cost": 10,
                "exchange_rate": 7.2,
            },
            db_path=db_path,
        )
    except ValueError as exc:
        assert str(exc) == "unmatched product must be verified before saving"
    else:
        raise AssertionError("unmatched quotation must require explicit verification")

    quotation_id = save_quotation_for_inquiry(
        inquiry_id,
        {
            "incoterm": "FOB",
            "unit_product_cost": 10,
            "exchange_rate": 7.2,
        },
        product_verified=True,
        db_path=db_path,
    )

    assert quotation_id > 0


def test_manual_product_selection_persists_on_the_inquiry(db_path) -> None:
    customer_id = create_customer(
        {"company_name": "Manual Match Fictional Buyer"},
        db_path=db_path,
    )
    product_id = create_product(
        {"product_name": "Manually Selected Fictional Product"},
        db_path=db_path,
    )
    inquiry_id = create_inquiry(
        customer_id=customer_id,
        raw_text="Fictional manual-match request for 1,000 units.",
        analysis=_analysis(),
        analysis_mode="rule",
        matched_product_id=None,
        db_path=db_path,
    )

    set_inquiry_matched_product(inquiry_id, product_id, db_path=db_path)
    context = build_quotation_context(inquiry_id, db_path=db_path)

    assert context["product_id"] == product_id
    assert context["product_name"] == "Manually Selected Fictional Product"
