"""Action-oriented customer portfolio and business timeline."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from components.theme import page_header
from database.repository import (
    create_customer,
    create_customers_batch,
    delete_customer,
    get_customer,
    list_customer_timeline,
    update_customer,
)
from services.customer_intelligence import customer_portfolio
from services.excel_service import customers_to_excel, import_customer_file
from utils.constants import IMPORT_FREQUENCIES, LEAD_SOURCES, STAGES
from utils.i18n import localize_error, option_label, t
from utils.validation import is_valid_email, is_valid_url, normalize_date


TIMELINE_EVENT_KEYS = {
    "customer_saved": "customer_saved",
    "Customer Created": "customer_saved",
    "inquiry_created": "inquiry_created",
    "Inquiry Analyzed": "inquiry_created",
    "product_matched": "product_matched",
    "quotation_created": "quotation_created",
    "Quotation Saved": "quotation_created",
    "follow_up_scheduled": "follow_up_scheduled",
}


def _date_value(value: object) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except (TypeError, ValueError):
        return None


def _customer_payload(prefix: str, existing: dict | None = None) -> dict:
    existing = existing or {}
    columns = st.columns(3)
    company_name = columns[0].text_input(
        t("customer.field.company"),
        value=existing.get("company_name") or "",
        key=f"{prefix}_company",
    )
    contact_name = columns[1].text_input(
        t("customer.field.contact"),
        value=existing.get("contact_name") or "",
        key=f"{prefix}_contact",
    )
    job_title = columns[2].text_input(
        t("customer.field.job_title"),
        value=existing.get("job_title") or "",
        key=f"{prefix}_title",
    )
    country = columns[0].text_input(
        t("customer.field.country"),
        value=existing.get("country") or "",
        key=f"{prefix}_country",
    )
    website = columns[1].text_input(
        t("customer.field.website"),
        value=existing.get("website") or "",
        placeholder="https://example.com",
        key=f"{prefix}_website",
    )
    email = columns[2].text_input(
        t("customer.field.email"),
        value=existing.get("email") or "",
        placeholder="fictional.contact@example.com",
        key=f"{prefix}_email",
    )
    phone = columns[0].text_input(
        t("customer.field.phone"),
        value=existing.get("phone") or "",
        key=f"{prefix}_phone",
    )
    lead_source_value = existing.get("lead_source") or LEAD_SOURCES[0]
    lead_source_options = (
        LEAD_SOURCES
        if lead_source_value in LEAD_SOURCES
        else [lead_source_value, *LEAD_SOURCES]
    )
    lead_source = columns[1].selectbox(
        t("customer.field.source"),
        lead_source_options,
        index=lead_source_options.index(lead_source_value),
        format_func=option_label,
        key=f"{prefix}_source",
    )
    product_interest = columns[2].text_input(
        t("customer.field.product"),
        value=existing.get("product_interest") or "",
        key=f"{prefix}_product",
    )
    frequency_value = (
        existing.get("import_frequency") or IMPORT_FREQUENCIES[0]
    )
    frequency_options = (
        IMPORT_FREQUENCIES
        if frequency_value in IMPORT_FREQUENCIES
        else [frequency_value, *IMPORT_FREQUENCIES]
    )
    import_frequency = columns[0].selectbox(
        t("customer.field.frequency"),
        frequency_options,
        index=frequency_options.index(frequency_value),
        format_func=option_label,
        key=f"{prefix}_frequency",
    )
    volume = columns[1].number_input(
        t("customer.field.volume"),
        min_value=0.0,
        value=float(existing.get("estimated_purchase_volume") or 0),
        step=1000.0,
        key=f"{prefix}_volume",
    )
    stage_value = existing.get("current_stage") or STAGES[0]
    current_stage = columns[2].selectbox(
        t("customer.field.stage"),
        STAGES,
        index=STAGES.index(stage_value) if stage_value in STAGES else 0,
        format_func=option_label,
        key=f"{prefix}_stage",
    )
    last_contact = columns[0].date_input(
        t("customer.field.last_contact"),
        value=_date_value(existing.get("last_contact_date")),
        key=f"{prefix}_last",
    )
    next_follow_up = columns[1].date_input(
        t("customer.field.next_follow_up"),
        value=_date_value(existing.get("next_follow_up_date")),
        key=f"{prefix}_next",
    )
    notes = st.text_area(
        t("customer.field.notes"),
        value=existing.get("notes") or "",
        key=f"{prefix}_notes",
    )
    return {
        "company_name": company_name.strip(),
        "contact_name": contact_name.strip(),
        "job_title": job_title.strip(),
        "country": country.strip(),
        "website": website.strip(),
        "email": email.strip(),
        "phone": phone.strip(),
        "lead_source": lead_source,
        "product_interest": product_interest.strip(),
        "import_frequency": import_frequency,
        "estimated_purchase_volume": volume,
        "last_contact_date": normalize_date(last_contact),
        "next_follow_up_date": normalize_date(next_follow_up),
        "current_stage": current_stage,
        "notes": notes.strip(),
    }


def _validate_customer(payload: dict) -> None:
    if not payload["company_name"]:
        raise ValueError("Company Name is required.")
    if not is_valid_email(payload.get("email")):
        raise ValueError("Email format is invalid.")
    if not is_valid_url(payload.get("website")):
        raise ValueError("Website must begin with http:// or https://.")


def _timeline_rows(customer_id: int) -> list[dict]:
    rows = []
    for event in list_customer_timeline(customer_id):
        event_key = TIMELINE_EVENT_KEYS.get(event["activity_type"])
        metadata = event.get("metadata") or {}
        inquiry_id = event.get("inquiry_id") or metadata.get("inquiry_id")
        quotation_id = event.get("quotation_id") or metadata.get(
            "quotation_id"
        )
        if event_key == "customer_saved":
            detail = t("customer.timeline.detail.customer_saved")
        elif event_key == "inquiry_created":
            detail = t(
                "customer.timeline.detail.inquiry_created",
                inquiry_id=inquiry_id or "—",
            )
        elif event_key == "product_matched":
            detail = t(
                "customer.timeline.detail.product_matched",
                product_id=metadata.get("product_id") or "—",
            )
        elif event_key == "quotation_created":
            detail = t(
                "customer.timeline.detail.quotation_created",
                quotation_id=quotation_id or "—",
            )
        elif event_key == "follow_up_scheduled":
            detail = t(
                "customer.timeline.detail.follow_up_scheduled",
                follow_up_id=metadata.get("follow_up_id") or "—",
                date=metadata.get("next_follow_up_date")
                or metadata.get("follow_up_date")
                or "—",
            )
        else:
            detail = event["description"]
        rows.append(
            {
                "activity_date": event["activity_date"],
                "event": (
                    t(f"customer.timeline.event.{event_key}")
                    if event_key
                    else option_label(event["activity_type"])
                ),
                "detail": detail,
                "inquiry_id": f"#{inquiry_id}" if inquiry_id else "—",
                "quotation_id": (
                    f"#{quotation_id}" if quotation_id else "—"
                ),
            }
        )
    return rows


page_header(
    t("page.customers.title"),
    t("page.customers.subtitle"),
    t("page.customers.section"),
)

portfolio = customer_portfolio()
portfolio_tab, detail_tab, add_tab, transfer_tab = st.tabs(
    [
        t("customer.tab.portfolio"),
        t("customer.tab.detail"),
        t("customer.tab.add"),
        t("customer.tab.transfer"),
    ]
)

with portfolio_tab:
    if not portfolio:
        st.info(t("customer.portfolio.empty"))
    else:
        filter_columns = st.columns([2, 1, 1, 1])
        search = filter_columns[0].text_input(
            t("customer.search.label"),
            placeholder=t("customer.search.placeholder"),
            key="customer_portfolio_search",
        )
        countries = sorted(
            {
                row.get("country")
                for row in portfolio
                if row.get("country")
            }
        )
        selected_country = filter_columns[1].selectbox(
            t("customer.filter.country"),
            [None, *countries],
            format_func=lambda value: value or t("common.all"),
            key="customer_portfolio_country",
        )
        selected_stage = filter_columns[2].selectbox(
            t("customer.filter.stage"),
            [None, *STAGES],
            format_func=lambda value: (
                t("common.all") if value is None else option_label(value)
            ),
            key="customer_portfolio_stage",
        )
        quality_bands = (
            "high_potential",
            "qualified",
            "developing",
            "low_signal",
        )
        selected_quality = filter_columns[3].selectbox(
            t("customer.filter.quality"),
            [None, *quality_bands],
            format_func=lambda value: (
                t("common.all")
                if value is None
                else t(f"lead_quality.band.{value}")
            ),
            key="customer_portfolio_quality",
        )
        filtered = portfolio
        if search:
            needle = search.lower()
            filtered = [
                row
                for row in filtered
                if needle
                in " ".join(
                    str(row.get(key) or "")
                    for key in (
                        "company_name",
                        "contact_name",
                        "email",
                        "product_interest",
                    )
                ).lower()
            ]
        if selected_country:
            filtered = [
                row
                for row in filtered
                if row.get("country") == selected_country
            ]
        if selected_stage:
            filtered = [
                row
                for row in filtered
                if row.get("current_stage") == selected_stage
            ]
        if selected_quality:
            filtered = [
                row
                for row in filtered
                if row.get("lead_quality_band") == selected_quality
            ]
        display_rows = []
        for row in filtered:
            display_rows.append(
                {
                    "company_name": row["company_name"],
                    "contact_name": row.get("contact_name"),
                    "country": row.get("country"),
                    "product_interest": row.get("product_interest"),
                    "current_stage": option_label(
                        row.get("current_stage") or "New Lead"
                    ),
                    "data_completeness": row["data_completeness_score"],
                    "lead_quality": t(
                        f"lead_quality.band.{row['lead_quality_band']}"
                    ),
                    "next_action": t(
                        f"customer.next_action.{row['next_action']}"
                    ),
                    "next_follow_up_date": row.get("next_follow_up_date"),
                }
            )
        st.caption(
            t(
                "customer.portfolio.count",
                visible=len(filtered),
                total=len(portfolio),
            )
        )
        st.dataframe(
            pd.DataFrame(display_rows),
            width="stretch",
            hide_index=True,
            column_config={
                "company_name": t("customer.column.company"),
                "contact_name": t("customer.column.contact"),
                "country": t("customer.column.country"),
                "product_interest": t("customer.column.product"),
                "current_stage": t("customer.column.stage"),
                "data_completeness": st.column_config.ProgressColumn(
                    t("customer.column.completeness"),
                    min_value=0,
                    max_value=100,
                    format="%d%%",
                ),
                "lead_quality": t("customer.column.quality"),
                "next_action": t("customer.column.next_action"),
                "next_follow_up_date": t("customer.column.next_follow_up"),
            },
        )

with detail_tab:
    if not portfolio:
        st.info(t("customer.detail.empty"))
    else:
        labels = {row["id"]: row["company_name"] for row in portfolio}
        context_customer_id = st.session_state.get(
            "workflow_context",
            {},
        ).get("customer_id")
        if (
            "customer_detail_id" not in st.session_state
            or st.session_state["customer_detail_id"] not in labels
        ):
            st.session_state["customer_detail_id"] = (
                context_customer_id
                if context_customer_id in labels
                else next(iter(labels))
            )
        selected_id = st.selectbox(
            t("customer.detail.select"),
            list(labels),
            format_func=labels.get,
            key="customer_detail_id",
        )
        selected_summary = next(
            row for row in portfolio if row["id"] == selected_id
        )
        decision_columns = st.columns(3)
        decision_columns[0].metric(
            t("customer.detail.stage"),
            option_label(selected_summary["current_stage"]),
        )
        decision_columns[1].metric(
            t("customer.detail.quality"),
            t(
                f"lead_quality.band."
                f"{selected_summary['lead_quality_band']}"
            ),
        )
        decision_columns[2].metric(
            t("customer.detail.next_date"),
            selected_summary.get("next_follow_up_date") or "—",
        )
        st.info(
            t("customer.detail.next_action")
            + " "
            + t(
                f"customer.next_action."
                f"{selected_summary['next_action']}"
            )
        )
        completeness_columns = st.columns([1, 2])
        completeness_columns[0].metric(
            t("customer.detail.completeness"),
            f"{selected_summary['data_completeness_score']}%",
        )
        missing_fields = selected_summary["missing_profile_fields"]
        completeness_columns[1].write(
            t("customer.detail.missing")
            + " "
            + (
                ", ".join(
                    t(f"customer.profile_field.{field}")
                    for field in missing_fields
                )
                if missing_fields
                else t("customer.detail.none_missing")
            )
        )

        st.subheader(t("customer.timeline.tab"))
        timeline_rows = _timeline_rows(selected_id)
        if timeline_rows:
            st.dataframe(
                pd.DataFrame(timeline_rows),
                width="stretch",
                hide_index=True,
                column_config={
                    "activity_date": t("customer.timeline.date"),
                    "event": t("customer.timeline.event"),
                    "detail": t("customer.timeline.detail"),
                    "inquiry_id": t("customer.timeline.inquiry_id"),
                    "quotation_id": t(
                        "customer.timeline.quotation_id"
                    ),
                },
            )
        else:
            st.info(t("customer.timeline.empty"))

        with st.expander(t("customer.edit.title"), expanded=False):
            selected = get_customer(selected_id)
            with st.form(f"customer_edit_form_{selected_id}"):
                edited = _customer_payload(
                    f"customer_edit_{selected_id}",
                    selected,
                )
                save_changes = st.form_submit_button(
                    t("customer.action.save"),
                    type="primary",
                )
            if save_changes:
                try:
                    _validate_customer(edited)
                    update_customer(selected_id, edited)
                    st.success(t("customer.edit.success"))
                    st.rerun()
                except ValueError as exc:
                    st.error(localize_error(str(exc)))
            if st.button(
                t("customer.action.delete"),
                key=f"customer_delete_{selected_id}",
            ):
                delete_customer(selected_id)
                st.success(t("customer.delete.success"))
                st.rerun()

with add_tab:
    with st.form("customer_add_form", clear_on_submit=True):
        new_customer = _customer_payload("customer_add")
        add_customer = st.form_submit_button(
            t("customer.action.add"),
            type="primary",
        )
    if add_customer:
        try:
            _validate_customer(new_customer)
            customer_id = create_customer(new_customer)
            st.success(
                t("customer.add.success", customer_id=customer_id)
            )
            st.rerun()
        except ValueError as exc:
            st.error(localize_error(str(exc)))

with transfer_tab:
    upload = st.file_uploader(
        t("customer.import.label"),
        type=["csv", "xlsx"],
        help=t("customer.import.help"),
    )
    if upload and st.button(
        t("customer.import.action"),
        type="primary",
    ):
        try:
            imported_rows = import_customer_file(
                upload.getvalue(),
                upload.name,
            )
            prepared = []
            for row in imported_rows:
                normalized = {
                    key: (
                        value.item() if hasattr(value, "item") else value
                    )
                    for key, value in row.items()
                }
                normalized.setdefault("email", "")
                normalized.setdefault("website", "")
                _validate_customer(normalized)
                prepared.append(normalized)
            count = len(create_customers_batch(prepared))
            st.success(t("customer.import.success", count=count))
            st.rerun()
        except (TypeError, ValueError) as exc:
            st.error(
                t(
                    "customer.import.error",
                    error=localize_error(str(exc)),
                )
            )

    st.download_button(
        t("customer.export.action"),
        data=customers_to_excel(portfolio),
        file_name="fictional_export_customers.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=not portfolio,
    )
    st.caption(t("customer.transfer.caption"))
