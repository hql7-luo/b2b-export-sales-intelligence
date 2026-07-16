"""Transparent export quotation calculator and record export."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pandas as pd
import streamlit as st

from components.theme import operations_ledger, page_header
from database.repository import create_quotation, list_customers, list_quotations
from services.excel_service import quotation_to_excel
from services.quotation import calculate_quotation
from utils.constants import INCOTERM_DESCRIPTIONS
from utils.i18n import localize_error, option_label, tr


INCOTERM_DESCRIPTIONS_ZH = {
    "EXW": "产品 + 包装 + 平台/银行手续费",
    "FOB": "EXW + 国内运输 + 出口操作费",
    "CIF": "FOB + 国际运费 + 保险",
    "DDP": "CIF + 关税与税费",
}


def _term_description(term: str) -> str:
    return tr(INCOTERM_DESCRIPTIONS[term], INCOTERM_DESCRIPTIONS_ZH[term])


page_header(
    tr("Quotation Calculator", "出口报价计算器"),
    tr("Build a traceable USD quotation from CNY costs and compare the commercial effect of Gross Margin versus Markup.", "根据人民币成本生成可追溯的美元报价，并比较毛利率与加成率两种定价方式。"),
    tr("P0 · Commercial decision", "P0 · 商务定价决策"),
)
operations_ledger()

st.markdown(
    f"""
    <div class="formula-note">
      <strong>{tr('Default: Gross Margin', '默认：毛利率')}</strong> — {tr('Selling price = Cost ÷ (1 − Gross Margin rate).', '售价 = 成本 ÷（1 − 毛利率）。')}<br>
      <strong>{tr('Alternative: Markup', '备选：加成率')}</strong> — {tr('Selling price = Cost × (1 + Markup rate).', '售价 = 成本 ×（1 + 加成率）。')}<br>
      {tr('The same percentage produces different selling prices. The selected method is saved and exported.', '相同百分比会产生不同售价；所选方式会随报价保存并导出。')}
    </div>
    """,
    unsafe_allow_html=True,
)

calculator_tab, records_tab = st.tabs([tr("Build quotation", "新建报价"), tr("Saved quotations", "已保存报价")])

with calculator_tab:
    with st.form("quotation_form"):
        context_left, context_mid, context_right = st.columns(3)
        product_name = context_left.text_input(tr("Product Name *", "产品名称 *"), value=tr("Fictional custom notebook", "虚拟定制笔记本"))
        quantity = context_mid.number_input(tr("Quantity *", "数量 *"), min_value=1, value=1000, step=100)
        exchange_rate = context_right.number_input(
            tr("Exchange Rate (1 USD = X CNY)", "汇率（1 USD = X CNY）"), min_value=0.0001, value=7.20, step=0.01, format="%.4f"
        )

        st.subheader(tr("Cost input · CNY", "成本输入 · 人民币"))
        cost_columns = st.columns(3)
        product_cost = cost_columns[0].number_input(tr("Unit Product Cost", "产品单位成本"), min_value=0.0, value=8.50, step=0.10)
        packaging_cost = cost_columns[1].number_input(tr("Unit Packaging Cost", "包装单位成本"), min_value=0.0, value=1.20, step=0.10)
        domestic = cost_columns[2].number_input(tr("Domestic Transportation", "国内运输费"), min_value=0.0, value=650.0, step=50.0)
        export_handling = cost_columns[0].number_input(tr("Export Handling", "出口操作费"), min_value=0.0, value=450.0, step=50.0)
        freight = cost_columns[1].number_input(tr("International Freight", "国际运费"), min_value=0.0, value=2800.0, step=100.0)
        insurance = cost_columns[2].number_input(tr("Insurance", "保险费"), min_value=0.0, value=120.0, step=10.0)
        tariff = cost_columns[0].number_input(tr("Tariff", "关税"), min_value=0.0, value=600.0, step=50.0)
        tax = cost_columns[1].number_input(tr("Tax", "税费"), min_value=0.0, value=380.0, step=50.0)
        platform_fee = cost_columns[2].number_input(tr("Platform / Bank Fee", "平台 / 银行手续费"), min_value=0.0, value=180.0, step=10.0)

        method_col, rate_col, term_col = st.columns(3)
        pricing_label = method_col.radio(
            tr("Pricing Method", "定价方式"),
            ["Gross Margin", "Markup"],
            format_func=option_label,
            help=tr("Gross Margin measures profit as a percentage of selling price. Markup measures profit as a percentage of cost.", "毛利率表示利润占售价的比例；加成率表示利润占成本的比例。"),
        )
        rate_percent = rate_col.number_input(
            tr(f"Target {pricing_label} (%)", f"目标{option_label(pricing_label)}（%）"), min_value=0.0, max_value=95.0 if pricing_label == "Gross Margin" else 500.0, value=25.0, step=1.0
        )
        selected_term = term_col.selectbox(tr("Primary Incoterm", "主要贸易术语"), ["EXW", "FOB", "CIF", "DDP"], index=1)

        detail_cols = st.columns(3)
        valid_until = detail_cols[0].date_input(tr("Quotation Valid Until", "报价有效期至"), value=date.today() + timedelta(days=30))
        moq = detail_cols[1].number_input("MOQ", min_value=1, value=500, step=100)
        lead_time = detail_cols[2].text_input(tr("Lead Time", "交货周期"), value=tr("25–30 days after artwork approval", "稿件确认后 25–30 天"))
        payment_terms = st.text_input(tr("Payment Terms", "付款条款"), value=tr("30% deposit, 70% balance before shipment", "30% 定金，70% 余款发货前付清"))
        notes = st.text_area(tr("Notes", "备注"), placeholder=tr("Optional assumptions or exclusions", "可选：报价假设或不包含事项"))
        calculate = st.form_submit_button(tr("Calculate quotation", "计算报价"), type="primary")

    if calculate:
        try:
            if not product_name.strip():
                raise ValueError("Product Name is required.")
            result = calculate_quotation(
                product_unit_cost_cny=product_cost,
                packaging_unit_cost_cny=packaging_cost,
                quantity=quantity,
                domestic_transport_cny=domestic,
                export_handling_cny=export_handling,
                international_freight_cny=freight,
                insurance_cny=insurance,
                tariff_tax_cny=tariff + tax,
                platform_bank_fee_cny=platform_fee,
                exchange_rate_cny_per_usd=exchange_rate,
                pricing_rate=Decimal(str(rate_percent)) / Decimal("100"),
                pricing_method="gross_margin" if pricing_label == "Gross Margin" else "markup",
            )
            st.session_state["quotation_result"] = result
            st.session_state["quotation_metadata"] = {
                "product_name": product_name,
                "selected_term": selected_term,
                "valid_until": valid_until.isoformat(),
                "moq": moq,
                "lead_time": lead_time,
                "payment_terms": payment_terms,
                "notes": notes,
            }
        except ValueError as exc:
            st.error(localize_error(str(exc)))

    if "quotation_result" in st.session_state:
        result = st.session_state["quotation_result"]
        metadata = st.session_state["quotation_metadata"]
        st.subheader(tr(f"Results · {result['pricing_method_label']}", f"计算结果 · {option_label(result['pricing_method_label'])}"))
        formula_text = tr(
            result["formula"],
            "售价 = 成本 ÷（1 − 毛利率）" if result["pricing_method"] == "gross_margin" else "售价 = 成本 ×（1 + 加成率）",
        )
        st.caption(tr(f"Formula: {result['formula']} · Exchange rate: 1 USD = {result['exchange_rate_cny_per_usd']} CNY", f"公式：{formula_text} · 汇率：1 USD = {result['exchange_rate_cny_per_usd']} CNY"))
        rows = []
        for term, values in result["terms"].items():
            rows.append(
                {
                    "Incoterm": term,
                    "Included costs": _term_description(term),
                    "Cost CNY": float(values["cost_total_cny"]),
                    "Quote USD": float(values["total_usd"]),
                    "Unit USD": float(values["unit_usd"]),
                    "Gross Profit USD": float(values["gross_profit_usd"]),
                    "Gross Margin %": float(values["gross_margin"] * 100),
                }
            )
        st.dataframe(
            pd.DataFrame(rows),
            width="stretch",
            hide_index=True,
            column_config={
                "Incoterm": tr("Incoterm", "贸易术语"),
                "Included costs": tr("Included costs", "包含成本"),
                "Cost CNY": st.column_config.NumberColumn(tr("Cost CNY", "成本 CNY"), format="¥ %.2f"),
                "Quote USD": st.column_config.NumberColumn(tr("Quote USD", "报价 USD"), format="$ %.2f"),
                "Unit USD": st.column_config.NumberColumn(tr("Unit USD", "单位报价 USD"), format="$ %.4f"),
                "Gross Profit USD": st.column_config.NumberColumn(tr("Gross Profit USD", "毛利润 USD"), format="$ %.2f"),
                "Gross Margin %": st.column_config.NumberColumn(tr("Gross Margin %", "毛利率 %"), format="%.2f%%"),
            },
        )
        chosen = result["terms"][metadata["selected_term"]]
        summary_cols = st.columns(4)
        summary_cols[0].metric(tr("Primary term", "主要术语"), metadata["selected_term"])
        summary_cols[1].metric(tr("Total quote", "报价总额"), f"${chosen['total_usd']:,.2f}")
        summary_cols[2].metric(tr("Unit quote", "单位报价"), f"${chosen['unit_usd']:,.4f}")
        summary_cols[3].metric(tr("Gross profit", "毛利润"), f"${chosen['gross_profit_usd']:,.2f}")

        with st.expander(tr("Cost composition by Incoterm", "各贸易术语成本构成")):
            for term, values in result["terms"].items():
                st.markdown(f"**{term}** — {_term_description(term)}")
                st.json({key: f"¥{value:,.2f}" for key, value in values["components_cny"].items()})

        customer_rows = list_customers()
        customer_options = {None: tr("No customer linked", "不关联客户"), **{row["id"]: row["company_name"] for row in customer_rows}}
        linked_customer = st.selectbox(tr("Link customer (optional)", "关联客户（可选）"), list(customer_options), format_func=customer_options.get)
        action_left, action_right = st.columns(2)
        if action_left.button(tr("Save quotation record", "保存报价记录"), type="primary", width="stretch"):
            record = {
                "customer_id": linked_customer,
                "product_name": metadata["product_name"],
                "quantity": result["quantity"],
                "incoterm": metadata["selected_term"],
                "pricing_method": result["pricing_method"],
                "pricing_rate": float(result["pricing_rate"]),
                "unit_product_cost": product_cost,
                "packaging_cost": packaging_cost,
                "domestic_transportation_cost": domestic,
                "export_handling_cost": export_handling,
                "international_freight": freight,
                "insurance_cost": insurance,
                "tariff_and_tax": tariff + tax,
                "platform_or_bank_fee": platform_fee,
                "exchange_rate": float(result["exchange_rate_cny_per_usd"]),
                "total_cost_cny": float(chosen["cost_total_cny"]),
                "total_quote_usd": float(chosen["total_usd"]),
                "unit_quote_usd": float(chosen["unit_usd"]),
                "gross_profit_usd": float(chosen["gross_profit_usd"]),
                "gross_margin": float(chosen["gross_margin"]),
                "valid_until": metadata["valid_until"],
                "moq": metadata["moq"],
                "lead_time": metadata["lead_time"],
                "payment_terms": metadata["payment_terms"],
                "notes": metadata["notes"],
                "calculation_json": result,
            }
            try:
                create_quotation(record)
                st.success(tr("Quotation record saved.", "报价记录已保存。"))
            except (TypeError, ValueError) as exc:
                st.error(localize_error(str(exc)))
        export_bytes = quotation_to_excel(result, metadata)
        action_right.download_button(
            tr("Export Excel quotation", "导出 Excel 报价单"),
            data=export_bytes,
            file_name="fictional_export_quotation.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )

with records_tab:
    records = list_quotations()
    if records:
        st.dataframe(pd.DataFrame(records), width="stretch", hide_index=True)
    else:
        st.info(tr("No saved quotations yet. Calculate and save one from the first tab.", "暂无已保存报价；请先在第一个标签页计算并保存。"))
