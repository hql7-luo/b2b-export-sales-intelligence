"""Customer CRUD, scoring, filtering, and spreadsheet transfer."""

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
    list_customers,
    set_manual_score,
    update_customer,
)
from services.excel_service import customers_to_excel, import_customer_file
from services.scoring import score_customer
from utils.constants import IMPORT_FREQUENCIES, LEAD_SOURCES, STAGES
from utils.i18n import is_chinese, localize_error, option_label, score_dimension_label, t, tr
from utils.validation import is_valid_email, is_valid_url, normalize_date


def _customer_payload(prefix: str, existing: dict | None = None) -> dict:
    """Render reusable customer fields and return normalized data."""
    existing = existing or {}
    left, middle, right = st.columns(3)
    with left:
        company_name = st.text_input(
            tr("Company Name *", "公司名称 *"), value=existing.get("company_name", "") or "", key=f"{prefix}_company"
        )
        contact_name = st.text_input(
            tr("Contact Name", "联系人姓名"), value=existing.get("contact_name", "") or "", key=f"{prefix}_contact"
        )
        job_title = st.text_input(
            tr("Job Title", "职位"), value=existing.get("job_title", "") or "", key=f"{prefix}_title"
        )
        country = st.text_input(
            tr("Country", "国家与地区"), value=existing.get("country", "") or "", key=f"{prefix}_country"
        )
        website = st.text_input(
            tr("Website", "网站"), value=existing.get("website", "") or "", placeholder="https://example.com", key=f"{prefix}_website"
        )
    with middle:
        email = st.text_input(
            tr("Email", "邮箱"), value=existing.get("email", "") or "", placeholder="fictional.contact@example.com", key=f"{prefix}_email"
        )
        phone = st.text_input(
            tr("Phone / WhatsApp", "电话 / WhatsApp"), value=existing.get("phone_whatsapp", existing.get("phone", "")) or "", key=f"{prefix}_phone"
        )
        lead_source_value = existing.get("lead_source") or LEAD_SOURCES[0]
        lead_source_options = (
            LEAD_SOURCES
            if lead_source_value in LEAD_SOURCES
            else [lead_source_value, *LEAD_SOURCES]
        )
        lead_source = st.selectbox(
            tr("Lead Source", "线索来源"),
            lead_source_options,
            index=lead_source_options.index(lead_source_value),
            key=f"{prefix}_source",
            format_func=option_label,
        )
        product_interest = st.text_input(
            tr("Product Interest", "意向产品"), value=existing.get("product_interest", "") or "", key=f"{prefix}_product"
        )
        frequency_value = existing.get("import_frequency") or IMPORT_FREQUENCIES[0]
        frequency_options = (
            IMPORT_FREQUENCIES
            if frequency_value in IMPORT_FREQUENCIES
            else [frequency_value, *IMPORT_FREQUENCIES]
        )
        import_frequency = st.selectbox(
            tr("Import Frequency", "进口频率"),
            frequency_options,
            index=frequency_options.index(frequency_value),
            key=f"{prefix}_frequency",
            format_func=option_label,
        )
    with right:
        try:
            existing_volume = max(
                0.0, float(existing.get("estimated_purchase_volume") or 0)
            )
        except (TypeError, ValueError):
            existing_volume = 0.0
        purchase_volume = st.number_input(
            tr("Estimated Purchase Volume (USD)", "预计采购金额（USD）"),
            min_value=0.0,
            value=existing_volume,
            step=1000.0,
            key=f"{prefix}_volume",
        )
        last_value = existing.get("last_contact_date")
        try:
            last_date = date.fromisoformat(str(last_value)[:10]) if last_value else None
        except ValueError:
            last_date = None
        last_contact = st.date_input(
            tr("Last Contact Date", "最近联系日期"),
            value=last_date,
            key=f"{prefix}_last",
        )
        next_value = existing.get("next_follow_up_date")
        try:
            next_date = date.fromisoformat(str(next_value)[:10]) if next_value else None
        except ValueError:
            next_date = None
        next_follow_up = st.date_input(
            tr("Next Follow-up Date", "下次跟进日期"),
            value=next_date,
            key=f"{prefix}_next",
        )
        stage_value = existing.get("current_stage") or STAGES[0]
        current_stage = st.selectbox(
            tr("Current Stage", "当前阶段"),
            STAGES,
            index=STAGES.index(stage_value) if stage_value in STAGES else 0,
            key=f"{prefix}_stage",
            format_func=option_label,
        )
        notes = st.text_area(
            tr("Notes", "备注"), value=existing.get("notes", "") or "", height=106, key=f"{prefix}_notes"
        )
    return {
        "company_name": company_name.strip(),
        "contact_name": contact_name.strip(),
        "job_title": job_title.strip(),
        "country": country.strip(),
        "website": website.strip(),
        "email": email.strip(),
        "phone_whatsapp": phone.strip(),
        "phone": phone.strip(),
        "lead_source": lead_source,
        "product_interest": product_interest.strip(),
        "import_frequency": import_frequency,
        "estimated_purchase_volume": purchase_volume,
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


page_header(
    t("page.customers.title"),
    t("page.customers.subtitle"),
    t("page.customers.section"),
)

customers = list_customers()
pipeline_tab, add_tab, edit_tab, timeline_tab, transfer_tab = st.tabs(
    [
        tr("Pipeline", "客户管道"),
        tr("Add customer", "新增客户"),
        tr("Edit & score", "编辑与评分"),
        t("customer.timeline.tab"),
        tr("Import / Export", "导入 / 导出"),
    ]
)

with pipeline_tab:
    if not customers:
        st.markdown(
            f'<div class="empty-guide"><strong>{tr("No customers yet.", "暂无客户。")}</strong><br>{tr("Add one manually or import the provided template.", "请手动新增客户，或导入客户表格。")}</div>',
            unsafe_allow_html=True,
        )
    else:
        search_col, country_col, stage_col, grade_col = st.columns([2, 1, 1, 1])
        search = search_col.text_input(tr("Search", "搜索"), placeholder=tr("Company, contact, email or product", "公司、联系人、邮箱或产品"))
        countries = sorted({row.get("country") for row in customers if row.get("country")})
        country_filter = country_col.selectbox(tr("Country", "国家与地区"), ["All", *countries], format_func=lambda value: tr("All", "全部") if value == "All" else value)
        stage_filter = stage_col.selectbox(tr("Stage", "阶段"), ["All", *STAGES], format_func=lambda value: tr("All", "全部") if value == "All" else option_label(value))
        grade_filter = grade_col.selectbox(tr("Grade", "等级"), ["All", "A", "B", "C", "D"], format_func=lambda value: tr("All", "全部") if value == "All" else value)

        filtered = customers
        if search:
            needle = search.lower()
            filtered = [
                row
                for row in filtered
                if needle
                in " ".join(
                    str(row.get(key) or "")
                    for key in ("company_name", "contact_name", "email", "product_interest")
                ).lower()
            ]
        if country_filter != "All":
            filtered = [row for row in filtered if row.get("country") == country_filter]
        if stage_filter != "All":
            filtered = [row for row in filtered if row.get("current_stage") == stage_filter]
        if grade_filter != "All":
            filtered = [row for row in filtered if row.get("effective_grade") == grade_filter]

        frame = pd.DataFrame(filtered)
        if is_chinese() and not frame.empty:
            frame["current_stage"] = frame["current_stage"].map(option_label)
        display_columns = [
            column
            for column in (
                "company_name",
                "contact_name",
                "country",
                "product_interest",
                "current_stage",
                "effective_grade",
                "effective_score",
                "next_follow_up_date",
            )
            if column in frame.columns
        ]
        st.caption(tr(f"{len(filtered)} of {len(customers)} customers", f"显示 {len(filtered)} / {len(customers)} 个客户"))
        st.dataframe(
            frame[display_columns],
            width="stretch",
            hide_index=True,
            column_config={
                "company_name": tr("Company", "公司"),
                "contact_name": tr("Contact", "联系人"),
                "country": tr("Country", "国家与地区"),
                "product_interest": tr("Product Interest", "意向产品"),
                "current_stage": tr("Stage", "阶段"),
                "effective_grade": tr("Grade", "等级"),
                "effective_score": st.column_config.ProgressColumn(tr("Score", "评分"), min_value=0, max_value=100),
                "next_follow_up_date": tr("Next Follow-up", "下次跟进"),
            },
        )

with add_tab:
    with st.form("add_customer_form", clear_on_submit=True):
        new_payload = _customer_payload("add")
        submitted = st.form_submit_button(tr("Add and score customer", "新增客户并自动评分"), type="primary")
    if submitted:
        try:
            _validate_customer(new_payload)
            score = score_customer(new_payload)
            new_payload.update(
                auto_score=score["total_score"],
                auto_grade=score["grade"],
                score_breakdown=score["breakdown"],
                score_reasons=score.get("dimension_reasons", []),
            )
            customer_id = create_customer(new_payload)
            st.success(tr(f"Customer #{customer_id} added with grade {score['grade']} ({score['total_score']}/100).", f"客户 #{customer_id} 已新增，评级 {score['grade']}（{score['total_score']}/100）。"))
            st.rerun()
        except (ValueError, TypeError) as exc:
            st.error(localize_error(str(exc)))

with edit_tab:
    if not customers:
        st.info(tr("Add a customer before editing or overriding a score.", "请先添加客户，再编辑或人工调整评分。"))
    else:
        labels = {row["id"]: f"{row['company_name']} · {row.get('effective_grade', '—')}" for row in customers}
        selected_id = st.selectbox(tr("Select customer", "选择客户"), list(labels), format_func=labels.get)
        selected = get_customer(selected_id)
        with st.form(f"edit_customer_{selected_id}"):
            edited_payload = _customer_payload(f"edit_{selected_id}", selected)
            recalculate = st.checkbox(tr("Recalculate automatic score from current fields", "根据当前字段重新计算自动评分"), value=True)
            save_edit = st.form_submit_button(tr("Save customer changes", "保存客户修改"), type="primary")
        if save_edit:
            try:
                _validate_customer(edited_payload)
                if recalculate:
                    score = score_customer(edited_payload)
                    edited_payload.update(
                        auto_score=score["total_score"],
                        auto_grade=score["grade"],
                        score_breakdown=score["breakdown"],
                        score_reasons=score.get("dimension_reasons", []),
                    )
                update_customer(selected_id, edited_payload)
                st.success(tr("Customer changes saved.", "客户修改已保存。"))
                st.rerun()
            except (ValueError, TypeError) as exc:
                st.error(localize_error(str(exc)))

        selected = get_customer(selected_id)
        st.subheader(tr("Scoring evidence", "评分依据"))
        score_cols = st.columns(5)
        breakdown = selected.get("score_breakdown") or {}
        for column, (key, label, maximum) in zip(
            score_cols,
            [
                ("company_authenticity", tr("Authenticity", "公司真实性"), 20),
                ("product_fit", tr("Product fit", "产品匹配"), 25),
                ("requirement_clarity", tr("Requirement", "需求清晰度"), 20),
                ("purchasing_capacity", tr("Capacity", "采购能力"), 20),
                ("communication_engagement", tr("Engagement", "沟通参与度"), 15),
            ],
        ):
            column.metric(label, f"{breakdown.get(key, 0)}/{maximum}")
        reasons = selected.get("score_reasons") or {}
        if isinstance(reasons, dict):
            for dimension, reason in reasons.items():
                st.write(f"• **{score_dimension_label(dimension)}** — {reason}")
        else:
            for reason in reasons:
                st.write(f"• {reason}")

        with st.form(f"score_override_{selected_id}"):
            override_score = st.number_input(
                tr("Manual score", "人工评分"), min_value=0, max_value=100, value=int(selected.get("effective_score") or 0)
            )
            override_reason = st.text_input(
                tr("Override reason *", "调整原因 *"), placeholder=tr("Example: Purchase plan confirmed during a video call", "例如：视频会议中已确认采购计划")
            )
            save_override = st.form_submit_button(tr("Apply manual score", "应用人工评分"))
        if save_override:
            if not override_reason.strip():
                st.error(tr("A reason is required for an auditable manual override.", "人工调整评分必须填写原因，以便审计。"))
            else:
                set_manual_score(selected_id, override_score, override_reason.strip())
                st.success(tr("Manual score saved with an audit reason.", "人工评分及调整原因已保存。"))
                st.rerun()

        if st.button(tr("Delete selected customer", "删除所选客户"), type="secondary"):
            delete_customer(selected_id)
            st.success(tr("Customer deleted.", "客户已删除。"))
            st.rerun()

with timeline_tab:
    if not customers:
        st.info(t("customer.timeline.no_customers"))
    else:
        timeline_labels = {
            row["id"]: row["company_name"]
            for row in customers
        }
        context_customer_id = st.session_state.get("workflow_context", {}).get(
            "customer_id"
        )
        if (
            "timeline_customer_id" not in st.session_state
            or st.session_state["timeline_customer_id"] not in timeline_labels
        ):
            st.session_state["timeline_customer_id"] = (
                context_customer_id
                if context_customer_id in timeline_labels
                else next(iter(timeline_labels))
            )
        timeline_customer_id = st.selectbox(
            t("customer.timeline.select"),
            list(timeline_labels),
            format_func=timeline_labels.get,
            key="timeline_customer_id",
        )
        timeline = list_customer_timeline(timeline_customer_id)
        st.subheader(
            t(
                "customer.timeline.title",
                customer=timeline_labels[timeline_customer_id],
            )
        )
        st.caption(t("customer.timeline.caption"))
        if timeline:
            event_keys = {
                "customer_saved": "customer_saved",
                "Customer Created": "customer_saved",
                "inquiry_created": "inquiry_created",
                "Inquiry Analyzed": "inquiry_created",
                "product_matched": "product_matched",
                "quotation_created": "quotation_created",
                "Quotation Saved": "quotation_created",
                "follow_up_scheduled": "follow_up_scheduled",
            }
            timeline_rows = []
            for event in timeline:
                event_key = event_keys.get(event["activity_type"])
                metadata = event.get("metadata") or {}
                inquiry_id = event.get("inquiry_id") or metadata.get(
                    "inquiry_id"
                )
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
                timeline_rows.append(
                    {
                        "activity_date": event["activity_date"],
                        "event": (
                            t(f"customer.timeline.event.{event_key}")
                            if event_key
                            else option_label(event["activity_type"])
                        ),
                        "detail": detail,
                        "inquiry_id": str(inquiry_id) if inquiry_id else "—",
                        "quotation_id": (
                            str(quotation_id) if quotation_id else "—"
                        ),
                    }
                )
            st.dataframe(
                pd.DataFrame(timeline_rows),
                width="stretch",
                hide_index=True,
                column_config={
                    "activity_date": t("customer.timeline.date"),
                    "event": t("customer.timeline.event"),
                    "detail": t("customer.timeline.detail"),
                    "inquiry_id": t("customer.timeline.inquiry_id"),
                    "quotation_id": t("customer.timeline.quotation_id"),
                },
            )
        else:
            st.info(t("customer.timeline.empty"))

with transfer_tab:
    upload = st.file_uploader(tr("Import customers", "导入客户"), type=["csv", "xlsx"], help=tr("Maximum 5 MB. Company Name is required.", "最大 5 MB；公司名称为必填项。"))
    if upload and st.button(tr("Validate and import", "验证并导入"), type="primary"):
        try:
            imported_rows = import_customer_file(upload.getvalue(), upload.name)
            prepared_rows = []
            for row in imported_rows:
                normalized = {
                    key: (value.item() if hasattr(value, "item") else value)
                    for key, value in row.items()
                }
                normalized.setdefault("email", "")
                normalized.setdefault("website", "")
                _validate_customer(normalized)
                score = score_customer(normalized)
                normalized.update(
                    auto_score=score["total_score"],
                    auto_grade=score["grade"],
                    score_breakdown=score["breakdown"],
                    score_reasons=score.get("dimension_reasons", []),
                )
                prepared_rows.append(normalized)
            imported_count = len(create_customers_batch(prepared_rows))
            st.success(tr(f"Imported {imported_count} customers.", f"已导入 {imported_count} 个客户。"))
            st.rerun()
        except (ValueError, TypeError) as exc:
            st.error(tr(f"Import stopped: {exc}", f"导入已停止：{localize_error(str(exc))}"))

    export_bytes = customers_to_excel(customers)
    st.download_button(
        tr("Export current customers to Excel", "导出当前客户到 Excel"),
        data=export_bytes,
        file_name="fictional_export_customers.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=not customers,
    )
    st.caption(tr("Spreadsheet text is protected against formula injection. Demo contacts use reserved example domains.", "表格文本已防止公式注入；演示联系人统一使用保留示例域名。"))
