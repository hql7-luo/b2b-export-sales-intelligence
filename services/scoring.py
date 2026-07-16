"""Transparent, rules-based 100-point lead scoring."""

from __future__ import annotations

from numbers import Real
from typing import Any, Mapping


DIMENSION_MAX_SCORES = {
    "company_authenticity": 20,
    "product_fit": 25,
    "requirement_clarity": 20,
    "purchasing_capacity": 20,
    "communication_engagement": 15,
}

GRADE_RANGES = {
    "A": "80-100: high-priority lead with strong commercial potential",
    "B": "65-79: qualified lead that merits active follow-up",
    "C": "45-64: developing lead that needs more qualification",
    "D": "0-44: low-information or low-priority lead",
}


def _validated_number(value: Real, name: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a number between 0 and {maximum}")
    if value < 0 or value > maximum:
        raise ValueError(f"{name} must be between 0 and {maximum}")
    if int(value) != value:
        raise ValueError(f"{name} must be a whole-number score")
    return int(value)


def grade_for_score(score: Real) -> str:
    """Convert a 0-100 score to the documented A/B/C/D grade."""
    numeric_score = _validated_number(score, "score", 100)
    if numeric_score >= 80:
        return "A"
    if numeric_score >= 65:
        return "B"
    if numeric_score >= 45:
        return "C"
    return "D"


def calculate_lead_score(
    company_authenticity: Real,
    product_fit: Real,
    requirement_clarity: Real,
    purchasing_capacity: Real,
    communication_engagement: Real,
) -> dict[str, Any]:
    """Add five visible dimensions and return an explainable result."""
    supplied = {
        "company_authenticity": company_authenticity,
        "product_fit": product_fit,
        "requirement_clarity": requirement_clarity,
        "purchasing_capacity": purchasing_capacity,
        "communication_engagement": communication_engagement,
    }
    breakdown = {
        name: _validated_number(value, name, DIMENSION_MAX_SCORES[name])
        for name, value in supplied.items()
    }
    total = sum(breakdown.values())
    grade = grade_for_score(total)
    return {
        "total_score": total,
        "grade": grade,
        "breakdown": breakdown,
        "grade_reason": GRADE_RANGES[grade],
    }


def _present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _volume(value: Any) -> float:
    try:
        return max(0.0, float(value or 0))
    except (TypeError, ValueError):
        return 0.0


def score_customer(customer: Mapping[str, Any]) -> dict[str, Any]:
    """Derive the five scores from ordinary customer fields.

    The individual rules are intentionally simple so a salesperson can see
    how every point was earned and can override the final score with a reason.
    """
    authenticity = 0
    authenticity_items: list[str] = []
    authenticity_rules = (
        ("company_name", 4, "company name"),
        ("website", 6, "website"),
        ("email", 5, "business email"),
        ("phone", 5, "phone/WhatsApp"),
    )
    for field, points, label in authenticity_rules:
        if _present(customer.get(field)):
            authenticity += points
            authenticity_items.append(f"{label} +{points}")

    interest = str(customer.get("product_interest") or "").strip()
    product_fit = 0
    product_items: list[str] = []
    if interest:
        product_fit += 15
        product_items.append("product interest recorded +15")
        detail_terms = (
            "custom",
            "material",
            "size",
            "specification",
            "packaging",
            "notebook",
            "gift box",
            "card",
            "calendar",
            "sticker",
        )
        if any(term in interest.lower() for term in detail_terms):
            product_fit += 10
            product_items.append("recognizable product/specification detail +10")

    requirement_clarity = 0
    clarity_items: list[str] = []
    clarity_rules = (
        (bool(interest), 5, "product identified"),
        (_present(customer.get("import_frequency")), 7, "purchase frequency recorded"),
        (_volume(customer.get("estimated_purchase_volume")) > 0, 8, "purchase volume recorded"),
    )
    for condition, points, label in clarity_rules:
        if condition:
            requirement_clarity += points
            clarity_items.append(f"{label} +{points}")

    volume = _volume(customer.get("estimated_purchase_volume"))
    if volume >= 50_000:
        volume_points = 14
    elif volume >= 10_000:
        volume_points = 12
    elif volume >= 5_000:
        volume_points = 9
    elif volume > 0:
        volume_points = 5
    else:
        volume_points = 0
    frequency = str(customer.get("import_frequency") or "").lower()
    frequency_points = 0
    for term, points in (
        ("monthly", 6),
        ("quarter", 5),
        ("biannual", 3),
        ("annual", 2),
    ):
        if term in frequency:
            frequency_points = points
            break
    purchasing_capacity = min(20, volume_points + frequency_points)
    capacity_items = []
    if volume_points:
        capacity_items.append(f"estimated purchase volume +{volume_points}")
    if frequency_points:
        capacity_items.append(f"import frequency +{frequency_points}")

    stage = str(customer.get("current_stage") or "New Lead")
    stage_points = {
        "New Lead": 2,
        "Contacted": 4,
        "Replied": 7,
        "Requirement Confirmed": 10,
        "Quoted": 11,
        "Sample": 12,
        "Negotiation": 14,
        "Order Confirmed": 15,
        "Lost": 0,
    }.get(stage, 0)
    recent_contact_points = 3 if _present(customer.get("last_contact_date")) else 0
    communication = min(15, stage_points + recent_contact_points)
    communication_items = [f"stage '{stage}' +{stage_points}"]
    if recent_contact_points:
        communication_items.append("contact date recorded +3")

    result = calculate_lead_score(
        company_authenticity=authenticity,
        product_fit=product_fit,
        requirement_clarity=requirement_clarity,
        purchasing_capacity=purchasing_capacity,
        communication_engagement=communication,
    )
    result["dimension_reasons"] = {
        "company_authenticity": ", ".join(authenticity_items) or "no verification fields",
        "product_fit": ", ".join(product_items) or "no product interest",
        "requirement_clarity": ", ".join(clarity_items) or "requirements not recorded",
        "purchasing_capacity": ", ".join(capacity_items) or "capacity not recorded",
        "communication_engagement": ", ".join(communication_items),
    }
    return result


# A concise alias for page code.
calculate_customer_score = score_customer
