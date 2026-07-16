"""Searchable product knowledge base with a simple add workflow."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.theme import operations_ledger, page_header
from database.repository import create_product, list_products
from utils.i18n import localize_error, tr


page_header(
    tr("Product Knowledge Base", "产品知识库"),
    tr(
        "Keep quotation inputs, production constraints, common questions, and selling points in one searchable reference.",
        "集中管理报价参数、生产限制、客户常见问题和产品卖点，方便快速检索。",
    ),
    tr("P2 · Commercial reference", "P2 · 商务资料"),
)
operations_ledger()

browse_tab, add_tab = st.tabs([tr("Browse products", "浏览产品"), tr("Add product", "新增产品")])

with browse_tab:
    all_products = list_products()
    categories = sorted({row.get("category") for row in all_products if row.get("category")})
    search_col, category_col = st.columns([2, 1])
    search = search_col.text_input(tr("Search", "搜索"), placeholder=tr("Name, application, material or specification", "产品名、用途、材料或规格"))
    selected_category = category_col.selectbox(
        tr("Category", "产品类别"),
        ["All", *categories],
        format_func=lambda value: tr("All", "全部") if value == "All" else value,
    )
    products = list_products(
        search=search or None,
        category=None if selected_category == "All" else selected_category,
    )
    st.caption(tr(f"{len(products)} products", f"共 {len(products)} 个产品"))
    for product in products:
        with st.expander(f"{product['product_name']} · {product.get('category') or 'Uncategorized'}"):
            left, right = st.columns(2)
            left.markdown(f"**{tr('Application', '用途')}**  \n{product.get('application') or '—'}")
            left.markdown(f"**{tr('Material', '材料')}**  \n{product.get('material') or '—'}")
            left.markdown(f"**{tr('Specification', '规格')}**  \n{product.get('specification') or '—'}")
            left.markdown(f"**{tr('Packaging', '包装')}**  \n{product.get('packaging') or '—'}")
            right.metric("MOQ", f"{product.get('moq') or 0:,}")
            right.metric(tr("Synthetic unit cost", "虚拟单位成本"), f"¥{product.get('unit_cost') or 0:,.2f}")
            right.write(f"{tr('Sample lead time', '样品周期')}：{product.get('sample_lead_time') or '—'}")
            right.write(f"{tr('Production lead time', '生产周期')}：{product.get('production_lead_time') or '—'}")
            st.markdown(f"**{tr('Selling points', '产品卖点')}：** {product.get('selling_points') or '—'}")
            st.markdown(f"**{tr('Common questions', '常见问题')}：** {product.get('common_customer_questions') or '—'}")
    if not products:
        st.info(tr("No products match the current search.", "没有符合当前条件的产品。"))

with add_tab:
    with st.form("add_product_form", clear_on_submit=True):
        cols = st.columns(3)
        product_name = cols[0].text_input(tr("Product Name *", "产品名称 *"))
        category = cols[1].text_input(tr("Category", "产品类别"))
        application = cols[2].text_input(tr("Application", "用途"))
        material = cols[0].text_input(tr("Material", "材料"))
        specification = cols[1].text_input(tr("Specification", "规格"))
        moq = cols[2].number_input("MOQ", min_value=0, value=500, step=100)
        sample_lead = cols[0].text_input(tr("Sample Lead Time", "样品周期"))
        production_lead = cols[1].text_input(tr("Production Lead Time", "生产周期"))
        unit_cost = cols[2].number_input(tr("Synthetic Unit Cost (CNY)", "虚拟单位成本（CNY）"), min_value=0.0, value=0.0)
        packaging = st.text_input(tr("Packaging", "包装"))
        questions = st.text_area(tr("Common Customer Questions", "客户常见问题"))
        selling_points = st.text_area(tr("Selling Points", "产品卖点"))
        notes = st.text_area(tr("Notes", "备注"))
        save = st.form_submit_button(tr("Add product", "新增产品"), type="primary")
    if save:
        try:
            product_id = create_product(
                {
                    "product_name": product_name.strip(),
                    "category": category.strip(),
                    "application": application.strip(),
                    "material": material.strip(),
                    "specification": specification.strip(),
                    "moq": moq,
                    "sample_lead_time": sample_lead.strip(),
                    "production_lead_time": production_lead.strip(),
                    "packaging": packaging.strip(),
                    "unit_cost": unit_cost,
                    "common_customer_questions": questions.strip(),
                    "selling_points": selling_points.strip(),
                    "notes": notes.strip(),
                }
            )
            st.success(tr(f"Product #{product_id} added.", f"产品 #{product_id} 已新增。"))
            st.rerun()
        except ValueError as exc:
            st.error(localize_error(str(exc)))

st.caption(tr("Every displayed company, cost and product example is fictional portfolio data.", "页面中的公司、成本和产品示例均为虚拟作品集数据。"))
