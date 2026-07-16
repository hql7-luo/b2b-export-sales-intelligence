"""Compact product-reference management."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.theme import page_header
from database.repository import (
    create_product,
    get_product,
    list_products_with_match_counts,
    update_product,
)
from utils.i18n import localize_error, t


def _product_payload(prefix: str, existing: dict | None = None) -> dict:
    existing = existing or {}
    columns = st.columns(3)
    product_name = columns[0].text_input(
        t("products.field.name"),
        value=existing.get("product_name") or "",
        key=f"{prefix}_name",
    )
    category = columns[1].text_input(
        t("products.field.category"),
        value=existing.get("category") or "",
        key=f"{prefix}_category",
    )
    application = columns[2].text_input(
        t("products.field.application"),
        value=existing.get("application") or "",
        key=f"{prefix}_application",
    )
    material = columns[0].text_input(
        t("products.field.material"),
        value=existing.get("material") or "",
        key=f"{prefix}_material",
    )
    specification = columns[1].text_input(
        t("products.field.specification"),
        value=existing.get("specification") or "",
        key=f"{prefix}_specification",
    )
    moq = columns[2].number_input(
        t("products.field.moq"),
        min_value=0,
        value=int(existing.get("moq") or 0),
        step=100,
        key=f"{prefix}_moq",
    )
    sample_lead = columns[0].text_input(
        t("products.field.sample_lead"),
        value=existing.get("sample_lead_time") or "",
        key=f"{prefix}_sample",
    )
    production_lead = columns[1].text_input(
        t("products.field.production_lead"),
        value=existing.get("production_lead_time") or "",
        key=f"{prefix}_production",
    )
    unit_cost = columns[2].number_input(
        t("products.field.unit_cost"),
        min_value=0.0,
        value=float(existing.get("unit_cost") or 0),
        step=0.10,
        key=f"{prefix}_cost",
    )
    packaging = st.text_input(
        t("products.field.packaging"),
        value=existing.get("packaging") or "",
        key=f"{prefix}_packaging",
    )
    questions = st.text_area(
        t("products.field.questions"),
        value=existing.get("common_customer_questions") or "",
        key=f"{prefix}_questions",
    )
    selling_points = st.text_area(
        t("products.field.selling_points"),
        value=existing.get("selling_points") or "",
        key=f"{prefix}_selling",
    )
    notes = st.text_area(
        t("products.field.notes"),
        value=existing.get("notes") or "",
        key=f"{prefix}_notes",
    )
    return {
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


page_header(
    t("page.products.title"),
    t("page.products.subtitle"),
    t("page.products.section"),
)

catalog_tab, edit_tab, add_tab = st.tabs(
    [
        t("products.tab.catalog"),
        t("products.tab.edit"),
        t("products.tab.add"),
    ]
)

all_products = list_products_with_match_counts()
with catalog_tab:
    categories = sorted(
        {
            row.get("category")
            for row in all_products
            if row.get("category")
        }
    )
    filter_columns = st.columns([2, 1])
    search = filter_columns[0].text_input(
        t("products.search.label"),
        placeholder=t("products.search.placeholder"),
        key="products_search",
    )
    category_options = ["", *categories]
    selected_category = filter_columns[1].selectbox(
        t("products.filter.category"),
        category_options,
        format_func=lambda value: value or t("common.all"),
        key="products_category_filter",
    )
    products = list_products_with_match_counts(
        search=search or None,
        category=selected_category or None,
    )
    st.caption(
        t(
            "products.catalog.count",
            visible=len(products),
            total=len(all_products),
        )
    )
    if products:
        frame = pd.DataFrame(products)
        st.dataframe(
            frame[
                [
                    "product_name",
                    "category",
                    "specification",
                    "moq",
                    "unit_cost",
                    "packaging",
                    "sample_lead_time",
                    "production_lead_time",
                    "matched_inquiry_count",
                ]
            ],
            width="stretch",
            hide_index=True,
            column_config={
                "product_name": t("products.field.name_plain"),
                "category": t("products.field.category"),
                "specification": t("products.field.specification"),
                "moq": t("products.field.moq"),
                "unit_cost": st.column_config.NumberColumn(
                    t("products.field.unit_cost"),
                    format="¥ %.2f",
                ),
                "packaging": t("products.field.packaging"),
                "sample_lead_time": t("products.field.sample_lead"),
                "production_lead_time": t("products.field.production_lead"),
                "matched_inquiry_count": t("products.field.match_count"),
            },
        )
    else:
        st.info(t("products.catalog.empty"))

with edit_tab:
    if not all_products:
        st.info(t("products.edit.empty"))
    else:
        product_labels = {
            row["id"]: row["product_name"] for row in all_products
        }
        selected_product_id = st.selectbox(
            t("products.edit.select"),
            list(product_labels),
            format_func=product_labels.get,
            key="products_edit_id",
        )
        selected_product = get_product(selected_product_id)
        with st.form(f"products_edit_form_{selected_product_id}"):
            changes = _product_payload(
                f"products_edit_{selected_product_id}",
                selected_product,
            )
            save_changes = st.form_submit_button(
                t("products.action.save"),
                type="primary",
            )
        if save_changes:
            try:
                if not changes["product_name"]:
                    raise ValueError("product_name is required")
                update_product(selected_product_id, changes)
                st.success(t("products.edit.success"))
                st.rerun()
            except ValueError as exc:
                st.error(localize_error(str(exc)))

with add_tab:
    with st.form("products_add_form", clear_on_submit=True):
        new_product = _product_payload("products_add")
        save_product = st.form_submit_button(
            t("products.action.add"),
            type="primary",
        )
    if save_product:
        try:
            product_id = create_product(new_product)
            st.success(t("products.add.success", product_id=product_id))
            st.rerun()
        except ValueError as exc:
            st.error(localize_error(str(exc)))

st.caption(t("products.demo.caption"))
