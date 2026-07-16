"""Localized, presentation-ready inquiry brief derived from analysis facts."""

from __future__ import annotations

from typing import Any, Mapping

from services.inquiry_analyzer import ANALYSIS_FIELDS
from utils.i18n import translate


SUMMARY_FIELDS = (
    "product",
    "specification",
    "quantity",
    "destination",
    "required_delivery_time",
    "target_price",
)

MISSING_LEVELS = {
    "required": (
        "product",
        "specification",
        "quantity",
        "destination",
    ),
    "recommended": (
        "required_delivery_time",
        "target_price",
        "payment_requirement",
        "customization_requirement",
    ),
    "optional": (
        "application",
        "packaging_requirement",
        "sample_requirement",
    ),
}

QUESTION_PRIORITY = (
    "product",
    "specification",
    "quantity",
    "destination",
    "required_delivery_time",
    "customization_requirement",
    "packaging_requirement",
    "target_price",
    "sample_requirement",
    "payment_requirement",
    "application",
)

CONFIRMATION_QUESTIONS = (
    "confirm_incoterm",
    "confirm_artwork",
    "confirm_decision_timeline",
)


def _text(key: str, language: str, **values: Any) -> str:
    return translate(key, language=language, **values)


def _missing_fields(fields: Mapping[str, Any]) -> list[str]:
    return [field for field in ANALYSIS_FIELDS if not fields.get(field)]


def _build_summary(fields: Mapping[str, Any], language: str) -> dict[str, Any]:
    return {
        field: fields.get(field) or _text("inquiry.value.not_confirmed", language)
        for field in SUMMARY_FIELDS
    }


def _build_missing_groups(
    fields: Mapping[str, Any],
    language: str,
) -> list[dict[str, Any]]:
    missing = set(_missing_fields(fields))
    groups = []
    for level, group_fields in MISSING_LEVELS.items():
        groups.append(
            {
                "level": level,
                "title": _text(f"inquiry.missing.{level}.title", language),
                "description": _text(
                    f"inquiry.missing.{level}.description",
                    language,
                ),
                "items": [
                    {
                        "field": field,
                        "label": _text(f"inquiry.field.{field}", language),
                    }
                    for field in group_fields
                    if field in missing
                ],
            }
        )
    return groups


def _risk(
    category: str,
    severity: str,
    message_key: str,
    language: str,
) -> dict[str, str]:
    return {
        "category": category,
        "category_label": _text(f"inquiry.risk.category.{category}", language),
        "severity": severity,
        "severity_label": _text(f"inquiry.risk.severity.{severity}", language),
        "message": _text(message_key, language),
    }


def _build_risks(
    fields: Mapping[str, Any],
    raw_text: str,
    language: str,
) -> list[dict[str, str]]:
    risks: list[dict[str, str]] = []
    lower = str(raw_text or "").lower()

    if not fields.get("product"):
        risks.append(
            _risk("pricing", "high", "inquiry.risk.product_missing", language)
        )
    if not fields.get("quantity"):
        risks.append(
            _risk("pricing", "high", "inquiry.risk.quantity_missing", language)
        )
    if fields.get("target_price") and not fields.get("specification"):
        risks.append(
            _risk(
                "pricing",
                "high",
                "inquiry.risk.target_without_specification",
                language,
            )
        )
    elif not fields.get("specification"):
        risks.append(
            _risk(
                "production",
                "high",
                "inquiry.risk.specification_missing",
                language,
            )
        )
    if not fields.get("destination"):
        risks.append(
            _risk("delivery", "high", "inquiry.risk.destination_missing", language)
        )
    if any(word in lower for word in ("urgent", "asap", "immediately")):
        risks.append(
            _risk("delivery", "medium", "inquiry.risk.urgent_timeline", language)
        )
    elif not fields.get("required_delivery_time"):
        risks.append(
            _risk("delivery", "medium", "inquiry.risk.delivery_missing", language)
        )
    if not fields.get("packaging_requirement"):
        risks.append(
            _risk("production", "low", "inquiry.risk.packaging_missing", language)
        )
    if not fields.get("payment_requirement"):
        risks.append(
            _risk("commercial", "low", "inquiry.risk.payment_missing", language)
        )
    return risks


def _build_questions(
    fields: Mapping[str, Any],
    language: str,
) -> list[dict[str, str]]:
    missing = set(_missing_fields(fields))
    question_keys = [field for field in QUESTION_PRIORITY if field in missing][:5]
    if len(question_keys) < 3:
        for key in CONFIRMATION_QUESTIONS:
            if len(question_keys) >= 3:
                break
            question_keys.append(key)
    return [
        {
            "key": key,
            "text": _text(f"inquiry.question.{key}", language),
        }
        for key in question_keys
    ]


def _build_next_actions(
    missing_groups: list[dict[str, Any]],
    language: str,
) -> list[dict[str, str]]:
    has_required_gaps = bool(missing_groups[0]["items"])
    review_key = (
        "inquiry.next.resolve_required"
        if has_required_gaps
        else "inquiry.next.confirm_summary"
    )
    return [
        {
            "key": "review",
            "title": _text("inquiry.next.review.title", language),
            "text": _text(review_key, language),
        },
        {
            "key": "match",
            "title": _text("inquiry.next.match.title", language),
            "text": _text("inquiry.next.match.text", language),
        },
        {
            "key": "save",
            "title": _text("inquiry.next.save.title", language),
            "text": _text("inquiry.next.save.text", language),
        },
    ]


def build_inquiry_brief(
    analysis: Mapping[str, Any],
    *,
    raw_text: str,
    language: str,
) -> dict[str, Any]:
    """Build a localized brief without mutating the stored analysis contract."""
    fields = dict(analysis.get("extracted_fields") or {})
    missing_groups = _build_missing_groups(fields, language)
    return {
        "summary": _build_summary(fields, language),
        "missing_groups": missing_groups,
        "risks": _build_risks(fields, raw_text, language),
        "questions": _build_questions(fields, language),
        "next_actions": _build_next_actions(missing_groups, language),
    }
