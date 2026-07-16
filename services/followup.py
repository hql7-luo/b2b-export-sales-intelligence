"""Follow-up prioritization and stage-specific communication helpers."""

from __future__ import annotations

from datetime import date

STAGE_ADVICE = {
    "New Lead": "Send a short first-contact message focused on product fit and one proof point.",
    "Contacted": "Follow up after 3–5 days with a relevant product example and one clear question.",
    "Replied": "Summarize the buyer's need and ask for the missing commercial details.",
    "Requirement Confirmed": "Confirm specification, quantity, destination and target date before quoting.",
    "Quoted": "Follow up 2 days after the quotation, then again after 7 days if there is no reply.",
    "Sample": "Check delivery and feedback after the sample arrives; agree on any required revisions.",
    "Negotiation": "Address price pressure through specification, volume or terms—not discount alone.",
    "Order Confirmed": "Confirm deposit, artwork approval, production milestones and shipping documents.",
    "Lost": "Record the loss reason and schedule a low-frequency reactivation if appropriate.",
}


def follow_up_advice(stage: str) -> str:
    """Return a concise, practical action for the current stage."""
    return STAGE_ADVICE.get(stage, "Confirm the customer's current need and agree on one next action.")


def follow_up_priority(grade: str, next_follow_up_date: str | date | None, today: date | None = None) -> int:
    """Combine explainable grade weight and overdue days into a priority score."""
    today = today or date.today()
    grade_weight = {"A": 40, "B": 30, "C": 20, "D": 10}.get(str(grade).upper(), 0)
    if not next_follow_up_date:
        return grade_weight
    try:
        due = (
            next_follow_up_date
            if isinstance(next_follow_up_date, date)
            else date.fromisoformat(str(next_follow_up_date)[:10])
        )
    except (TypeError, ValueError):
        return grade_weight
    overdue_days = max((today - due).days, 0)
    due_soon_bonus = 5 if 0 <= (due - today).days <= 2 else 0
    return grade_weight + min(overdue_days * 3, 45) + due_soon_bonus


def generate_follow_up_message(
    contact_name: str | None,
    stage: str | None,
    product_interest: str | None,
) -> str:
    """Generate a short, natural message without an external API."""
    name = str(contact_name or "").strip() or "there"
    product = str(product_interest or "").strip() or "your sourcing project"
    body_map = {
        "Quoted": f"I wanted to check whether you had any questions about our quotation for {product}. We can also review specifications, quantity or shipping terms if helpful.",
        "Sample": f"I hope the sample for {product} arrived safely. Could you share your feedback on quality, finish and packaging so we can prepare the next step?",
        "Negotiation": f"Thank you for your feedback on {product}. We can review volume, specifications and commercial terms together to find a workable option.",
        "Order Confirmed": f"We are ready to move forward with {product}. Please confirm the artwork, deposit and requested shipping schedule so we can reserve production capacity.",
    }
    body = body_map.get(
        stage,
        f"I am following up regarding {product}. Please let me know your current priorities and whether any additional information would help your evaluation.",
    )
    return f"Hi {name},\n\n{body}\n\nBest regards,\nExport Sales Team"
