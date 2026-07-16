"""Pure, deterministic export quotation calculations.

All costs are entered in CNY.  Product and packaging inputs are unit costs;
logistics, tax, and transaction inputs are costs for the whole quotation.
The exchange rate is expressed as ``1 USD = X CNY``.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import TypeAlias


Number: TypeAlias = Decimal | int | float | str

MONEY_PLACES = Decimal("0.01")
RATE_PLACES = Decimal("0.0001")
ZERO = Decimal("0")

PRICING_DETAILS = {
    "gross_margin": {
        "label": "Gross Margin",
        "formula": "sale = cost / (1 - rate)",
    },
    "markup": {
        "label": "Markup",
        "formula": "sale = cost * (1 + rate)",
    },
}


def _decimal(value: Number, field_name: str) -> Decimal:
    """Convert a supported value to a finite Decimal with a clear error."""
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a finite number.") from exc
    if not number.is_finite():
        raise ValueError(f"{field_name} must be a finite number.")
    return number


def _nonnegative(value: Number, field_name: str) -> Decimal:
    number = _decimal(value, field_name)
    if number < ZERO:
        raise ValueError(f"{field_name} cannot be negative.")
    return number


def _positive_quantity(value: Number) -> int:
    quantity = _decimal(value, "quantity")
    if quantity <= ZERO or quantity != quantity.to_integral_value():
        raise ValueError("quantity must be a positive integer.")
    return int(quantity)


def _money(value: Decimal) -> Decimal:
    """Round money to two decimal places using commercial half-up rounding."""
    return value.quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def _rate(value: Decimal) -> Decimal:
    return value.quantize(RATE_PLACES, rounding=ROUND_HALF_UP)


def _sale_total(
    cost_total: Decimal,
    pricing_method: str,
    pricing_rate: Decimal,
) -> Decimal:
    if pricing_method == "gross_margin":
        return cost_total / (Decimal("1") - pricing_rate)
    return cost_total * (Decimal("1") + pricing_rate)


def _term_result(
    components: dict[str, Decimal],
    *,
    quantity: int,
    exchange_rate: Decimal,
    pricing_method: str,
    pricing_rate: Decimal,
) -> dict[str, object]:
    # Round each visible component first so the displayed ledger always
    # reconciles exactly to the displayed cost total.
    rounded_components = {
        name: _money(amount) for name, amount in components.items()
    }
    cost_total = sum(rounded_components.values(), start=ZERO)
    sale_total = _sale_total(cost_total, pricing_method, pricing_rate)
    gross_profit = sale_total - cost_total
    actual_gross_margin = (
        gross_profit / sale_total if sale_total != ZERO else ZERO
    )

    return {
        "components_cny": rounded_components,
        "components_usd": {
            name: _money(amount / exchange_rate)
            for name, amount in rounded_components.items()
        },
        "cost_total_cny": _money(cost_total),
        "cost_total_usd": _money(cost_total / exchange_rate),
        "total_cny": _money(sale_total),
        "total_usd": _money(sale_total / exchange_rate),
        "unit_cny": _money(sale_total / quantity),
        "unit_usd": _money(sale_total / exchange_rate / quantity),
        "gross_profit_cny": _money(gross_profit),
        "gross_profit_usd": _money(gross_profit / exchange_rate),
        "gross_margin": _rate(actual_gross_margin),
    }


def calculate_quotation(
    *,
    product_unit_cost_cny: Number,
    quantity: Number,
    packaging_unit_cost_cny: Number = 0,
    domestic_transport_cny: Number = 0,
    export_handling_cny: Number = 0,
    international_freight_cny: Number = 0,
    insurance_cny: Number = 0,
    tariff_tax_cny: Number = 0,
    platform_bank_fee_cny: Number = 0,
    exchange_rate_cny_per_usd: Number = "7.20",
    pricing_rate: Number = "0.20",
    pricing_method: str = "gross_margin",
) -> dict[str, object]:
    """Calculate EXW, FOB, CIF, and DDP quotations.

    ``gross_margin`` is the default and uses ``cost / (1 - rate)``. ``markup``
    uses ``cost * (1 + rate)``. Rates are decimal ratios, so 20% is ``0.20``.
    The platform/bank fee is a fixed transaction cost included in every term.
    """
    method = str(pricing_method).strip().lower()
    if method not in PRICING_DETAILS:
        raise ValueError("pricing method must be 'gross_margin' or 'markup'.")

    quantity_value = _positive_quantity(quantity)
    exchange_rate = _decimal(
        exchange_rate_cny_per_usd,
        "exchange rate",
    )
    if exchange_rate <= ZERO:
        raise ValueError("exchange rate must be greater than zero.")

    target_rate = _decimal(pricing_rate, f"{method.replace('_', ' ')} rate")
    if method == "gross_margin" and not ZERO <= target_rate < Decimal("1"):
        raise ValueError(
            "gross margin rate must be at least 0 and below 1."
        )
    if method == "markup" and target_rate < ZERO:
        raise ValueError("markup rate cannot be negative.")

    costs = {
        "product": _nonnegative(product_unit_cost_cny, "product unit cost")
        * quantity_value,
        "packaging": _nonnegative(
            packaging_unit_cost_cny,
            "packaging unit cost",
        )
        * quantity_value,
        "platform_bank_fee": _nonnegative(
            platform_bank_fee_cny,
            "platform/bank fee",
        ),
        "domestic_transport": _nonnegative(
            domestic_transport_cny,
            "domestic transportation cost",
        ),
        "export_handling": _nonnegative(
            export_handling_cny,
            "export handling cost",
        ),
        "international_freight": _nonnegative(
            international_freight_cny,
            "international freight",
        ),
        "insurance": _nonnegative(insurance_cny, "insurance cost"),
        "tariff_tax": _nonnegative(tariff_tax_cny, "tariff and tax"),
    }

    common = {
        "product": costs["product"],
        "packaging": costs["packaging"],
        "platform_bank_fee": costs["platform_bank_fee"],
    }
    components_by_term = {
        "EXW": common,
        "FOB": {
            **common,
            "domestic_transport": costs["domestic_transport"],
            "export_handling": costs["export_handling"],
        },
        "CIF": {
            **common,
            "domestic_transport": costs["domestic_transport"],
            "export_handling": costs["export_handling"],
            "international_freight": costs["international_freight"],
            "insurance": costs["insurance"],
        },
        "DDP": {
            **common,
            "domestic_transport": costs["domestic_transport"],
            "export_handling": costs["export_handling"],
            "international_freight": costs["international_freight"],
            "insurance": costs["insurance"],
            "tariff_tax": costs["tariff_tax"],
        },
    }

    details = PRICING_DETAILS[method]
    return {
        "pricing_method": method,
        "pricing_method_label": details["label"],
        "formula": details["formula"],
        "pricing_rate": target_rate,
        "exchange_rate_cny_per_usd": exchange_rate,
        "quantity": quantity_value,
        "terms": {
            incoterm: _term_result(
                components,
                quantity=quantity_value,
                exchange_rate=exchange_rate,
                pricing_method=method,
                pricing_rate=target_rate,
            )
            for incoterm, components in components_by_term.items()
        },
    }


__all__ = ["calculate_quotation"]
