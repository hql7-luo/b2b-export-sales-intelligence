"""Phase 2 inquiry-brief behavior and localization tests."""

from services.inquiry_analyzer import analyze_inquiry_rules
from services.inquiry_brief import build_inquiry_brief


DEMO_INQUIRY = (
    "Hello, we need 5,000 custom hardcover notebooks with our logo, A5 size "
    "and recycled paper. Please pack each notebook in a paper sleeve and "
    "deliver to Hamburg, Germany by 15 October. Could you quote a "
    "pre-production sample and advise T/T payment terms?"
)


def test_brief_builds_summary_and_tiered_missing_information() -> None:
    result = analyze_inquiry_rules(DEMO_INQUIRY)

    brief = build_inquiry_brief(result, raw_text=DEMO_INQUIRY, language="en")

    assert brief["summary"]["product"] == "Custom hardcover notebook"
    assert brief["summary"]["quantity"]
    assert brief["summary"]["destination"] == "Hamburg, Germany"
    assert "recycled paper" in brief["summary"]["specification"].lower()
    assert result["extracted_fields"]["packaging_requirement"] == "paper sleeve"
    assert [group["level"] for group in brief["missing_groups"]] == [
        "required",
        "recommended",
        "optional",
    ]
    grouped_fields = {
        item["field"]
        for group in brief["missing_groups"]
        for item in group["items"]
    }
    assert grouped_fields == set(result["missing_info"])


def test_brief_returns_classified_risks_and_three_to_five_questions() -> None:
    text = "Urgent: please quote custom gift boxes at USD 2.00 per piece."
    result = analyze_inquiry_rules(text)

    brief = build_inquiry_brief(result, raw_text=text, language="en")

    assert 3 <= len(brief["questions"]) <= 5
    assert {risk["category"] for risk in brief["risks"]} <= {
        "pricing",
        "delivery",
        "production",
        "commercial",
    }
    assert {risk["severity"] for risk in brief["risks"]} <= {
        "high",
        "medium",
        "low",
    }
    assert any(risk["category"] == "pricing" for risk in brief["risks"])
    assert any(risk["category"] == "delivery" for risk in brief["risks"])


def test_chinese_brief_localizes_risks_questions_and_action_guidance() -> None:
    result = analyze_inquiry_rules("Please send your catalogue.")

    brief = build_inquiry_brief(
        result,
        raw_text="Please send your catalogue.",
        language="zh",
    )

    user_guidance = [
        *(risk["message"] for risk in brief["risks"]),
        *(question["text"] for question in brief["questions"]),
        *(action["text"] for action in brief["next_actions"]),
    ]
    assert user_guidance
    assert all(any("\u4e00" <= char <= "\u9fff" for char in text) for text in user_guidance)
    assert all("Which exact product" not in text for text in user_guidance)
    assert all("Quantity is not confirmed" not in text for text in user_guidance)
    assert "Unavailable text" not in str(brief)
    assert "文案暂不可用" not in str(brief)


def test_brief_supplies_three_confirmation_questions_when_few_fields_are_missing() -> None:
    complete = {
        "extracted_fields": {
            "product": "Notebook",
            "specification": "A5, recycled paper",
            "quantity": "5,000 pcs",
            "application": "Corporate gifts",
            "customization_requirement": "Logo printing",
            "packaging_requirement": "Paper sleeve",
            "destination": "Hamburg, Germany",
            "required_delivery_time": "15 October",
            "target_price": "USD 3.00",
            "sample_requirement": "Pre-production sample",
            "payment_requirement": "T/T",
        },
        "confirmed_info": [],
        "missing_info": [],
        "risks": [],
        "next_questions": [],
        "completeness_score": 100,
        "suggested_reply": "Dear Customer,\n\nThank you.\n\nBest regards",
    }

    brief = build_inquiry_brief(complete, raw_text="Complete inquiry", language="en")

    assert len(brief["questions"]) == 3
    assert len({question["key"] for question in brief["questions"]}) == 3
