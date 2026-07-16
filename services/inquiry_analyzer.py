"""Rule-based and optional LLM inquiry analysis with one stable JSON contract."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

ANALYSIS_FIELDS = (
    "product",
    "specification",
    "quantity",
    "application",
    "customization_requirement",
    "packaging_requirement",
    "destination",
    "required_delivery_time",
    "target_price",
    "sample_requirement",
    "payment_requirement",
)

QUESTION_MAP = {
    "product": "Which exact product would you like us to quote?",
    "specification": "Could you confirm the size, material, finish and other specifications?",
    "quantity": "What order quantity should we use for the quotation?",
    "application": "How will the product be used or sold?",
    "customization_requirement": "Do you need logo, artwork or other customization?",
    "packaging_requirement": "What packing method and carton requirements do you prefer?",
    "destination": "What is the destination country and delivery port or postcode?",
    "required_delivery_time": "When do you need the goods to arrive?",
    "target_price": "Do you have a target unit price or budget range?",
    "sample_requirement": "Would you like a stock or customized sample first?",
    "payment_requirement": "Do you have a preferred payment method?",
}

PRODUCT_PATTERNS = (
    (r"\bhardcover\s+notebooks?\b", "Custom hardcover notebook"),
    (r"\bnotebooks?\b", "Custom notebook"),
    (r"\bgift\s+boxes?\b", "Custom gift box"),
    (r"\bgreeting\s+cards?\b", "Greeting card set"),
    (r"\bpackaging\s+boxes?\b", "Custom packaging box"),
    (r"\b(?:desk|wall)?\s*calendars?\b", "Custom calendar"),
    (r"\bstickers?\b", "Custom sticker"),
)

COUNTRIES = (
    "United States",
    "USA",
    "Canada",
    "United Kingdom",
    "UK",
    "Germany",
    "France",
    "Netherlands",
    "Australia",
    "Japan",
    "Singapore",
    "United Arab Emirates",
    "UAE",
    "Saudi Arabia",
    "Brazil",
    "Mexico",
)

ANALYSIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "extracted_fields",
        "confirmed_info",
        "missing_info",
        "risks",
        "next_questions",
        "completeness_score",
        "suggested_reply",
    ],
    "properties": {
        "extracted_fields": {
            "type": "object",
            "additionalProperties": False,
            "required": list(ANALYSIS_FIELDS),
            "properties": {
                field: {"type": ["string", "null"]} for field in ANALYSIS_FIELDS
            },
        },
        "confirmed_info": {"type": "array", "items": {"type": "string"}},
        "missing_info": {"type": "array", "items": {"type": "string"}},
        "risks": {"type": "array", "items": {"type": "string"}},
        "next_questions": {"type": "array", "items": {"type": "string"}},
        "completeness_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "suggested_reply": {"type": "string"},
    },
}


@dataclass(frozen=True)
class AnalysisRun:
    """Result plus mode information for the UI."""

    result: dict[str, Any]
    mode: str
    notice: str


def _first_match(pattern: str, text: str, flags: int = re.IGNORECASE) -> str | None:
    match = re.search(pattern, text, flags)
    return match.group(0).strip(" ,.;") if match else None


def _extract_product(text: str) -> str | None:
    for pattern, label in PRODUCT_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return label
    return None


def _extract_destination(text: str) -> str | None:
    port_match = re.search(
        r"(?:to|port of|delivery to|ship to)\s+([A-Z][A-Za-z .-]{2,35}(?:,\s*[A-Z][A-Za-z .-]{2,25})?)",
        text,
    )
    if port_match:
        return port_match.group(1).strip(" ,.;")
    for country in COUNTRIES:
        if re.search(rf"\b{re.escape(country)}\b", text, re.IGNORECASE):
            return country
    return None


def _extract_fields(text: str) -> dict[str, str | None]:
    lower = text.lower()
    specification_parts = []
    for pattern in (
        r"\bA[3-6]\b",
        r"\b\d+(?:\.\d+)?\s*(?:mm|cm|gsm)\b",
        r"\b(?:hardcover|softcover|kraft|rigid|recycled|matte|glossy)\b",
    ):
        match = _first_match(pattern, text)
        if match and match.lower() not in {part.lower() for part in specification_parts}:
            specification_parts.append(match)

    quantity = _first_match(
        r"\b\d[\d,]*(?:\.\d+)?\s*(?:pcs?|pieces?|sets?|units?|boxes?|cartons?)\b",
        text,
    )
    if not quantity:
        # Buyers often write "5,000 custom notebooks" without an explicit pcs unit.
        quantity = _first_match(
            r"\b\d[\d,]*(?:\.\d+)?\s+(?:custom\s+)?(?:hardcover\s+)?(?:notebooks?|gift\s+boxes?|greeting\s+cards?|packaging\s+boxes?|calendars?|stickers?)\b",
            text,
        )
    application = _first_match(
        r"\b(?:retail|resale|promotion(?:al)?|corporate gifts?|wedding|holiday campaign|subscription box)\b",
        text,
    )
    customization = _first_match(
        r"\b(?:custom(?:ized)?[^.;\n]{0,45}|with (?:our|a) logo|logo printing|custom artwork|foil stamping|emboss(?:ed|ing)?)\b",
        text,
    )
    packaging = _first_match(
        r"\b(?:individually packed|individual packaging|retail packaging|polybagged|gift packaging|export cartons?|palletized)\b",
        text,
    )
    delivery = _first_match(
        r"\b(?:by|before|within|in)\s+(?:\d{1,2}\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December|\d{1,3}\s+(?:days?|weeks?))[^.;\n]*",
        text,
    )
    target_price = _first_match(
        r"(?:(?:USD|US\$|EUR|€|\$)\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*(?:USD|EUR))\s*(?:/|per\s*)?(?:pc|piece|set|unit)?",
        text,
    )
    sample = _first_match(r"\b(?:customized sample|stock sample|pre-production sample|sample)\b", text)
    payment = _first_match(r"\b(?:T/T|telegraphic transfer|L/C|letter of credit|PayPal|30% deposit|OA\s*\d+)\b", text)

    return {
        "product": _extract_product(text),
        "specification": ", ".join(specification_parts) or None,
        "quantity": quantity,
        "application": application,
        "customization_requirement": customization,
        "packaging_requirement": packaging,
        "destination": _extract_destination(text),
        "required_delivery_time": delivery,
        "target_price": target_price,
        "sample_requirement": sample,
        "payment_requirement": payment,
    }


def analyze_inquiry_rules(text: str) -> dict[str, Any]:
    """Extract only explicit information using deterministic rules."""
    cleaned = str(text or "").strip()
    if not cleaned:
        raise ValueError("Inquiry text is required.")
    if len(cleaned) > 20_000:
        raise ValueError("Inquiry text cannot exceed 20,000 characters.")

    fields = _extract_fields(cleaned)
    confirmed = [f"{key}: {value}" for key, value in fields.items() if value]
    missing = [key for key, value in fields.items() if not value]
    completeness = round(len(confirmed) / len(ANALYSIS_FIELDS) * 100)

    risks: list[str] = []
    lower = cleaned.lower()
    if not fields["quantity"]:
        risks.append("Quantity is not confirmed, so pricing and production planning are unreliable.")
    if not fields["destination"]:
        risks.append("Destination is missing, so freight and landed cost cannot be estimated.")
    if any(word in lower for word in ("urgent", "asap", "immediately")):
        risks.append("The requested timeline may be urgent; confirm artwork approval and production milestones.")
    if fields["target_price"] and not fields["specification"]:
        risks.append("A target price is mentioned without enough specification detail for comparison.")

    questions = [QUESTION_MAP[field] for field in missing[:6]]
    known_line = "; ".join(confirmed[:3]) or "your sourcing request"
    questions_text = " ".join(f"{index + 1}) {question}" for index, question in enumerate(questions))
    reply = (
        "Dear Customer,\n\n"
        f"Thank you for your inquiry. We have noted {known_line}. "
        "To prepare an accurate quotation, could you please confirm the following? "
        f"{questions_text}\n\n"
        "Once confirmed, we will review production feasibility, lead time and the most suitable shipping term.\n\n"
        "Best regards,\nExport Sales Team"
    )

    return {
        "extracted_fields": fields,
        "confirmed_info": confirmed,
        "missing_info": missing,
        "risks": risks,
        "next_questions": questions,
        "completeness_score": completeness,
        "suggested_reply": reply,
    }


def validate_analysis(result: Any) -> dict[str, Any]:
    """Validate and normalize an AI result without inventing missing values."""
    if not isinstance(result, dict):
        raise ValueError("Analysis must be a JSON object.")
    required = set(ANALYSIS_SCHEMA["required"])
    missing_keys = required - set(result)
    if missing_keys:
        raise ValueError(f"Analysis is missing required keys: {sorted(missing_keys)}")
    fields = result.get("extracted_fields")
    if not isinstance(fields, dict):
        raise ValueError("Analysis is missing a valid extracted_fields object.")
    missing_fields = set(ANALYSIS_FIELDS) - set(fields)
    if missing_fields:
        raise ValueError(f"Analysis is missing extracted fields: {sorted(missing_fields)}")

    normalized_fields = {
        field: str(fields[field]).strip() if fields[field] not in (None, "") else None
        for field in ANALYSIS_FIELDS
    }
    score = result.get("completeness_score")
    if not isinstance(score, (int, float)) or not 0 <= score <= 100:
        raise ValueError("completeness_score must be between 0 and 100.")
    for key in ("confirmed_info", "missing_info", "risks", "next_questions"):
        if not isinstance(result.get(key), list) or not all(
            isinstance(item, str) for item in result[key]
        ):
            raise ValueError(f"{key} must be a list of strings.")
    if not isinstance(result.get("suggested_reply"), str):
        raise ValueError("suggested_reply must be a string.")

    return {
        "extracted_fields": normalized_fields,
        "confirmed_info": result["confirmed_info"],
        "missing_info": result["missing_info"],
        "risks": result["risks"],
        "next_questions": result["next_questions"],
        "completeness_score": int(round(score)),
        "suggested_reply": result["suggested_reply"].strip(),
    }


def analyze_inquiry_ai(text: str, api_key: str, model: str) -> dict[str, Any]:
    """Use OpenAI Structured Outputs. Exceptions are handled by the caller."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key, timeout=25.0)
    prompt = (
        "Analyze this English B2B export inquiry. Extract only facts explicitly stated. "
        "Use null for anything not mentioned; never guess. Risks and questions should be concise. "
        "The suggested reply must be professional natural English.\n\n"
        f"INQUIRY:\n{text.strip()}"
    )
    response = client.responses.create(
        model=model,
        input=prompt,
        store=False,
        text={
            "format": {
                "type": "json_schema",
                "name": "export_inquiry_analysis",
                "schema": ANALYSIS_SCHEMA,
                "strict": True,
            }
        },
    )
    return validate_analysis(json.loads(response.output_text))


def analyze_inquiry(text: str, api_key: str | None = None, model: str = "gpt-5-mini") -> AnalysisRun:
    """Prefer AI when configured and safely fall back to rules."""
    cleaned = str(text or "").strip()
    if not cleaned:
        raise ValueError("Inquiry text is required.")
    if len(cleaned) > 20_000:
        raise ValueError("Inquiry text cannot exceed 20,000 characters.")
    if api_key:
        try:
            return AnalysisRun(
                result=analyze_inquiry_ai(cleaned, api_key, model),
                mode="AI",
                notice="Structured AI analysis completed.",
            )
        except Exception as exc:  # External API failures must not break the app.
            return AnalysisRun(
                result=analyze_inquiry_rules(cleaned),
                mode="Rule fallback",
                notice=f"AI analysis failed; rule analysis was used instead ({type(exc).__name__}).",
            )
    return AnalysisRun(
        result=analyze_inquiry_rules(cleaned),
        mode="Rule",
        notice="OPENAI_API_KEY is not configured; deterministic rule analysis is active.",
    )
