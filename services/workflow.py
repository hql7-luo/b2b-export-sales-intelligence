"""Database-backed orchestration for the inquiry-to-follow-up workflow."""

from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Mapping

from database.repository import (
    create_customer,
    create_follow_up,
    create_inquiry,
    create_quotation,
    get_customer,
    get_inquiry,
    get_product,
    get_quotation,
)


def parse_quantity(value: Any) -> int:
    """Extract the first positive whole-number quantity from inquiry text."""
    match = re.search(r"\d[\d,\s]*", str(value or ""))
    if not match:
        raise ValueError("quantity is required before creating a quotation")
    quantity = int(re.sub(r"[,\s]", "", match.group()))
    if quantity <= 0:
        raise ValueError("quantity must be greater than zero")
    return quantity


def save_inquiry_for_customer(
    *,
    raw_text: str,
    analysis: Mapping[str, Any],
    analysis_mode: str,
    matched_product_id: int | None,
    existing_customer_id: int | None = None,
    new_customer: Mapping[str, Any] | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Save or create the customer, then persist the linked inquiry."""
    if existing_customer_id and new_customer:
        raise ValueError("choose either an existing customer or a new customer")
    customer_created = False
    customer_id = existing_customer_id
    if customer_id is None:
        if not new_customer:
            raise ValueError("customer is required before saving the inquiry")
        customer_id = create_customer(new_customer, db_path=db_path)
        customer_created = True
    elif get_customer(customer_id, db_path=db_path) is None:
        raise ValueError("selected customer was not found")

    inquiry_id = create_inquiry(
        customer_id=customer_id,
        raw_text=raw_text,
        analysis=analysis,
        analysis_mode=analysis_mode,
        matched_product_id=matched_product_id,
        db_path=db_path,
    )
    customer = get_customer(customer_id, db_path=db_path)
    return {
        "customer_id": customer_id,
        "customer_name": customer["company_name"],
        "customer_created": customer_created,
        "inquiry_id": inquiry_id,
        "product_id": matched_product_id,
    }


def build_quotation_context(
    inquiry_id: int, db_path: str | Path | None = None
) -> dict[str, Any]:
    """Reload quote inheritance from SQLite, not Session State."""
    inquiry = get_inquiry(inquiry_id, db_path=db_path)
    if inquiry is None:
        raise ValueError("saved inquiry was not found")
    if inquiry.get("customer_id") is None:
        raise ValueError("saved inquiry is not linked to a customer")
    customer = get_customer(inquiry["customer_id"], db_path=db_path)
    if customer is None:
        raise ValueError("linked customer was not found")
    product = (
        get_product(inquiry["matched_product_id"], db_path=db_path)
        if inquiry.get("matched_product_id") is not None
        else None
    )
    return {
        "customer_id": customer["id"],
        "customer_name": customer["company_name"],
        "customer_stage": customer["current_stage"],
        "country": customer.get("country") or "",
        "inquiry_id": inquiry["id"],
        "product_id": inquiry.get("matched_product_id"),
        "product_name": (
            product.get("product_name") if product else inquiry.get("product")
        )
        or "",
        "quantity": parse_quantity(inquiry.get("quantity")),
        "quantity_text": inquiry.get("quantity") or "",
        "specification": inquiry.get("specification") or "",
        "destination": inquiry.get("destination") or "",
        "unit_cost": product.get("unit_cost") if product else None,
        "moq": product.get("moq") if product else None,
        "production_lead_time": (
            product.get("production_lead_time") if product else None
        ),
    }


def save_quotation_for_inquiry(
    inquiry_id: int,
    quotation: Mapping[str, Any],
    db_path: str | Path | None = None,
) -> int:
    """Persist a quotation while forcing all core fields from the inquiry."""
    inherited = build_quotation_context(inquiry_id, db_path=db_path)
    record = {
        **dict(quotation),
        "customer_id": inherited["customer_id"],
        "inquiry_id": inherited["inquiry_id"],
        "product_id": inherited["product_id"],
        "product_name": inherited["product_name"],
        "quantity": inherited["quantity"],
        "specification": inherited["specification"],
        "destination": inherited["destination"],
        "moq": inherited["moq"],
        "lead_time": inherited["production_lead_time"],
    }
    return create_quotation(record, db_path=db_path)


def build_follow_up_context(
    quotation_id: int,
    *,
    today: date | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Reload quotation relationships and recommend the next follow-up date."""
    quotation = get_quotation(quotation_id, db_path=db_path)
    if quotation is None:
        raise ValueError("saved quotation was not found")
    if quotation.get("customer_id") is None:
        raise ValueError("saved quotation is not linked to a customer")
    customer = get_customer(quotation["customer_id"], db_path=db_path)
    if customer is None:
        raise ValueError("linked customer was not found")
    current_date = today or date.today()
    offset = 2 if customer["current_stage"] == "Quoted" else 3
    return {
        "customer_id": customer["id"],
        "customer_name": customer["company_name"],
        "customer_stage": customer["current_stage"],
        "inquiry_id": quotation.get("inquiry_id"),
        "quotation_id": quotation["id"],
        "product_id": quotation.get("product_id"),
        "product_name": quotation.get("product_name") or "",
        "recommended_follow_up_date": (
            current_date + timedelta(days=offset)
        ).isoformat(),
    }


def save_follow_up_for_quotation(
    quotation_id: int,
    follow_up: Mapping[str, Any],
    db_path: str | Path | None = None,
) -> int:
    """Persist a follow-up with customer, inquiry and quotation IDs inherited."""
    inherited = build_follow_up_context(quotation_id, db_path=db_path)
    record = {
        **dict(follow_up),
        "customer_id": inherited["customer_id"],
        "inquiry_id": inherited["inquiry_id"],
        "quotation_id": inherited["quotation_id"],
        "customer_stage": inherited["customer_stage"],
    }
    return create_follow_up(record, db_path=db_path)


__all__ = [
    "build_follow_up_context",
    "build_quotation_context",
    "parse_quantity",
    "save_follow_up_for_quotation",
    "save_inquiry_for_customer",
    "save_quotation_for_inquiry",
]
