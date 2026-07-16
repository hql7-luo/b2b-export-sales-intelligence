"""Tests for schema, customer CRUD, overrides, and demo data."""

from decimal import Decimal

from database.connection import get_connection, resolve_database_path
from database.init_db import REQUIRED_TABLES
from database.repository import (
    create_customer,
    create_customers_batch,
    create_quotation,
    delete_customer,
    get_customer,
    list_customers,
    list_quotations,
    set_manual_score,
    update_customer,
)
from database.seed_data import seed_demo_data
from services.quotation import calculate_quotation
from utils.constants import IMPORT_FREQUENCIES, LEAD_SOURCES


def test_initialization_creates_six_required_tables(db_path):
    connection = get_connection(db_path)
    try:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = ?", ("table",)
        ).fetchall()
    finally:
        connection.close()

    table_names = {row["name"] for row in rows}
    assert REQUIRED_TABLES == {
        "customers",
        "inquiries",
        "quotations",
        "follow_ups",
        "products",
        "activities",
    }
    assert REQUIRED_TABLES.issubset(table_names)


def test_database_path_can_be_overridden_for_clean_demo_runs(
    tmp_path,
    monkeypatch,
):
    override = tmp_path / "clean-demo.db"
    monkeypatch.setenv("DATABASE_PATH", str(override))

    assert resolve_database_path() == override
    connection = get_connection()
    try:
        assert connection.execute("PRAGMA database_list").fetchone()["file"] == str(
            override
        )
    finally:
        connection.close()


def test_customer_crud_uses_and_returns_business_fields(db_path):
    customer_id = create_customer(
        {
            "company_name": "Ink & Orbit Atelier's",
            "contact_name": "Avery Lin",
            "country": "Canada",
            "email": "avery@ink-orbit.example.com",
            "product_interest": "Gift boxes",
            "current_stage": "New Lead",
        },
        db_path=db_path,
    )

    customer = get_customer(customer_id, db_path=db_path)
    assert customer["company_name"] == "Ink & Orbit Atelier's"

    updated = update_customer(
        customer_id,
        {"current_stage": "Contacted", "notes": "Requested FSC options"},
        db_path=db_path,
    )
    assert updated is True
    assert get_customer(customer_id, db_path=db_path)["current_stage"] == "Contacted"
    assert len(list_customers(db_path=db_path)) == 1

    assert delete_customer(customer_id, db_path=db_path) is True
    assert get_customer(customer_id, db_path=db_path) is None


def test_phone_whatsapp_alias_is_preserved(db_path):
    customer_id = create_customer(
        {
            "company_name": "Fictional Alias Studio",
            "phone_whatsapp": "+00 555 0199",
        },
        db_path=db_path,
    )
    assert get_customer(customer_id, db_path=db_path)["phone"] == "+00 555 0199"


def test_customer_batch_rejects_all_rows_before_any_insert(db_path):
    try:
        create_customers_batch(
            [
                {"company_name": "Fictional Valid Row"},
                {"company_name": ""},
            ],
            db_path=db_path,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("invalid customer batch should fail")

    assert list_customers(db_path=db_path) == []


def test_manual_score_override_is_persisted_and_auditable(db_path):
    customer_id = create_customer(
        {
            "company_name": "Paper Comet Collective",
            "auto_score": 72,
            "auto_grade": "B",
            "score_breakdown": {"company_authenticity": 15},
        },
        db_path=db_path,
    )

    set_manual_score(
        customer_id,
        score=82,
        reason="Purchase plan confirmed during video call",
        db_path=db_path,
    )
    customer = get_customer(customer_id, db_path=db_path)

    assert customer["manual_score"] == 82
    assert customer["manual_grade"] == "A"
    assert customer["effective_score"] == 82
    assert customer["effective_grade"] == "A"
    assert customer["score_override_reason"] == "Purchase plan confirmed during video call"
    assert customer["score_overridden_at"] is not None


def test_quotation_repository_matches_page_payload_and_serializes_decimals(db_path):
    quotation_id = create_quotation(
        {
            "product_name": "Fictional custom notebook",
            "incoterm": "FOB",
            "quantity": 1000,
            "pricing_method": "gross_margin",
            "pricing_rate": 0.25,
            "exchange_rate": 7.2,
            "total_quote_usd": 2000.0,
            "unit_quote_usd": 2.0,
            "gross_profit_usd": 500.0,
            "gross_margin": 0.25,
            "calculation_json": {"total": Decimal("2000.00")},
        },
        db_path=db_path,
    )

    rows = list_quotations(db_path=db_path)
    assert quotation_id == rows[0]["id"]
    assert rows[0]["pricing_method"] == "gross_margin"
    assert rows[0]["pricing_rate"] == 0.25
    assert rows[0]["calculation_json"] == {"total": "2000.00"}


def test_demo_seed_is_fictional_exact_and_idempotent(db_path):
    counts = seed_demo_data(db_path)
    second_counts = seed_demo_data(db_path)

    assert counts == {
        "customers": 20,
        "inquiries": 10,
        "quotations": 8,
        "follow_ups": 10,
        "products": 6,
    }
    assert second_counts == counts

    connection = get_connection(db_path)
    try:
        emails = [
            row["email"]
            for row in connection.execute("SELECT email FROM customers").fetchall()
        ]
        product_names = {
            row["product_name"]
            for row in connection.execute("SELECT product_name FROM products").fetchall()
        }
    finally:
        connection.close()

    assert all(email.endswith(".example.com") for email in emails)
    assert product_names == {
        "Aurora Custom Notebook",
        "Starlight Festival Gift Box",
        "Meadow Greeting Card Set",
        "Orbit Creative Packaging Box",
        "Harbor Desk Calendar",
        "Comet Die-cut Sticker Pack",
    }


def test_demo_scores_are_rule_derived_and_cover_all_grade_bands(db_path):
    seed_demo_data(db_path)
    customers = list_customers(db_path=db_path)

    assert {customer["auto_grade"] for customer in customers} == {"A", "B", "C", "D"}
    for customer in customers:
        assert customer["auto_score"] == sum(customer["score_breakdown"].values())
        assert "calibrated" not in " ".join(customer["score_reasons"].values()).lower()
        assert customer["lead_source"] in LEAD_SOURCES
        assert customer["import_frequency"] in {*IMPORT_FREQUENCIES, ""}


def test_every_demo_quotation_matches_the_calculation_engine(db_path):
    seed_demo_data(db_path)
    for stored in list_quotations(db_path=db_path):
        calculated = calculate_quotation(
            product_unit_cost_cny=stored["unit_product_cost"],
            packaging_unit_cost_cny=stored["packaging_cost"],
            quantity=stored["quantity"],
            domestic_transport_cny=stored["domestic_transportation_cost"],
            export_handling_cny=stored["export_handling_cost"],
            international_freight_cny=stored["international_freight"],
            insurance_cny=stored["insurance_cost"],
            tariff_tax_cny=stored["tariff_and_tax"],
            platform_bank_fee_cny=stored["platform_or_bank_fee"],
            exchange_rate_cny_per_usd=stored["exchange_rate"],
            pricing_method=stored["pricing_method"],
            pricing_rate=stored["pricing_rate"],
        )["terms"][stored["incoterm"]]
        assert stored["total_cost_cny"] == float(calculated["cost_total_cny"])
        assert stored["unit_quote_usd"] == float(calculated["unit_usd"])
        assert stored["total_quote_usd"] == float(calculated["total_usd"])
        assert stored["gross_profit_usd"] == float(calculated["gross_profit_usd"])
        assert stored["gross_margin"] == float(calculated["gross_margin"])
