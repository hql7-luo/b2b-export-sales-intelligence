"""Database-backed follow-up queue and quotation-linked communication records."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from components.theme import page_header
from components.workflow import update_workflow_context, workflow_rail
from database.repository import list_customers, list_follow_ups, list_quotations
from services.followup import (
    follow_up_advice,
    follow_up_priority,
    generate_follow_up_message,
)
from services.workflow import build_follow_up_context, save_follow_up_for_quotation
from utils.i18n import is_chinese, localize_error, option_label, t, tr


FOLLOW_UP_ADVICE_ZH = {
    "New Lead": "发送简短的首次联系信息，突出产品匹配度和一个可信证明。",
    "Contacted": "3–5 天后跟进，分享相关产品案例并提出一个明确问题。",
    "Replied": "总结客户需求，并追问尚未确认的商务信息。",
    "Requirement Confirmed": "报价前确认规格、数量、目的地和目标交期。",
    "Quoted": "报价后第 2 天跟进；如未回复，第 7 天再次跟进。",
    "Sample": "样品签收后确认质量反馈，并商定需要调整的内容。",
    "Negotiation": "从规格、数量或条款优化价格方案，避免只做直接降价。",
    "Order Confirmed": "确认定金、稿件、生产节点和出货文件。",
    "Lost": "记录丢单原因，并根据情况安排低频重新激活。",
}


def _display_advice(stage: str | None) -> str:
    english = follow_up_advice(stage or "")
    if is_chinese():
        return FOLLOW_UP_ADVICE_ZH.get(
            stage or "",
            "确认客户当前需求，并约定一个明确的下一步行动。",
        )
    return english


def _localized_selectbox(
    label: str,
    values: list[str],
    *,
    state_key: str,
    default: str,
) -> str:
    labels = {value: option_label(value) for value in values}
    existing_label = st.session_state.get(state_key)
    current = next(
        (
            value
            for value, localized in labels.items()
            if localized == existing_label
        ),
        st.session_state.get(f"{state_key}_value", default),
    )
    st.session_state[state_key] = labels[current]
    selected_label = st.selectbox(label, list(labels.values()), key=state_key)
    selected = next(
        value for value, localized in labels.items() if localized == selected_label
    )
    st.session_state[f"{state_key}_value"] = selected
    return selected


page_header(
    t("page.followup.title"),
    t("page.followup.subtitle"),
    t("page.followup.section"),
)
workflow_rail("follow_up")

customers = list_customers()
today = date.today()

queue_tab, record_tab, history_tab = st.tabs(
    [
        t("followup.tab.queue"),
        t("followup.tab.record"),
        t("followup.tab.history"),
    ]
)

with queue_tab:
    queue = []
    for customer in customers:
        if customer.get("current_stage") in {"Order Confirmed", "Lost"}:
            continue
        due = customer.get("next_follow_up_date")
        queue.append(
            {
                "priority_score": follow_up_priority(
                    customer.get("effective_grade", "D"),
                    due,
                    today,
                ),
                "status": (
                    t("followup.queue.overdue")
                    if due and str(due) < today.isoformat()
                    else t("followup.queue.due")
                ),
                "company": customer["company_name"],
                "grade": customer.get("effective_grade"),
                "stage": customer.get("current_stage"),
                "next_follow_up": due or t("followup.queue.unscheduled"),
                "recommended_action": _display_advice(
                    customer.get("current_stage")
                ),
            }
        )
    queue.sort(key=lambda row: row["priority_score"], reverse=True)
    overdue_count = sum(
        row["status"] == t("followup.queue.overdue") for row in queue
    )
    top_columns = st.columns(3)
    top_columns[0].metric(t("followup.queue.active"), len(queue))
    top_columns[1].metric(t("followup.queue.overdue_metric"), overdue_count)
    top_columns[2].metric(
        t("followup.queue.a_grade"),
        sum(row["grade"] == "A" for row in queue),
    )
    if queue:
        queue_frame = pd.DataFrame(queue)
        if is_chinese():
            queue_frame["stage"] = queue_frame["stage"].map(option_label)
        st.dataframe(
            queue_frame,
            width="stretch",
            hide_index=True,
            column_config={
                "priority_score": t("followup.queue.priority_score"),
                "status": t("followup.queue.status"),
                "company": t("followup.queue.company"),
                "grade": t("followup.queue.grade"),
                "stage": t("followup.queue.stage"),
                "next_follow_up": t("followup.queue.next"),
                "recommended_action": t("followup.queue.action"),
            },
        )
    else:
        st.info(t("followup.queue.empty"))

with record_tab:
    workflow_context = st.session_state.get("workflow_context", {})
    selected_quotation_id = workflow_context.get("quotation_id")
    quotations = [
        record
        for record in list_quotations()
        if record.get("customer_id") and record.get("inquiry_id")
    ]
    quotation_by_id = {record["id"]: record for record in quotations}
    if selected_quotation_id not in quotation_by_id:
        selected_quotation_id = None

    if selected_quotation_id is None and quotations:
        st.info(t("followup.source.info"))
        source_options = {
            (
                f"#{record['id']} · {record.get('product_name') or '—'} · "
                f"{record.get('quotation_date') or '—'}"
            ): record["id"]
            for record in quotations
        }
        selected_source = st.selectbox(
            t("followup.source.select"),
            list(source_options),
            key="followup_source_quotation",
        )
        selected_quotation_id = source_options[selected_source]
        if st.button(
            t("followup.source.load"),
            type="primary",
            key="followup_source_load",
        ):
            selected = quotation_by_id[selected_quotation_id]
            update_workflow_context(
                stage="follow_up",
                customer_id=selected["customer_id"],
                inquiry_id=selected["inquiry_id"],
                product_id=selected.get("product_id"),
                quotation_id=selected_quotation_id,
            )
            for key in (
                "followup_content",
                "followup_outcome",
                "followup_next_date",
                "saved_follow_up_id",
            ):
                st.session_state.pop(key, None)
            st.rerun()

    if selected_quotation_id is None:
        st.warning(t("followup.source.empty"))
        if st.button(
            t("followup.action.return_quote"),
            key="followup_empty_return",
        ):
            st.switch_page("pages/quotation_calculator.py")
    else:
        try:
            inherited = build_follow_up_context(
                selected_quotation_id,
                today=today,
            )
        except ValueError as exc:
            st.error(localize_error(str(exc)))
            inherited = None

        if inherited:
            update_workflow_context(
                stage="follow_up",
                customer_id=inherited["customer_id"],
                customer_name=inherited["customer_name"],
                inquiry_id=inherited["inquiry_id"],
                product_id=inherited["product_id"],
                product=inherited["product_name"],
                quotation_id=inherited["quotation_id"],
            )
            st.subheader(t("followup.context.title"))
            context_frame = pd.DataFrame(
                [
                    {
                        t("followup.context.field"): t(
                            f"followup.context.{field}"
                        ),
                        t("followup.context.value"): value or "—",
                    }
                    for field, value in (
                        ("customer", inherited["customer_name"]),
                        ("stage", option_label(inherited["customer_stage"])),
                        ("inquiry", f"#{inherited['inquiry_id']}"),
                        ("quotation", f"#{inherited['quotation_id']}"),
                        ("product", inherited["product_name"]),
                        (
                            "recommended_date",
                            inherited["recommended_follow_up_date"],
                        ),
                    )
                ]
            )
            st.dataframe(context_frame, width="stretch", hide_index=True)
            st.info(
                t("followup.context.advice")
                + " "
                + _display_advice(inherited["customer_stage"])
            )

            recommended_date = date.fromisoformat(
                inherited["recommended_follow_up_date"]
            )
            with st.form("follow_up_form"):
                form_columns = st.columns(3)
                follow_date = form_columns[0].date_input(
                    t("followup.form.contact_date"),
                    value=today,
                    key="followup_contact_date",
                )
                with form_columns[1]:
                    channel = _localized_selectbox(
                        t("followup.form.channel"),
                        [
                            "Email",
                            "WhatsApp / Chat",
                            "Phone",
                            "Video Call",
                            "Meeting",
                        ],
                        state_key="followup_channel",
                        default="Email",
                    )
                with form_columns[2]:
                    priority = _localized_selectbox(
                        t("followup.form.priority"),
                        ["High", "Medium", "Low"],
                        state_key="followup_priority",
                        default="High",
                    )
                content = st.text_area(
                    t("followup.form.content"),
                    placeholder=t("followup.form.content_placeholder"),
                    key="followup_content",
                )
                outcome = st.text_input(
                    t("followup.form.outcome"),
                    placeholder=t("followup.form.outcome_placeholder"),
                    key="followup_outcome",
                )
                next_date = st.date_input(
                    t("followup.form.next_date"),
                    value=recommended_date,
                    key="followup_next_date",
                )
                save = st.form_submit_button(
                    t("followup.action.save"),
                    type="primary",
                    disabled=bool(st.session_state.get("saved_follow_up_id")),
                )
            if save:
                try:
                    follow_up_id = save_follow_up_for_quotation(
                        inherited["quotation_id"],
                        {
                            "follow_up_date": follow_date.isoformat(),
                            "communication_type": channel,
                            "content": content.strip(),
                            "outcome": outcome.strip(),
                            "next_follow_up_date": next_date.isoformat(),
                            "priority": priority,
                        },
                    )
                    st.session_state["saved_follow_up_id"] = follow_up_id
                    update_workflow_context(follow_up_id=follow_up_id)
                    st.success(
                        t(
                            "followup.save.success",
                            follow_up_id=follow_up_id,
                        )
                    )
                except ValueError as exc:
                    st.error(localize_error(str(exc)))

            customer = next(
                (
                    row
                    for row in customers
                    if row["id"] == inherited["customer_id"]
                ),
                {},
            )
            st.subheader(t("followup.message.title"))
            st.caption(t("followup.message.caption"))
            st.code(
                generate_follow_up_message(
                    customer.get("contact_name", ""),
                    inherited["customer_stage"],
                    inherited["product_name"],
                ),
                language=None,
            )
            if st.session_state.get("saved_follow_up_id"):
                action_columns = st.columns(2)
                if action_columns[0].button(
                    t("followup.action.timeline"),
                    width="stretch",
                    key="followup_view_timeline",
                ):
                    st.switch_page("pages/customers.py")
                if action_columns[1].button(
                    t("followup.action.return_quote"),
                    width="stretch",
                    key="followup_return_quote",
                ):
                    st.switch_page("pages/quotation_calculator.py")

with history_tab:
    history = list_follow_ups()
    if history:
        frame = pd.DataFrame(history)
        columns = [
            column
            for column in (
                "follow_up_date",
                "company_name",
                "inquiry_id",
                "quotation_id",
                "customer_stage",
                "communication_type",
                "content",
                "outcome",
                "next_follow_up_date",
                "priority",
            )
            if column in frame.columns
        ]
        if is_chinese():
            for column in ("customer_stage", "communication_type", "priority"):
                if column in frame:
                    frame[column] = frame[column].map(option_label)
        st.dataframe(frame[columns], width="stretch", hide_index=True)
    else:
        st.info(t("followup.history.empty"))
