"""轻量输入验证，避免无效数据进入业务层。"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
URL_PATTERN = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)


def is_valid_email(value: str | None) -> bool:
    """Allow an empty email, otherwise require a basic valid structure."""
    return not value or bool(EMAIL_PATTERN.match(value.strip()))


def is_valid_url(value: str | None) -> bool:
    """Allow an empty website, otherwise require http/https."""
    return not value or bool(URL_PATTERN.match(value.strip()))


def required_text(value: Any, field_name: str) -> str:
    """Return trimmed required text or raise a user-friendly error."""
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required.")
    return text


def nonnegative_decimal(value: Any, field_name: str) -> Decimal:
    """Convert numeric input to a non-negative Decimal."""
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number.") from exc
    if not number.is_finite():
        raise ValueError(f"{field_name} must be a finite number.")
    if number < 0:
        raise ValueError(f"{field_name} cannot be negative.")
    return number


def normalize_date(value: Any) -> str | None:
    """Normalize date-like values to ISO format for SQLite."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return date.fromisoformat(str(value)[:10]).isoformat()
