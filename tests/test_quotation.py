"""Unit tests for the pure quotation calculation service."""

from decimal import Decimal

import pytest

from services.quotation import calculate_quotation


@pytest.fixture
def quotation_inputs() -> dict[str, object]:
    """A fully populated, deterministic quotation in CNY."""
    return {
        "product_unit_cost_cny": "10",
        "packaging_unit_cost_cny": "2",
        "quantity": 10,
        "domestic_transport_cny": "20",
        "export_handling_cny": "10",
        "international_freight_cny": "30",
        "insurance_cny": "5",
        "tariff_tax_cny": "15",
        "platform_bank_fee_cny": "4",
        "exchange_rate_cny_per_usd": "2",
        "pricing_rate": "0.20",
    }


def test_gross_margin_calculates_all_incoterms(
    quotation_inputs: dict[str, object],
) -> None:
    result = calculate_quotation(**quotation_inputs)

    assert result["pricing_method"] == "gross_margin"
    assert result["pricing_method_label"] == "Gross Margin"
    assert result["formula"] == "sale = cost / (1 - rate)"
    assert list(result["terms"]) == ["EXW", "FOB", "CIF", "DDP"]

    expected = {
        "EXW": ("124.00", "155.00", "77.50", "15.50", "31.00"),
        "FOB": ("154.00", "192.50", "96.25", "19.25", "38.50"),
        "CIF": ("189.00", "236.25", "118.13", "23.63", "47.25"),
        "DDP": ("204.00", "255.00", "127.50", "25.50", "51.00"),
    }
    for incoterm, values in expected.items():
        cost_cny, total_cny, total_usd, unit_cny, profit_cny = map(
            Decimal, values
        )
        term = result["terms"][incoterm]
        assert term["cost_total_cny"] == cost_cny
        assert term["total_cny"] == total_cny
        assert term["total_usd"] == total_usd
        assert term["unit_cny"] == unit_cny
        assert term["gross_profit_cny"] == profit_cny
        assert term["gross_margin"] == Decimal("0.2000")


def test_cost_components_are_transparent_and_cumulative(
    quotation_inputs: dict[str, object],
) -> None:
    terms = calculate_quotation(**quotation_inputs)["terms"]

    assert terms["EXW"]["components_cny"] == {
        "product": Decimal("100.00"),
        "packaging": Decimal("20.00"),
        "platform_bank_fee": Decimal("4.00"),
    }
    assert set(terms["FOB"]["components_cny"]) == {
        "product",
        "packaging",
        "platform_bank_fee",
        "domestic_transport",
        "export_handling",
    }
    assert set(terms["CIF"]["components_cny"]) == {
        *terms["FOB"]["components_cny"],
        "international_freight",
        "insurance",
    }
    assert set(terms["DDP"]["components_cny"]) == {
        *terms["CIF"]["components_cny"],
        "tariff_tax",
    }
    for term in terms.values():
        assert term["components_cny"]["platform_bank_fee"] == Decimal("4.00")
        assert sum(term["components_cny"].values()) == term["cost_total_cny"]


def test_components_are_also_converted_to_usd(
    quotation_inputs: dict[str, object],
) -> None:
    exw = calculate_quotation(**quotation_inputs)["terms"]["EXW"]

    assert exw["components_usd"] == {
        "product": Decimal("50.00"),
        "packaging": Decimal("10.00"),
        "platform_bank_fee": Decimal("2.00"),
    }
    assert exw["cost_total_usd"] == Decimal("62.00")
    assert exw["unit_usd"] == Decimal("7.75")
    assert exw["gross_profit_usd"] == Decimal("15.50")


def test_markup_uses_cost_times_one_plus_rate(
    quotation_inputs: dict[str, object],
) -> None:
    quotation_inputs["pricing_method"] = "markup"
    quotation_inputs["pricing_rate"] = "0.25"

    result = calculate_quotation(**quotation_inputs)
    exw = result["terms"]["EXW"]

    assert result["pricing_method_label"] == "Markup"
    assert result["formula"] == "sale = cost * (1 + rate)"
    assert exw["total_cny"] == Decimal("155.00")
    assert exw["gross_profit_cny"] == Decimal("31.00")
    assert exw["gross_margin"] == Decimal("0.2000")


def test_default_method_is_gross_margin_not_markup(
    quotation_inputs: dict[str, object],
) -> None:
    quotation_inputs["pricing_rate"] = "0.25"

    result = calculate_quotation(**quotation_inputs)

    assert result["pricing_method"] == "gross_margin"
    assert result["terms"]["EXW"]["total_cny"] == Decimal("165.33")


def test_money_rounding_is_half_up() -> None:
    result = calculate_quotation(
        product_unit_cost_cny="0.335",
        quantity=3,
        pricing_rate=0,
        exchange_rate_cny_per_usd=1,
    )
    exw = result["terms"]["EXW"]

    assert exw["components_cny"]["product"] == Decimal("1.01")
    assert exw["cost_total_cny"] == Decimal("1.01")
    assert exw["total_cny"] == Decimal("1.01")
    assert exw["total_usd"] == Decimal("1.01")
    assert exw["unit_cny"] == Decimal("0.34")
    assert exw["gross_profit_cny"] == Decimal("0.00")


def test_visible_components_reconcile_after_individual_rounding() -> None:
    result = calculate_quotation(
        product_unit_cost_cny="0.005",
        packaging_unit_cost_cny="0.005",
        quantity=1,
        pricing_rate=0,
        exchange_rate_cny_per_usd=1,
    )
    exw = result["terms"]["EXW"]

    assert exw["components_cny"]["product"] == Decimal("0.01")
    assert exw["components_cny"]["packaging"] == Decimal("0.01")
    assert sum(exw["components_cny"].values()) == exw["cost_total_cny"]
    assert exw["cost_total_cny"] == Decimal("0.02")


@pytest.mark.parametrize(
    "field",
    [
        "product_unit_cost_cny",
        "packaging_unit_cost_cny",
        "domestic_transport_cny",
        "export_handling_cny",
        "international_freight_cny",
        "insurance_cny",
        "tariff_tax_cny",
        "platform_bank_fee_cny",
    ],
)
def test_rejects_negative_costs(field: str) -> None:
    inputs: dict[str, object] = {
        "product_unit_cost_cny": 1,
        "quantity": 1,
        field: -1,
    }

    with pytest.raises(ValueError, match="cannot be negative"):
        calculate_quotation(**inputs)


@pytest.mark.parametrize("value", ["not-a-number", "NaN", "Infinity"])
def test_rejects_invalid_numeric_values(value: str) -> None:
    with pytest.raises(ValueError, match="must be a finite number"):
        calculate_quotation(product_unit_cost_cny=value, quantity=1)


@pytest.mark.parametrize("quantity", [0, -1, Decimal("1.5")])
def test_quantity_must_be_a_positive_integer(quantity: object) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        calculate_quotation(product_unit_cost_cny=1, quantity=quantity)


@pytest.mark.parametrize("exchange_rate", [0, -1])
def test_exchange_rate_must_be_positive(exchange_rate: object) -> None:
    with pytest.raises(ValueError, match="exchange rate must be greater than zero"):
        calculate_quotation(
            product_unit_cost_cny=1,
            quantity=1,
            exchange_rate_cny_per_usd=exchange_rate,
        )


@pytest.mark.parametrize("rate", [-1, 1, "1.25"])
def test_gross_margin_rate_must_be_between_zero_and_one(rate: object) -> None:
    with pytest.raises(ValueError, match="gross margin rate must be at least 0 and below 1"):
        calculate_quotation(
            product_unit_cost_cny=1,
            quantity=1,
            pricing_rate=rate,
        )


def test_markup_rate_cannot_be_negative() -> None:
    with pytest.raises(ValueError, match="markup rate cannot be negative"):
        calculate_quotation(
            product_unit_cost_cny=1,
            quantity=1,
            pricing_method="markup",
            pricing_rate=-1,
        )


def test_rejects_unknown_pricing_method() -> None:
    with pytest.raises(ValueError, match="pricing method must be"):
        calculate_quotation(
            product_unit_cost_cny=1,
            quantity=1,
            pricing_method="margin",
        )
