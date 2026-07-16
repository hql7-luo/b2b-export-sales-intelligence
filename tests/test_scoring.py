"""Tests for the transparent lead-scoring service."""

import pytest

from services.scoring import calculate_lead_score, grade_for_score, score_customer


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0, "D"),
        (44, "D"),
        (45, "C"),
        (64, "C"),
        (65, "B"),
        (79, "B"),
        (80, "A"),
        (100, "A"),
    ],
)
def test_grade_boundaries(score, expected):
    assert grade_for_score(score) == expected


@pytest.mark.parametrize("score", [-1, 101])
def test_grade_rejects_scores_outside_100_point_scale(score):
    with pytest.raises(ValueError, match="between 0 and 100"):
        grade_for_score(score)


def test_calculate_lead_score_returns_explainable_breakdown():
    result = calculate_lead_score(
        company_authenticity=18,
        product_fit=22,
        requirement_clarity=16,
        purchasing_capacity=17,
        communication_engagement=12,
    )

    assert result["total_score"] == 85
    assert result["grade"] == "A"
    assert result["breakdown"] == {
        "company_authenticity": 18,
        "product_fit": 22,
        "requirement_clarity": 16,
        "purchasing_capacity": 17,
        "communication_engagement": 12,
    }
    assert "80-100" in result["grade_reason"]


def test_calculate_lead_score_validates_each_dimension():
    with pytest.raises(ValueError, match="product_fit"):
        calculate_lead_score(
            company_authenticity=18,
            product_fit=26,
            requirement_clarity=16,
            purchasing_capacity=17,
            communication_engagement=12,
        )


def test_score_customer_explains_field_based_rules():
    result = score_customer(
        {
            "company_name": "Fable Harbor Studio",
            "website": "https://fable-harbor.example.com",
            "email": "mia@fable-harbor.example.com",
            "phone": "+1 202 555 0188",
            "product_interest": "Custom notebook with recycled-paper specification",
            "import_frequency": "Quarterly",
            "estimated_purchase_volume": 18000,
            "current_stage": "Requirement Confirmed",
            "last_contact_date": "2026-07-15",
        }
    )

    assert result["total_score"] == sum(result["breakdown"].values())
    assert set(result["breakdown"]) == {
        "company_authenticity",
        "product_fit",
        "requirement_clarity",
        "purchasing_capacity",
        "communication_engagement",
    }
    assert len(result["dimension_reasons"]) == 5
    assert 0 <= result["total_score"] <= 100
