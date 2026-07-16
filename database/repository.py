"""Small parameterized-SQL repository for application persistence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from database.connection import get_connection
from database.init_db import initialize_database
from services.scoring import grade_for_score, score_customer


CUSTOMER_FIELDS = {
    "company_name",
    "contact_name",
    "job_title",
    "country",
    "website",
    "email",
    "phone",
    "lead_source",
    "product_interest",
    "import_frequency",
    "estimated_purchase_volume",
    "last_contact_date",
    "next_follow_up_date",
    "current_stage",
    "lead_grade",
    "auto_score",
    "auto_grade",
    "score_breakdown",
    "score_reasons",
    "manual_score",
    "manual_grade",
    "score_override_reason",
    "score_overridden_at",
    "notes",
}

SCORING_INPUT_FIELDS = {
    "company_name",
    "website",
    "email",
    "phone",
    "product_interest",
    "import_frequency",
    "estimated_purchase_volume",
    "last_contact_date",
    "current_stage",
}

QUOTATION_FIELDS = {
    "customer_id",
    "inquiry_id",
    "product_id",
    "product_name",
    "specification",
    "destination",
    "quotation_date",
    "incoterm",
    "quantity",
    "unit_product_cost",
    "packaging_cost",
    "domestic_transportation_cost",
    "export_handling_cost",
    "international_freight",
    "insurance_cost",
    "tariff_and_tax",
    "platform_or_bank_fee",
    "exchange_rate",
    "pricing_method",
    "pricing_rate",
    "total_cost_cny",
    "unit_quote_usd",
    "total_quote_usd",
    "gross_profit_usd",
    "gross_margin",
    "valid_until",
    "moq",
    "lead_time",
    "payment_terms",
    "notes",
    "calculation_json",
}

FOLLOW_UP_FIELDS = {
    "customer_id",
    "inquiry_id",
    "quotation_id",
    "customer_stage",
    "follow_up_date",
    "communication_type",
    "content",
    "outcome",
    "next_follow_up_date",
    "priority",
}

PRODUCT_FIELDS = {
    "product_name",
    "category",
    "application",
    "material",
    "specification",
    "moq",
    "sample_lead_time",
    "production_lead_time",
    "packaging",
    "unit_cost",
    "common_customer_questions",
    "selling_points",
    "notes",
}


def _serialize_customer_value(field: str, value: Any) -> Any:
    if field in {"score_breakdown", "score_reasons"} and not isinstance(value, str):
        return json.dumps(value or {}, ensure_ascii=False)
    return value


def _json_default(value: Any) -> str:
    """Keep exact Decimal values readable in stored calculation evidence."""
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"{type(value).__name__} is not JSON serializable")


def _customer_from_row(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    customer = dict(row)
    for field in ("score_breakdown", "score_reasons"):
        try:
            customer[field] = json.loads(customer.get(field) or "{}")
        except (TypeError, json.JSONDecodeError):
            customer[field] = {}
    customer["effective_score"] = (
        customer["manual_score"]
        if customer.get("manual_score") is not None
        else customer["auto_score"]
    )
    customer["effective_grade"] = (
        customer.get("manual_grade") or customer["auto_grade"]
    )
    return customer


def _inquiry_from_row(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    inquiry = dict(row)
    for key in (
        "confirmed_info",
        "missing_info",
        "risks",
        "next_questions",
        "analysis_json",
    ):
        try:
            inquiry[key] = json.loads(
                inquiry.get(key) or ("{}" if key == "analysis_json" else "[]")
            )
        except (TypeError, json.JSONDecodeError):
            inquiry[key] = {} if key == "analysis_json" else []
    return inquiry


def _quotation_from_row(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    quotation = dict(row)
    try:
        quotation["calculation_json"] = json.loads(
            quotation.get("calculation_json") or "{}"
        )
    except (TypeError, json.JSONDecodeError):
        quotation["calculation_json"] = {}
    return quotation


def _scored_values(customer: Mapping[str, Any]) -> dict[str, Any]:
    result = score_customer(customer)
    return {
        "auto_score": result["total_score"],
        "auto_grade": result["grade"],
        "lead_grade": result["grade"],
        "score_breakdown": result["breakdown"],
        "score_reasons": result["dimension_reasons"],
    }


def create_customer(
    customer: Mapping[str, Any], db_path: str | Path | None = None
) -> int:
    """Create a customer, calculating its transparent automatic score."""
    if not str(customer.get("company_name") or "").strip():
        raise ValueError("company_name is required")
    initialize_database(db_path)
    normalized = dict(customer)
    if "phone" not in normalized and "phone_whatsapp" in normalized:
        normalized["phone"] = normalized["phone_whatsapp"]
    values = {key: value for key, value in normalized.items() if key in CUSTOMER_FIELDS}
    if "auto_score" not in values:
        values.update(_scored_values(values))
    else:
        values["auto_score"] = int(values["auto_score"])
        values["auto_grade"] = grade_for_score(values["auto_score"])
        values.setdefault("lead_grade", values.get("manual_grade") or values["auto_grade"])
    values = {key: _serialize_customer_value(key, value) for key, value in values.items()}
    fields = list(values)
    placeholders = ", ".join("?" for _ in fields)
    sql = f"INSERT INTO customers ({', '.join(fields)}) VALUES ({placeholders})"
    connection = get_connection(db_path)
    try:
        cursor = connection.execute(sql, tuple(values[field] for field in fields))
        customer_id = int(cursor.lastrowid)
        connection.execute(
            "INSERT INTO activities (customer_id, activity_type, description) "
            "VALUES (?, ?, ?)",
            (customer_id, "customer_saved", "Customer record saved"),
        )
        connection.commit()
        return customer_id
    finally:
        connection.close()


def create_customers_batch(
    customers: list[Mapping[str, Any]], db_path: str | Path | None = None
) -> list[int]:
    """Create a validated customer batch in one SQLite transaction."""
    prepared: list[dict[str, Any]] = []
    for customer in customers:
        if not str(customer.get("company_name") or "").strip():
            raise ValueError("company_name is required")
        normalized = dict(customer)
        if "phone" not in normalized and "phone_whatsapp" in normalized:
            normalized["phone"] = normalized["phone_whatsapp"]
        values = {
            key: value for key, value in normalized.items() if key in CUSTOMER_FIELDS
        }
        if "auto_score" not in values:
            values.update(_scored_values(values))
        else:
            values["auto_score"] = int(values["auto_score"])
            values["auto_grade"] = grade_for_score(values["auto_score"])
            values.setdefault(
                "lead_grade", values.get("manual_grade") or values["auto_grade"]
            )
        prepared.append(
            {
                key: _serialize_customer_value(key, value)
                for key, value in values.items()
            }
        )

    initialize_database(db_path)
    connection = get_connection(db_path)
    customer_ids: list[int] = []
    try:
        for values in prepared:
            fields = list(values)
            placeholders = ", ".join("?" for _ in fields)
            cursor = connection.execute(
                f"INSERT INTO customers ({', '.join(fields)}) VALUES ({placeholders})",
                tuple(values[field] for field in fields),
            )
            customer_id = int(cursor.lastrowid)
            customer_ids.append(customer_id)
            connection.execute(
                "INSERT INTO activities (customer_id, activity_type, description) "
                "VALUES (?, ?, ?)",
                (customer_id, "customer_saved", "Customer record imported"),
            )
        connection.commit()
        return customer_ids
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_customer(
    customer_id: int, db_path: str | Path | None = None
) -> dict[str, Any] | None:
    initialize_database(db_path)
    connection = get_connection(db_path)
    try:
        row = connection.execute(
            "SELECT * FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()
        return _customer_from_row(row)
    finally:
        connection.close()


def list_customers(
    *,
    search: str | None = None,
    grade: str | None = None,
    stage: str | None = None,
    country: str | None = None,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """List customers with optional parameterized business filters."""
    initialize_database(db_path)
    conditions: list[str] = []
    parameters: list[Any] = []
    if search:
        conditions.append(
            "(company_name LIKE ? OR contact_name LIKE ? OR email LIKE ? "
            "OR product_interest LIKE ?)"
        )
        pattern = f"%{search.strip()}%"
        parameters.extend([pattern] * 4)
    if grade:
        conditions.append("lead_grade = ?")
        parameters.append(grade)
    if stage:
        conditions.append("current_stage = ?")
        parameters.append(stage)
    if country:
        conditions.append("country = ?")
        parameters.append(country)
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    connection = get_connection(db_path)
    try:
        rows = connection.execute(
            f"SELECT * FROM customers{where} ORDER BY updated_at DESC, id DESC",
            tuple(parameters),
        ).fetchall()
        return [_customer_from_row(row) for row in rows]
    finally:
        connection.close()


def update_customer(
    customer_id: int,
    changes: Mapping[str, Any],
    db_path: str | Path | None = None,
) -> bool:
    """Update allowed fields and recalculate scoring inputs when needed."""
    current = get_customer(customer_id, db_path=db_path)
    if current is None:
        return False
    normalized = dict(changes)
    if "phone" not in normalized and "phone_whatsapp" in normalized:
        normalized["phone"] = normalized["phone_whatsapp"]
    values = {key: value for key, value in normalized.items() if key in CUSTOMER_FIELDS}
    if not values:
        return False
    merged = {**current, **values}
    if SCORING_INPUT_FIELDS.intersection(values) and "auto_score" not in values:
        values.update(_scored_values(merged))
        if current.get("manual_grade"):
            values["lead_grade"] = current["manual_grade"]
    elif "auto_score" in values:
        values["auto_score"] = int(values["auto_score"])
        values["auto_grade"] = grade_for_score(values["auto_score"])
        if not current.get("manual_grade"):
            values["lead_grade"] = values["auto_grade"]
    values = {key: _serialize_customer_value(key, value) for key, value in values.items()}
    assignments = ", ".join(f"{field} = ?" for field in values)
    parameters = [values[field] for field in values]
    parameters.append(customer_id)
    connection = get_connection(db_path)
    try:
        cursor = connection.execute(
            f"UPDATE customers SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            tuple(parameters),
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()


def delete_customer(customer_id: int, db_path: str | Path | None = None) -> bool:
    initialize_database(db_path)
    connection = get_connection(db_path)
    try:
        cursor = connection.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()


def set_manual_score(
    customer_id: int,
    score: int | None,
    reason: str | None = None,
    db_path: str | Path | None = None,
) -> bool:
    """Set or clear a human override while retaining the automatic score."""
    customer = get_customer(customer_id, db_path=db_path)
    if customer is None:
        return False
    if score is None:
        values = (None, None, None, None, customer["auto_grade"], customer_id)
    else:
        numeric_score = int(score)
        if numeric_score != score:
            raise ValueError("manual score must be a whole number")
        manual_grade = grade_for_score(numeric_score)
        if not str(reason or "").strip():
            raise ValueError("an override reason is required")
        overridden_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        values = (
            numeric_score,
            manual_grade,
            str(reason).strip(),
            overridden_at,
            manual_grade,
            customer_id,
        )
    connection = get_connection(db_path)
    try:
        cursor = connection.execute(
            "UPDATE customers SET manual_score = ?, manual_grade = ?, "
            "score_override_reason = ?, score_overridden_at = ?, lead_grade = ?, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            values,
        )
        if score is not None:
            connection.execute(
                "INSERT INTO activities "
                "(customer_id, activity_type, description, metadata) VALUES (?, ?, ?, ?)",
                (
                    customer_id,
                    "Score Override",
                    str(reason).strip(),
                    json.dumps(
                        {
                            "automatic_score": customer["auto_score"],
                            "manual_score": numeric_score,
                        }
                    ),
                ),
            )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()


def create_quotation(
    quotation: Mapping[str, Any], db_path: str | Path | None = None
) -> int:
    """Persist a calculated quotation using the page's documented payload."""
    if not str(quotation.get("product_name") or "").strip():
        raise ValueError("product_name is required")
    if str(quotation.get("incoterm") or "").upper() not in {"EXW", "FOB", "CIF", "DDP"}:
        raise ValueError("incoterm must be EXW, FOB, CIF, or DDP")
    try:
        if int(quotation.get("quantity", 0)) <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("quantity must be greater than zero") from None
    initialize_database(db_path)
    values = {
        key: value for key, value in quotation.items() if key in QUOTATION_FIELDS
    }
    values["incoterm"] = str(values["incoterm"]).upper()
    if "calculation_json" in values and not isinstance(values["calculation_json"], str):
        values["calculation_json"] = json.dumps(
            values["calculation_json"], ensure_ascii=False, default=_json_default
        )
    fields = list(values)
    placeholders = ", ".join("?" for _ in fields)
    connection = get_connection(db_path)
    try:
        cursor = connection.execute(
            f"INSERT INTO quotations ({', '.join(fields)}) VALUES ({placeholders})",
            tuple(values[field] for field in fields),
        )
        quotation_id = int(cursor.lastrowid)
        if values.get("customer_id") is not None:
            connection.execute(
                "INSERT INTO activities "
                "(customer_id, inquiry_id, quotation_id, activity_type, "
                "description, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    values["customer_id"],
                    values.get("inquiry_id"),
                    quotation_id,
                    "quotation_created",
                    f"{values['incoterm']} quotation created for {values['product_name']}",
                    json.dumps(
                        {
                            "quotation_id": quotation_id,
                            "product_id": values.get("product_id"),
                        }
                    ),
                ),
            )
            connection.execute(
                "UPDATE customers SET current_stage = 'Quoted', "
                "updated_at = CURRENT_TIMESTAMP "
                "WHERE id = ? AND current_stage NOT IN ('Order Confirmed', 'Lost')",
                (values["customer_id"],),
            )
        connection.commit()
        return quotation_id
    finally:
        connection.close()


def list_quotations(
    customer_id: int | None = None, db_path: str | Path | None = None
) -> list[dict[str, Any]]:
    """List saved quotations, optionally for one customer."""
    initialize_database(db_path)
    sql = "SELECT * FROM quotations"
    parameters: tuple[Any, ...] = ()
    if customer_id is not None:
        sql += " WHERE customer_id = ?"
        parameters = (customer_id,)
    sql += " ORDER BY quotation_date DESC, id DESC"
    connection = get_connection(db_path)
    try:
        records = [
            _quotation_from_row(row)
            for row in connection.execute(sql, parameters).fetchall()
        ]
    finally:
        connection.close()
    return records


def get_quotation(
    quotation_id: int, db_path: str | Path | None = None
) -> dict[str, Any] | None:
    """Return one quotation with its calculation evidence decoded."""
    initialize_database(db_path)
    connection = get_connection(db_path)
    try:
        row = connection.execute(
            "SELECT * FROM quotations WHERE id = ?",
            (quotation_id,),
        ).fetchone()
        return _quotation_from_row(row)
    finally:
        connection.close()


def create_inquiry(
    *,
    customer_id: int | None,
    raw_text: str,
    analysis: Mapping[str, Any],
    analysis_mode: str,
    matched_product_id: int | None = None,
    db_path: str | Path | None = None,
) -> int:
    """Persist the normalized inquiry-analysis contract."""
    if not str(raw_text or "").strip():
        raise ValueError("raw_text is required")
    fields = dict(analysis.get("extracted_fields") or {})
    values = {
        "customer_id": customer_id,
        "matched_product_id": matched_product_id,
        "raw_text": str(raw_text).strip(),
        **{key: fields.get(key) for key in (
            "product", "specification", "quantity", "application",
            "customization_requirement", "packaging_requirement", "destination",
            "required_delivery_time", "target_price", "sample_requirement",
            "payment_requirement",
        )},
        "confirmed_info": json.dumps(analysis.get("confirmed_info") or [], ensure_ascii=False),
        "missing_info": json.dumps(analysis.get("missing_info") or [], ensure_ascii=False),
        "risks": json.dumps(analysis.get("risks") or [], ensure_ascii=False),
        "next_questions": json.dumps(analysis.get("next_questions") or [], ensure_ascii=False),
        "completeness_score": int(analysis.get("completeness_score") or 0),
        "suggested_reply": analysis.get("suggested_reply") or "",
        "analysis_mode": str(analysis_mode or "rule").lower(),
        "analysis_json": json.dumps(dict(analysis), ensure_ascii=False),
    }
    columns = list(values)
    initialize_database(db_path)
    connection = get_connection(db_path)
    try:
        cursor = connection.execute(
            f"INSERT INTO inquiries ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
            tuple(values[column] for column in columns),
        )
        inquiry_id = int(cursor.lastrowid)
        if customer_id is not None:
            connection.execute(
                "INSERT INTO activities "
                "(customer_id, inquiry_id, activity_type, description, metadata) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    customer_id,
                    inquiry_id,
                    "inquiry_created",
                    f"Inquiry analyzed in {values['analysis_mode']} mode",
                    json.dumps({"inquiry_id": inquiry_id}),
                ),
            )
            if matched_product_id is not None:
                connection.execute(
                    "INSERT INTO activities "
                    "(customer_id, inquiry_id, activity_type, description, metadata) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        customer_id,
                        inquiry_id,
                        "product_matched",
                        "Product matched to inquiry",
                        json.dumps({"product_id": matched_product_id}),
                    ),
                )
        connection.commit()
        return inquiry_id
    finally:
        connection.close()


def list_inquiries(
    customer_id: int | None = None, db_path: str | Path | None = None
) -> list[dict[str, Any]]:
    """List saved analyses with decoded JSON fields."""
    initialize_database(db_path)
    sql = "SELECT * FROM inquiries"
    parameters: tuple[Any, ...] = ()
    if customer_id is not None:
        sql += " WHERE customer_id = ?"
        parameters = (customer_id,)
    sql += " ORDER BY inquiry_date DESC, id DESC"
    connection = get_connection(db_path)
    try:
        records = [
            _inquiry_from_row(row)
            for row in connection.execute(sql, parameters).fetchall()
        ]
    finally:
        connection.close()
    return records


def get_inquiry(
    inquiry_id: int, db_path: str | Path | None = None
) -> dict[str, Any] | None:
    """Return one persisted inquiry with decoded analysis fields."""
    initialize_database(db_path)
    connection = get_connection(db_path)
    try:
        row = connection.execute(
            "SELECT * FROM inquiries WHERE id = ?",
            (inquiry_id,),
        ).fetchone()
        return _inquiry_from_row(row)
    finally:
        connection.close()


def create_follow_up(
    follow_up: Mapping[str, Any], db_path: str | Path | None = None
) -> int:
    """Save a communication record and synchronize the customer's next action."""
    values = {key: value for key, value in follow_up.items() if key in FOLLOW_UP_FIELDS}
    if not values.get("customer_id"):
        raise ValueError("customer_id is required")
    if not str(values.get("follow_up_date") or "").strip():
        raise ValueError("follow_up_date is required")
    if not str(values.get("content") or "").strip():
        raise ValueError("content is required")
    initialize_database(db_path)
    columns = list(values)
    connection = get_connection(db_path)
    try:
        if not values.get("customer_stage"):
            row = connection.execute(
                "SELECT current_stage FROM customers WHERE id = ?",
                (values["customer_id"],),
            ).fetchone()
            values["customer_stage"] = row["current_stage"] if row else None
            columns = list(values)
        cursor = connection.execute(
            f"INSERT INTO follow_ups ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
            tuple(values[column] for column in columns),
        )
        follow_up_id = int(cursor.lastrowid)
        connection.execute(
            "UPDATE customers SET last_contact_date = ?, next_follow_up_date = ?, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (values["follow_up_date"], values.get("next_follow_up_date"), values["customer_id"]),
        )
        connection.execute(
            "INSERT INTO activities "
            "(customer_id, inquiry_id, quotation_id, activity_type, "
            "description, metadata) VALUES (?, ?, ?, ?, ?, ?)",
            (
                values["customer_id"],
                values.get("inquiry_id"),
                values.get("quotation_id"),
                "follow_up_scheduled",
                values["content"],
                json.dumps(
                    {
                        "follow_up_id": follow_up_id,
                        "follow_up_date": values["follow_up_date"],
                        "next_follow_up_date": values.get("next_follow_up_date"),
                        "outcome": values.get("outcome"),
                    }
                ),
            ),
        )
        connection.commit()
        return follow_up_id
    finally:
        connection.close()


def list_follow_ups(
    customer_id: int | None = None, db_path: str | Path | None = None
) -> list[dict[str, Any]]:
    """List communication history with customer context."""
    initialize_database(db_path)
    sql = (
        "SELECT f.*, c.company_name, c.contact_name, c.current_stage, c.lead_grade, "
        "c.product_interest FROM follow_ups f JOIN customers c ON c.id = f.customer_id"
    )
    parameters: tuple[Any, ...] = ()
    if customer_id is not None:
        sql += " WHERE f.customer_id = ?"
        parameters = (customer_id,)
    sql += " ORDER BY f.follow_up_date DESC, f.id DESC"
    connection = get_connection(db_path)
    try:
        return [dict(row) for row in connection.execute(sql, parameters).fetchall()]
    finally:
        connection.close()


def list_customer_timeline(
    customer_id: int, db_path: str | Path | None = None
) -> list[dict[str, Any]]:
    """Return a customer's auditable workflow events in creation order."""
    initialize_database(db_path)
    connection = get_connection(db_path)
    try:
        rows = connection.execute(
            "SELECT * FROM activities WHERE customer_id = ? "
            "ORDER BY activity_date ASC, id ASC",
            (customer_id,),
        ).fetchall()
    finally:
        connection.close()
    timeline = []
    for row in rows:
        event = dict(row)
        try:
            event["metadata"] = json.loads(event.get("metadata") or "{}")
        except (TypeError, json.JSONDecodeError):
            event["metadata"] = {}
        timeline.append(event)
    return timeline


def create_product(product: Mapping[str, Any], db_path: str | Path | None = None) -> int:
    """Create one product knowledge record."""
    values = {key: value for key, value in product.items() if key in PRODUCT_FIELDS}
    if not str(values.get("product_name") or "").strip():
        raise ValueError("product_name is required")
    columns = list(values)
    initialize_database(db_path)
    connection = get_connection(db_path)
    try:
        cursor = connection.execute(
            f"INSERT INTO products ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
            tuple(values[column] for column in columns),
        )
        connection.commit()
        return int(cursor.lastrowid)
    finally:
        connection.close()


def get_product(product_id: int, db_path: str | Path | None = None) -> dict[str, Any] | None:
    initialize_database(db_path)
    connection = get_connection(db_path)
    try:
        row = connection.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def list_products(
    *, search: str | None = None, category: str | None = None, db_path: str | Path | None = None
) -> list[dict[str, Any]]:
    """Search products using parameterized conditions."""
    conditions: list[str] = []
    parameters: list[Any] = []
    if search:
        conditions.append("(product_name LIKE ? OR application LIKE ? OR specification LIKE ? OR selling_points LIKE ?)")
        pattern = f"%{search.strip()}%"
        parameters.extend([pattern] * 4)
    if category:
        conditions.append("category = ?")
        parameters.append(category)
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    initialize_database(db_path)
    connection = get_connection(db_path)
    try:
        return [
            dict(row)
            for row in connection.execute(
                f"SELECT * FROM products{where} ORDER BY category, product_name", tuple(parameters)
            ).fetchall()
        ]
    finally:
        connection.close()


def update_product(
    product_id: int, changes: Mapping[str, Any], db_path: str | Path | None = None
) -> bool:
    values = {key: value for key, value in changes.items() if key in PRODUCT_FIELDS}
    if not values:
        return False
    assignments = ", ".join(f"{field} = ?" for field in values)
    connection = get_connection(db_path)
    try:
        cursor = connection.execute(
            f"UPDATE products SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (*[values[field] for field in values], product_id),
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()


def delete_product(product_id: int, db_path: str | Path | None = None) -> bool:
    connection = get_connection(db_path)
    try:
        cursor = connection.execute("DELETE FROM products WHERE id = ?", (product_id,))
        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()


# Friendly aliases for page code.
get_all_customers = list_customers
save_customer = create_customer
