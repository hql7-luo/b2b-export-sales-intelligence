"""Independent customer data-completeness and commercial-quality assessment."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Mapping

from database.connection import get_connection
from database.init_db import initialize_database


COMPLETENESS_FIELDS = (
    "company_name",
    "contact_name",
    "country",
    "email",
    "phone",
    "lead_source",
    "product_interest",
    "import_frequency",
    "estimated_purchase_volume",
    "current_stage",
    "next_follow_up_date",
)

STAGE_VALUE = {
    "New Lead": 0,
    "Contacted": 5,
    "Replied": 10,
    "Requirement Confirmed": 18,
    "Quoted": 23,
    "Sample": 27,
    "Negotiation": 31,
    "Order Confirmed": 35,
    "Lost": 0,
}

NEXT_ACTION_BY_STAGE = {
    "New Lead": "first_contact",
    "Contacted": "share_relevant_example",
    "Replied": "confirm_missing_requirements",
    "Requirement Confirmed": "prepare_quotation",
    "Quoted": "follow_up_quotation",
    "Sample": "collect_sample_feedback",
    "Negotiation": "resolve_commercial_terms",
    "Order Confirmed": "confirm_execution_milestones",
    "Lost": "record_loss_reason",
}


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value > 0
    return bool(str(value).strip())


def _parse_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except (TypeError, ValueError):
        return None


def data_completeness(customer: Mapping[str, Any]) -> dict[str, Any]:
    """Measure record usability without inferring commercial value."""
    present = [field for field in COMPLETENESS_FIELDS if _has_value(customer.get(field))]
    missing = [field for field in COMPLETENESS_FIELDS if field not in present]
    score = round(len(present) / len(COMPLETENESS_FIELDS) * 100)
    status = "complete" if score >= 80 else "partial" if score >= 50 else "limited"
    return {
        "score": score,
        "status": status,
        "present_fields": present,
        "missing_fields": missing,
    }


def commercial_lead_quality(
    customer: Mapping[str, Any],
    *,
    evidence: Mapping[str, Any] | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Score value and buying progress, independent of profile completeness."""
    evidence = evidence or {}
    today = today or date.today()
    try:
        volume = float(customer.get("estimated_purchase_volume") or 0)
    except (TypeError, ValueError):
        volume = 0
    if volume >= 40000:
        volume_score = 30
    elif volume >= 25000:
        volume_score = 25
    elif volume >= 15000:
        volume_score = 20
    elif volume >= 8000:
        volume_score = 14
    elif volume > 0:
        volume_score = 8
    else:
        volume_score = 0

    frequency_score = {
        "Weekly": 10,
        "Monthly": 10,
        "Quarterly": 7,
        "Biannual": 4,
        "Annual": 2,
        "One-time": 1,
    }.get(str(customer.get("import_frequency") or ""), 0)
    stage_score = STAGE_VALUE.get(str(customer.get("current_stage") or ""), 0)

    inquiry_count = int(evidence.get("inquiry_count") or 0)
    quotation_count = int(evidence.get("quotation_count") or 0)
    follow_up_count = int(evidence.get("follow_up_count") or 0)
    matched_product_count = int(evidence.get("matched_product_count") or 0)
    evidence_score = (
        (4 if inquiry_count else 0)
        + (7 if quotation_count else 0)
        + (2 if follow_up_count else 0)
        + (2 if matched_product_count else 0)
    )

    engagement_score = 0
    last_contact = _parse_date(customer.get("last_contact_date"))
    if last_contact is not None:
        days_since_contact = (today - last_contact).days
        engagement_score += 5 if days_since_contact <= 14 else 2 if days_since_contact <= 45 else 0
    next_follow_up = _parse_date(customer.get("next_follow_up_date"))
    if next_follow_up is not None:
        engagement_score += 5 if next_follow_up >= today else 2

    score = min(
        volume_score
        + frequency_score
        + stage_score
        + evidence_score
        + engagement_score,
        100,
    )
    if score >= 75:
        band = "high_potential"
    elif score >= 55:
        band = "qualified"
    elif score >= 30:
        band = "developing"
    else:
        band = "low_signal"
    return {
        "score": score,
        "band": band,
        "drivers": {
            "purchase_potential": volume_score + frequency_score,
            "buying_progress": stage_score,
            "commercial_evidence": evidence_score,
            "engagement": engagement_score,
        },
    }


def assess_customer(
    customer: Mapping[str, Any],
    *,
    evidence: Mapping[str, Any] | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Return the two independent assessments and one actionable next step."""
    due_date = _parse_date(customer.get("next_follow_up_date"))
    current_date = today or date.today()
    next_action = (
        "recover_overdue_follow_up"
        if due_date is not None
        and due_date < current_date
        and customer.get("current_stage") not in {"Order Confirmed", "Lost"}
        else NEXT_ACTION_BY_STAGE.get(
            str(customer.get("current_stage") or ""),
            "confirm_next_action",
        )
    )
    return {
        "data_completeness": data_completeness(customer),
        "lead_quality": commercial_lead_quality(
            customer,
            evidence=evidence,
            today=current_date,
        ),
        "next_action": next_action,
    }


def customer_portfolio(
    db_path: str | Path | None = None,
    *,
    today: date | None = None,
) -> list[dict[str, Any]]:
    """Return customers enriched with persisted workflow evidence."""
    initialize_database(db_path)
    connection = get_connection(db_path)
    try:
        rows = connection.execute(
            """
            SELECT
                c.*,
                COUNT(DISTINCT i.id) AS inquiry_count,
                COUNT(DISTINCT q.id) AS quotation_count,
                COUNT(DISTINCT f.id) AS follow_up_count,
                COUNT(DISTINCT CASE
                    WHEN i.matched_product_id IS NOT NULL THEN i.id
                END) AS matched_product_count
            FROM customers c
            LEFT JOIN inquiries i ON i.customer_id = c.id
            LEFT JOIN quotations q ON q.customer_id = c.id
            LEFT JOIN follow_ups f ON f.customer_id = c.id
            GROUP BY c.id
            ORDER BY c.updated_at DESC, c.id DESC
            """
        ).fetchall()
    finally:
        connection.close()

    portfolio = []
    for raw in rows:
        customer = dict(raw)
        evidence = {
            "inquiry_count": customer["inquiry_count"],
            "quotation_count": customer["quotation_count"],
            "follow_up_count": customer["follow_up_count"],
            "matched_product_count": customer["matched_product_count"],
        }
        assessment = assess_customer(customer, evidence=evidence, today=today)
        portfolio.append(
            {
                **customer,
                **evidence,
                "data_completeness_score": assessment["data_completeness"]["score"],
                "data_completeness_status": assessment["data_completeness"]["status"],
                "missing_profile_fields": assessment["data_completeness"]["missing_fields"],
                "lead_quality_score": assessment["lead_quality"]["score"],
                "lead_quality_band": assessment["lead_quality"]["band"],
                "lead_quality_drivers": assessment["lead_quality"]["drivers"],
                "next_action": assessment["next_action"],
            }
        )
    return portfolio


__all__ = [
    "assess_customer",
    "commercial_lead_quality",
    "customer_portfolio",
    "data_completeness",
]
