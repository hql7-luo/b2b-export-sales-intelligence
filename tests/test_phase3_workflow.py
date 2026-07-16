"""End-to-end persistence coverage for the Phase 3 core workflow."""

from __future__ import annotations

from datetime import date

from database.connection import get_connection
from database.repository import (
    create_customer,
    create_product,
    get_customer,
    get_inquiry,
    get_quotation,
    list_customer_timeline,
)
from services.inquiry_analyzer import analyze_inquiry_rules
from services.workflow import (
    build_follow_up_context,
    build_quotation_context,
    save_follow_up_for_quotation,
    save_inquiry_for_customer,
    save_quotation_for_inquiry,
)


INQUIRY_TEXT = (
    "Hello, we need 5,000 custom hardcover notebooks with recycled paper "
    "delivered to Hamburg, Germany."
)


def _product(db_path) -> int:
    return create_product(
        {
            "product_name": "Fictional Workflow Notebook",
            "category": "Stationery",
            "specification": "A5 recycled paper, hardcover",
            "unit_cost": 8.5,
            "moq": 500,
        },
        db_path=db_path,
    )


def _quotation_inputs() -> dict:
    return {
        "incoterm": "CIF",
        "unit_product_cost": 8.5,
        "packaging_cost": 1.2,
        "domestic_transportation_cost": 650,
        "export_handling_cost": 450,
        "international_freight": 2800,
        "insurance_cost": 120,
        "pricing_method": "gross_margin",
        "pricing_rate": 0.25,
        "exchange_rate": 7.2,
        "total_cost_cny": 56520,
        "unit_quote_usd": 2.0933,
        "total_quote_usd": 10466.67,
        "gross_profit_usd": 2616.67,
        "gross_margin": 0.25,
        "valid_until": "2026-08-15",
        "payment_terms": "30% deposit, 70% before shipment",
        "calculation_json": {"source": "phase3-test"},
    }


def test_new_customer_is_saved_and_linked_to_current_inquiry(db_path) -> None:
    product_id = _product(db_path)
    analysis = analyze_inquiry_rules(INQUIRY_TEXT)

    context = save_inquiry_for_customer(
        raw_text=INQUIRY_TEXT,
        analysis=analysis,
        analysis_mode="rule",
        matched_product_id=product_id,
        new_customer={
            "company_name": "Fictional Northstar Imports",
            "contact_name": "Morgan Example",
            "country": "Germany",
            "email": "morgan@northstar-imports.example.com",
            "product_interest": "Custom notebooks",
        },
        db_path=db_path,
    )

    inquiry = get_inquiry(context["inquiry_id"], db_path=db_path)
    customer = get_customer(context["customer_id"], db_path=db_path)
    assert context["customer_created"] is True
    assert customer["company_name"] == "Fictional Northstar Imports"
    assert inquiry["customer_id"] == customer["id"]
    assert inquiry["matched_product_id"] == product_id


def test_existing_customer_can_be_linked_to_saved_inquiry(db_path) -> None:
    customer_id = create_customer(
        {"company_name": "Fictional Existing Buyer"},
        db_path=db_path,
    )
    product_id = _product(db_path)

    context = save_inquiry_for_customer(
        raw_text=INQUIRY_TEXT,
        analysis=analyze_inquiry_rules(INQUIRY_TEXT),
        analysis_mode="rule",
        matched_product_id=product_id,
        existing_customer_id=customer_id,
        db_path=db_path,
    )

    assert context["customer_created"] is False
    assert context["customer_id"] == customer_id
    assert get_inquiry(context["inquiry_id"], db_path=db_path)["customer_id"] == customer_id


def test_inquiry_creates_quotation_with_all_inherited_context(db_path) -> None:
    product_id = _product(db_path)
    saved = save_inquiry_for_customer(
        raw_text=INQUIRY_TEXT,
        analysis=analyze_inquiry_rules(INQUIRY_TEXT),
        analysis_mode="rule",
        matched_product_id=product_id,
        new_customer={
            "company_name": "Fictional Quote Buyer",
            "country": "Germany",
        },
        db_path=db_path,
    )

    inherited = build_quotation_context(saved["inquiry_id"], db_path=db_path)
    quotation_id = save_quotation_for_inquiry(
        saved["inquiry_id"],
        _quotation_inputs(),
        db_path=db_path,
    )
    quotation = get_quotation(quotation_id, db_path=db_path)

    assert inherited == {
        "customer_id": saved["customer_id"],
        "customer_name": "Fictional Quote Buyer",
        "customer_stage": "New Lead",
        "country": "Germany",
        "inquiry_id": saved["inquiry_id"],
        "product_id": product_id,
        "product_name": "Fictional Workflow Notebook",
        "quantity": 5000,
        "quantity_text": "5,000 custom hardcover notebooks",
        "specification": "recycled paper, hardcover",
        "destination": "Hamburg, Germany",
        "unit_cost": 8.5,
        "moq": 500,
        "production_lead_time": None,
    }
    assert quotation["customer_id"] == saved["customer_id"]
    assert quotation["inquiry_id"] == saved["inquiry_id"]
    assert quotation["product_id"] == product_id
    assert quotation["product_name"] == inherited["product_name"]
    assert quotation["quantity"] == inherited["quantity"]
    assert quotation["specification"] == inherited["specification"]
    assert quotation["destination"] == inherited["destination"]
    assert get_customer(saved["customer_id"], db_path=db_path)["current_stage"] == "Quoted"


def test_quotation_creates_linked_follow_up_with_stage_and_recommended_date(
    db_path,
) -> None:
    product_id = _product(db_path)
    saved = save_inquiry_for_customer(
        raw_text=INQUIRY_TEXT,
        analysis=analyze_inquiry_rules(INQUIRY_TEXT),
        analysis_mode="rule",
        matched_product_id=product_id,
        new_customer={"company_name": "Fictional Follow-up Buyer"},
        db_path=db_path,
    )
    quotation_id = save_quotation_for_inquiry(
        saved["inquiry_id"],
        _quotation_inputs(),
        db_path=db_path,
    )

    inherited = build_follow_up_context(
        quotation_id,
        today=date(2026, 7, 16),
        db_path=db_path,
    )
    follow_up_id = save_follow_up_for_quotation(
        quotation_id,
        {
            "follow_up_date": "2026-07-16",
            "communication_type": "Email",
            "content": "Sent the fictional CIF quotation for review.",
            "outcome": "Awaiting buyer feedback",
            "next_follow_up_date": inherited["recommended_follow_up_date"],
            "priority": "High",
        },
        db_path=db_path,
    )

    connection = get_connection(db_path)
    try:
        follow_up = dict(
            connection.execute(
                "SELECT * FROM follow_ups WHERE id = ?",
                (follow_up_id,),
            ).fetchone()
        )
    finally:
        connection.close()

    assert inherited["customer_id"] == saved["customer_id"]
    assert inherited["inquiry_id"] == saved["inquiry_id"]
    assert inherited["quotation_id"] == quotation_id
    assert inherited["customer_stage"] == "Quoted"
    assert inherited["recommended_follow_up_date"] == "2026-07-18"
    assert follow_up["customer_id"] == saved["customer_id"]
    assert follow_up["inquiry_id"] == saved["inquiry_id"]
    assert follow_up["quotation_id"] == quotation_id
    assert follow_up["customer_stage"] == "Quoted"


def test_foreign_keys_and_customer_timeline_cover_the_complete_workflow(
    db_path,
) -> None:
    product_id = _product(db_path)
    saved = save_inquiry_for_customer(
        raw_text=INQUIRY_TEXT,
        analysis=analyze_inquiry_rules(INQUIRY_TEXT),
        analysis_mode="rule",
        matched_product_id=product_id,
        new_customer={"company_name": "Fictional Timeline Buyer"},
        db_path=db_path,
    )
    quotation_id = save_quotation_for_inquiry(
        saved["inquiry_id"],
        _quotation_inputs(),
        db_path=db_path,
    )
    save_follow_up_for_quotation(
        quotation_id,
        {
            "follow_up_date": "2026-07-16",
            "communication_type": "Email",
            "content": "Scheduled quotation follow-up.",
            "next_follow_up_date": "2026-07-18",
            "priority": "High",
        },
        db_path=db_path,
    )

    timeline = list_customer_timeline(saved["customer_id"], db_path=db_path)
    event_types = [event["activity_type"] for event in timeline]
    assert event_types == [
        "customer_saved",
        "inquiry_created",
        "product_matched",
        "quotation_created",
        "follow_up_scheduled",
    ]
    assert all(event["customer_id"] == saved["customer_id"] for event in timeline)
    assert timeline[-1]["inquiry_id"] == saved["inquiry_id"]
    assert timeline[-1]["quotation_id"] == quotation_id

    connection = get_connection(db_path)
    try:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        connection.close()
