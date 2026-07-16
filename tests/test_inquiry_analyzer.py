from __future__ import annotations

from services.inquiry_analyzer import ANALYSIS_FIELDS, analyze_inquiry_rules, validate_analysis
import pytest


def test_rule_analysis_returns_normalized_contract() -> None:
    text = (
        "We need 5,000 custom hardcover notebooks with our logo, A5 size, "
        "individually packed for delivery to Hamburg, Germany by 15 October. "
        "Please quote a sample and advise T/T payment."
    )

    result = analyze_inquiry_rules(text)

    assert set(result) == {
        "extracted_fields",
        "confirmed_info",
        "missing_info",
        "risks",
        "next_questions",
        "completeness_score",
        "suggested_reply",
    }
    assert set(result["extracted_fields"]) == set(ANALYSIS_FIELDS)
    assert result["extracted_fields"]["product"] == "Custom hardcover notebook"
    assert "5,000" in result["extracted_fields"]["quantity"]
    assert result["extracted_fields"]["destination"] is not None
    assert result["extracted_fields"]["target_price"] is None
    assert 0 < result["completeness_score"] < 100
    assert "Dear" in result["suggested_reply"]


def test_rule_analysis_does_not_invent_missing_information() -> None:
    result = analyze_inquiry_rules("Please send your catalogue.")

    assert all(value is None for value in result["extracted_fields"].values())
    assert result["completeness_score"] == 0
    assert "product" in result["missing_info"]


def test_validation_rejects_invalid_ai_contract() -> None:
    invalid = {"extracted_fields": {"product": "Gift box"}}

    try:
        validate_analysis(invalid)
    except ValueError as exc:
        assert "missing" in str(exc).lower()
    else:
        raise AssertionError("Invalid analysis should be rejected")


def test_rule_analysis_rejects_oversized_input() -> None:
    with pytest.raises(ValueError, match="20,000"):
        analyze_inquiry_rules("x" * 20_001)
