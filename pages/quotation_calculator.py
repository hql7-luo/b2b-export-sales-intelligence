"""Database-backed export quotation preparation and persistence."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pandas as pd
import streamlit as st

from components.theme import page_header
from components.workflow import update_workflow_context, workflow_rail
from database.repository import list_inquiries, list_quotations
from services.excel_service import quotation_to_excel
from services.quotation import calculate_quotation
from services.workflow import build_quotation_context, save_quotation_for_inquiry
from utils.constants import INCOTERM_DESCRIPTIONS
from utils.i18n import localize_error, t, tr


INCOTERM_DESCRIPTIONS_ZH = {
    "EXW": "产品 + 包装",
    "FOB": "EXW + 国内运输 + 出口费用",
    "CIF": "FOB + 国际运费 + 保险",
    "DDP": "CIF + 目的国关税与税费",
}


def _term_description(term: str) -> str:
    return tr(INCOTERM_DESCRIPTIONS[term], INCOTERM_DESCRIPTIONS_ZH[term])


page_header(
    t("page.quotation.title"),
    t("page.quotation.subtitle"),
    t("page.quotation.section"),
)
workflow_rail("prepare")

st.markdown(
    f"""
    <div class="formula-note">
      <strong>{t("quotation.formula.margin.title")}</strong> —
      {t("quotation.formula.margin.text")}<br>
      <strong>{t("quotation.formula.markup.title")}</strong> —
      {t("quotation.formula.markup.text")}<br>
      {t("quotation.formula.caption")}
    </div>
    """,
    unsafe_allow_html=True,
)

calculator_tab, records_tab = st.tabs(
    [t("quotation.tab.create"), t("quotation.tab.saved")]
)

with calculator_tab:
    workflow_context = st.session_state.get("workflow_context", {})
    selected_inquiry_id = workflow_context.get("inquiry_id")
    eligible_inquiries = [
        inquiry
        for inquiry in list_inquiries()
        if inquiry.get("customer_id")
        and inquiry.get("matched_product_id")
        and inquiry.get("quantity")
    ]
    inquiry_by_id = {row["id"]: row for row in eligible_inquiries}
    if selected_inquiry_id not in inquiry_by_id:
        selected_inquiry_id = None

    if selected_inquiry_id is None and eligible_inquiries:
        st.info(t("quotation.source.info"))
        source_options = {
            (
                f"#{inquiry['id']} · {inquiry.get('product') or '—'} · "
                f"{inquiry.get('destination') or '—'}"
            ): inquiry["id"]
            for inquiry in eligible_inquiries
        }
        selected_source = st.selectbox(
            t("quotation.source.select"),
            list(source_options),
            key="quotation_source_inquiry",
        )
        selected_inquiry_id = source_options[selected_source]
        if st.button(
            t("quotation.source.load"),
            type="primary",
            key="quotation_source_load",
        ):
            update_workflow_context(
                stage="prepare",
                inquiry_id=selected_inquiry_id,
                customer_id=inquiry_by_id[selected_inquiry_id]["customer_id"],
                product_id=inquiry_by_id[selected_inquiry_id][
                    "matched_product_id"
                ],
            )
            for key in (
                "quotation_result",
                "quotation_metadata",
                "saved_quotation_id",
            ):
                st.session_state.pop(key, None)
            st.rerun()

    if selected_inquiry_id is None:
        st.warning(t("quotation.source.empty"))
        if st.button(t("quotation.action.return_inquiry"), key="quote_empty_return"):
            st.switch_page("pages/inquiry_analyzer.py")
    else:
        try:
            inherited = build_quotation_context(selected_inquiry_id)
        except ValueError as exc:
            st.error(localize_error(str(exc)))
            inherited = None

        if inherited:
            update_workflow_context(
                stage="prepare",
                customer_id=inherited["customer_id"],
                customer_name=inherited["customer_name"],
                country=inherited["country"],
                inquiry_id=inherited["inquiry_id"],
                product_id=inherited["product_id"],
                product=inherited["product_name"],
                quantity=inherited["quantity_text"],
                specification=inherited["specification"],
                destination=inherited["destination"],
            )
            st.subheader(t("quotation.context.title"))
            st.caption(t("quotation.context.caption"))
            context_frame = pd.DataFrame(
                [
                    {
                        t("quotation.context.field"): t(
                            f"quotation.context.{field}"
                        ),
                        t("quotation.context.value"): value or "—",
                    }
                    for field, value in (
                        ("customer", inherited["customer_name"]),
                        ("inquiry", f"#{inherited['inquiry_id']}"),
                        ("product", inherited["product_name"]),
                        ("quantity", inherited["quantity_text"]),
                        ("specification", inherited["specification"]),
                        ("destination", inherited["destination"]),
                    )
                ]
            )
            st.dataframe(context_frame, width="stretch", hide_index=True)
            if inherited.get("unit_cost") is not None:
                st.caption(
                    t(
                        "quotation.context.product_reference",
                        cost=f"{inherited['unit_cost']:,.2f}",
                        moq=inherited.get("moq") or "—",
                    )
                )

            with st.form("quotation_form"):
                st.subheader(t("quotation.cost.title"))
                cost_columns = st.columns(3)
                product_cost = cost_columns[0].number_input(
                    t("quotation.cost.product"),
                    min_value=0.0,
                    value=float(inherited.get("unit_cost") or 0),
                    step=0.10,
                    key="quote_product_cost",
                )
                packaging_cost = cost_columns[1].number_input(
                    t("quotation.cost.packaging"),
                    min_value=0.0,
                    value=0.0,
                    step=0.10,
                    key="quote_packaging_cost",
                )
                domestic = cost_columns[2].number_input(
                    t("quotation.cost.domestic"),
                    min_value=0.0,
                    value=0.0,
                    step=50.0,
                    key="quote_domestic",
                )
                export_handling = cost_columns[0].number_input(
                    t("quotation.cost.export"),
                    min_value=0.0,
                    value=0.0,
                    step=50.0,
                    key="quote_export",
                )
                freight = cost_columns[1].number_input(
                    t("quotation.cost.freight"),
                    min_value=0.0,
                    value=0.0,
                    step=100.0,
                    key="quote_freight",
                )
                insurance = cost_columns[2].number_input(
                    t("quotation.cost.insurance"),
                    min_value=0.0,
                    value=0.0,
                    step=10.0,
                    key="quote_insurance",
                )

                method_col, rate_col, term_col = st.columns(3)
                pricing_values = {
                    "gross_margin": t("quotation.pricing.gross_margin"),
                    "markup": t("quotation.pricing.markup"),
                }
                existing_pricing_label = st.session_state.get(
                    "quote_pricing_method_label"
                )
                current_pricing_method = next(
                    (
                        value
                        for value, label in pricing_values.items()
                        if label == existing_pricing_label
                    ),
                    st.session_state.get(
                        "quote_pricing_method_value",
                        "gross_margin",
                    ),
                )
                st.session_state["quote_pricing_method_label"] = pricing_values[
                    current_pricing_method
                ]
                selected_pricing_label = method_col.radio(
                    t("quotation.pricing.method"),
                    list(pricing_values.values()),
                    key="quote_pricing_method_label",
                )
                pricing_method = next(
                    value
                    for value, label in pricing_values.items()
                    if label == selected_pricing_label
                )
                st.session_state["quote_pricing_method_value"] = pricing_method
                rate_percent = rate_col.number_input(
                    t(
                        "quotation.pricing.rate_margin"
                        if pricing_method == "gross_margin"
                        else "quotation.pricing.rate_markup"
                    ),
                    min_value=0.0,
                    max_value=95.0 if pricing_method == "gross_margin" else 500.0,
                    value=25.0,
                    step=1.0,
                    key="quote_pricing_rate",
                )
                selected_term = term_col.selectbox(
                    t("quotation.terms.incoterm"),
                    ["EXW", "FOB", "CIF", "DDP"],
                    index=2,
                    key="quote_incoterm",
                )
                detail_columns = st.columns(2)
                payment_terms = detail_columns[0].text_input(
                    t("quotation.terms.payment"),
                    value=t("quotation.terms.payment_default"),
                    key="quote_payment_terms",
                )
                valid_until = detail_columns[1].date_input(
                    t("quotation.terms.valid_until"),
                    value=date.today() + timedelta(days=30),
                    key="quote_valid_until",
                )
                calculate = st.form_submit_button(
                    t("quotation.action.calculate"),
                    type="primary",
                )

            if calculate:
                try:
                    result = calculate_quotation(
                        product_unit_cost_cny=product_cost,
                        packaging_unit_cost_cny=packaging_cost,
                        quantity=inherited["quantity"],
                        domestic_transport_cny=domestic,
                        export_handling_cny=export_handling,
                        international_freight_cny=freight,
                        insurance_cny=insurance,
                        tariff_tax_cny=0,
                        platform_bank_fee_cny=0,
                        exchange_rate_cny_per_usd=7.2,
                        pricing_rate=Decimal(str(rate_percent))
                        / Decimal("100"),
                        pricing_method=pricing_method,
                    )
                    st.session_state["quotation_result"] = result
                    st.session_state["quotation_metadata"] = {
                        "inquiry_id": inherited["inquiry_id"],
                        "product_name": inherited["product_name"],
                        "specification": inherited["specification"],
                        "destination": inherited["destination"],
                        "selected_term": selected_term,
                        "valid_until": valid_until.isoformat(),
                        "moq": inherited.get("moq"),
                        "lead_time": inherited.get("production_lead_time"),
                        "payment_terms": payment_terms,
                        "notes": "",
                        "costs": {
                            "unit_product_cost": product_cost,
                            "packaging_cost": packaging_cost,
                            "domestic_transportation_cost": domestic,
                            "export_handling_cost": export_handling,
                            "international_freight": freight,
                            "insurance_cost": insurance,
                        },
                    }
                    st.session_state.pop("saved_quotation_id", None)
                except ValueError as exc:
                    st.error(localize_error(str(exc)))

            result = st.session_state.get("quotation_result")
            metadata = st.session_state.get("quotation_metadata")
            if (
                result
                and metadata
                and metadata.get("inquiry_id") == inherited["inquiry_id"]
            ):
                st.subheader(
                    t(
                        "quotation.result.title",
                        method=t(
                            f"quotation.pricing.{result['pricing_method']}"
                        ),
                    )
                )
                formula_key = (
                    "quotation.formula.margin.text"
                    if result["pricing_method"] == "gross_margin"
                    else "quotation.formula.markup.text"
                )
                st.caption(
                    t(
                        "quotation.result.caption",
                        formula=t(formula_key),
                        exchange=result["exchange_rate_cny_per_usd"],
                    )
                )
                rows = [
                    {
                        "Incoterm": term,
                        "Included costs": _term_description(term),
                        "Cost CNY": float(values["cost_total_cny"]),
                        "Quote USD": float(values["total_usd"]),
                        "Unit USD": float(values["unit_usd"]),
                        "Gross Profit USD": float(values["gross_profit_usd"]),
                        "Gross Margin %": float(values["gross_margin"] * 100),
                    }
                    for term, values in result["terms"].items()
                ]
                st.dataframe(
                    pd.DataFrame(rows),
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Incoterm": t("quotation.result.incoterm"),
                        "Included costs": t("quotation.result.included"),
                        "Cost CNY": st.column_config.NumberColumn(
                            t("quotation.result.cost"),
                            format="¥ %.2f",
                        ),
                        "Quote USD": st.column_config.NumberColumn(
                            t("quotation.result.quote"),
                            format="$ %.2f",
                        ),
                        "Unit USD": st.column_config.NumberColumn(
                            t("quotation.result.unit"),
                            format="$ %.4f",
                        ),
                        "Gross Profit USD": st.column_config.NumberColumn(
                            t("quotation.result.profit"),
                            format="$ %.2f",
                        ),
                        "Gross Margin %": st.column_config.NumberColumn(
                            t("quotation.result.margin"),
                            format="%.2f%%",
                        ),
                    },
                )
                chosen = result["terms"][metadata["selected_term"]]
                summary_columns = st.columns(4)
                summary_columns[0].metric(
                    t("quotation.summary.term"),
                    metadata["selected_term"],
                )
                summary_columns[1].metric(
                    t("quotation.summary.total"),
                    f"${chosen['total_usd']:,.2f}",
                )
                summary_columns[2].metric(
                    t("quotation.summary.unit"),
                    f"${chosen['unit_usd']:,.4f}",
                )
                summary_columns[3].metric(
                    t("quotation.summary.profit"),
                    f"${chosen['gross_profit_usd']:,.2f}",
                )

                save_column, export_column = st.columns(2)
                if save_column.button(
                    t("quotation.action.save"),
                    type="primary",
                    width="stretch",
                    disabled=bool(st.session_state.get("saved_quotation_id")),
                    key="save_quotation_record",
                ):
                    record = {
                        **metadata["costs"],
                        "incoterm": metadata["selected_term"],
                        "pricing_method": result["pricing_method"],
                        "pricing_rate": float(result["pricing_rate"]),
                        "exchange_rate": float(
                            result["exchange_rate_cny_per_usd"]
                        ),
                        "tariff_and_tax": 0,
                        "platform_or_bank_fee": 0,
                        "total_cost_cny": float(chosen["cost_total_cny"]),
                        "total_quote_usd": float(chosen["total_usd"]),
                        "unit_quote_usd": float(chosen["unit_usd"]),
                        "gross_profit_usd": float(chosen["gross_profit_usd"]),
                        "gross_margin": float(chosen["gross_margin"]),
                        "valid_until": metadata["valid_until"],
                        "payment_terms": metadata["payment_terms"],
                        "calculation_json": result,
                    }
                    try:
                        quotation_id = save_quotation_for_inquiry(
                            inherited["inquiry_id"],
                            record,
                        )
                        st.session_state["saved_quotation_id"] = quotation_id
                        update_workflow_context(
                            stage="follow_up",
                            quotation_id=quotation_id,
                        )
                        st.success(
                            t(
                                "quotation.save.success",
                                quotation_id=quotation_id,
                            )
                        )
                    except (TypeError, ValueError) as exc:
                        st.error(localize_error(str(exc)))

                export_bytes = quotation_to_excel(result, metadata)
                export_column.download_button(
                    t("quotation.action.export"),
                    data=export_bytes,
                    file_name="fictional_export_quotation.xlsx",
                    mime=(
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                    width="stretch",
                )

                if st.session_state.get("saved_quotation_id"):
                    st.subheader(t("quotation.next.title"))
                    follow_column, inquiry_column, customer_column = st.columns(3)
                    if follow_column.button(
                        t("quotation.action.follow_up"),
                        type="primary",
                        width="stretch",
                        key="quotation_add_follow_up",
                    ):
                        st.switch_page("pages/follow_up_tracker.py")
                    if inquiry_column.button(
                        t("quotation.action.return_inquiry"),
                        width="stretch",
                        key="quotation_return_inquiry",
                    ):
                        st.switch_page("pages/inquiry_analyzer.py")
                    if customer_column.button(
                        t("quotation.action.customer_timeline"),
                        width="stretch",
                        key="quotation_customer_timeline",
                    ):
                        st.switch_page("pages/customers.py")

with records_tab:
    records = list_quotations()
    if records:
        frame = pd.DataFrame(records)
        columns = [
            column
            for column in (
                "id",
                "quotation_date",
                "customer_id",
                "inquiry_id",
                "product_name",
                "quantity",
                "incoterm",
                "total_quote_usd",
                "valid_until",
            )
            if column in frame.columns
        ]
        st.dataframe(frame[columns], width="stretch", hide_index=True)
    else:
        st.info(t("quotation.saved.empty"))
