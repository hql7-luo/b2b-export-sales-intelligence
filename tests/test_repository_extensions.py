from __future__ import annotations

from database.repository import (
    create_customer,
    create_follow_up,
    create_inquiry,
    create_product,
    delete_product,
    get_product,
    list_follow_ups,
    list_inquiries,
    list_products,
    update_product,
)
from services.inquiry_analyzer import analyze_inquiry_rules


def test_inquiry_analysis_can_be_persisted(db_path) -> None:
    analysis = analyze_inquiry_rules("We need 2,000 custom gift boxes to Germany.")
    inquiry_id = create_inquiry(
        customer_id=None,
        raw_text="We need 2,000 custom gift boxes to Germany.",
        analysis=analysis,
        analysis_mode="rule",
        db_path=db_path,
    )

    rows = list_inquiries(db_path=db_path)
    assert rows[0]["id"] == inquiry_id
    assert rows[0]["product"] == "Custom gift box"
    assert isinstance(rows[0]["analysis_json"], dict)


def test_follow_up_updates_customer_next_date(db_path) -> None:
    customer_id = create_customer({"company_name": "Fictional Follow-up Studio"}, db_path=db_path)
    create_follow_up(
        {
            "customer_id": customer_id,
            "follow_up_date": "2026-07-16",
            "communication_type": "Email",
            "content": "Sent fictional packaging specifications.",
            "outcome": "Awaiting reply",
            "next_follow_up_date": "2026-07-20",
            "priority": "High",
        },
        db_path=db_path,
    )

    follow_ups = list_follow_ups(db_path=db_path)
    assert follow_ups[0]["company_name"] == "Fictional Follow-up Studio"
    assert follow_ups[0]["next_follow_up_date"] == "2026-07-20"


def test_product_crud_and_search(db_path) -> None:
    product_id = create_product(
        {"product_name": "Fictional Paper Sleeve", "category": "Packaging", "moq": 500},
        db_path=db_path,
    )
    assert get_product(product_id, db_path=db_path)["moq"] == 500
    assert update_product(product_id, {"moq": 800}, db_path=db_path)
    assert list_products(search="Paper Sleeve", db_path=db_path)[0]["moq"] == 800
    assert delete_product(product_id, db_path=db_path)
    assert get_product(product_id, db_path=db_path) is None
