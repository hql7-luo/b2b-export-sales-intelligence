"""Follow-up queue, communication history, and stage advice."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from components.theme import page_header
from components.workflow import workflow_rail
from database.repository import create_follow_up, get_customer, list_customers, list_follow_ups
from services.followup import follow_up_advice, follow_up_priority, generate_follow_up_message
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
    return FOLLOW_UP_ADVICE_ZH.get(stage or "", "确认客户当前需求，并约定一个明确的下一步行动。") if is_chinese() else english


page_header(
    t("page.followup.title"),
    t("page.followup.subtitle"),
    t("page.followup.section"),
)
workflow_rail("follow_up")

customers = list_customers()
today = date.today()

queue_tab, record_tab, history_tab = st.tabs([tr("Priority queue", "优先队列"), tr("Record follow-up", "记录跟进"), tr("History", "沟通历史")])

with queue_tab:
    queue = []
    for customer in customers:
        if customer.get("current_stage") in {"Order Confirmed", "Lost"}:
            continue
        due = customer.get("next_follow_up_date")
        queue.append(
            {
                "priority_score": follow_up_priority(customer.get("effective_grade", "D"), due, today),
                "status": tr("OVERDUE", "已逾期") if due and str(due) < today.isoformat() else tr("DUE / UNSCHEDULED", "待跟进 / 未安排"),
                "company": customer["company_name"],
                "grade": customer.get("effective_grade"),
                "stage": customer.get("current_stage"),
                "next_follow_up": due or tr("Not scheduled", "未安排"),
                "recommended_action": _display_advice(customer.get("current_stage")),
            }
        )
    queue.sort(key=lambda row: row["priority_score"], reverse=True)
    overdue_count = sum(row["status"] == tr("OVERDUE", "已逾期") for row in queue)
    top_cols = st.columns(3)
    top_cols[0].metric(tr("Active follow-ups", "活跃跟进"), len(queue))
    top_cols[1].metric(tr("Overdue", "已逾期"), overdue_count)
    top_cols[2].metric(tr("A-grade active", "活跃 A 级客户"), sum(row["grade"] == "A" for row in queue))
    if queue:
        queue_frame = pd.DataFrame(queue)
        if is_chinese():
            queue_frame["stage"] = queue_frame["stage"].map(option_label)
        st.dataframe(
            queue_frame,
            width="stretch",
            hide_index=True,
            column_config={
                "priority_score": tr("Priority score", "优先级分数"),
                "status": tr("Status", "状态"),
                "company": tr("Company", "公司"),
                "grade": tr("Grade", "等级"),
                "stage": tr("Stage", "阶段"),
                "next_follow_up": tr("Next follow-up", "下次跟进"),
                "recommended_action": tr("Recommended action", "建议行动"),
            },
        )
    else:
        st.info(tr("No active leads require follow-up.", "当前没有需要跟进的活跃客户。"))

with record_tab:
    if not customers:
        st.info(tr("Add a customer before recording communication.", "请先添加客户，再记录沟通。"))
    else:
        labels = {row["id"]: f"{row['company_name']} · {row.get('current_stage')}" for row in customers}
        selected_id = st.selectbox(tr("Customer", "客户"), list(labels), format_func=labels.get)
        customer = get_customer(selected_id)
        st.markdown(f"**{tr('Recommended action', '建议行动')}：** {_display_advice(customer.get('current_stage'))}")
        with st.form("follow_up_form", clear_on_submit=True):
            form_cols = st.columns(3)
            follow_date = form_cols[0].date_input(tr("Contact Date", "联系日期"), value=today)
            channel = form_cols[1].selectbox(tr("Communication Type", "沟通方式"), ["Email", "WhatsApp / Chat", "Phone", "Video Call", "Meeting"], format_func=option_label)
            priority = form_cols[2].selectbox(tr("Priority", "优先级"), ["High", "Medium", "Low"], format_func=option_label)
            content = st.text_area(tr("Communication Content *", "沟通内容 *"), placeholder=tr("What was discussed or sent?", "记录讨论或发送的内容"))
            outcome = st.text_input(tr("Outcome", "沟通结果"), placeholder=tr("Example: Customer reviewing sample", "例如：客户正在评估样品"))
            next_date = st.date_input(tr("Next Follow-up Date", "下次跟进日期"), value=today + timedelta(days=3))
            save = st.form_submit_button(tr("Save follow-up", "保存跟进记录"), type="primary")
        if save:
            try:
                follow_up_id = create_follow_up(
                    {
                        "customer_id": selected_id,
                        "follow_up_date": follow_date.isoformat(),
                        "communication_type": channel,
                        "content": content.strip(),
                        "outcome": outcome.strip(),
                        "next_follow_up_date": next_date.isoformat(),
                        "priority": priority,
                    }
                )
                st.success(tr(f"Follow-up #{follow_up_id} saved and the customer's next date was updated.", f"跟进记录 #{follow_up_id} 已保存，并更新了客户的下次跟进日期。"))
                st.rerun()
            except ValueError as exc:
                st.error(localize_error(str(exc)))

        st.subheader(tr("Suggested English message", "英文跟进消息建议"))
        st.code(
            generate_follow_up_message(
                customer.get("contact_name", ""),
                customer.get("current_stage", ""),
                customer.get("product_interest", ""),
            ),
            language=None,
        )

with history_tab:
    history = list_follow_ups()
    if history:
        frame = pd.DataFrame(history)
        columns = [
            column
            for column in ("follow_up_date", "company_name", "communication_type", "content", "outcome", "next_follow_up_date", "priority")
            if column in frame.columns
        ]
        st.dataframe(
            frame[columns],
            width="stretch",
            hide_index=True,
            column_config={
                "follow_up_date": tr("Follow-up date", "联系日期"),
                "company_name": tr("Company", "公司"),
                "communication_type": tr("Communication type", "沟通方式"),
                "content": tr("Content", "沟通内容"),
                "outcome": tr("Outcome", "沟通结果"),
                "next_follow_up_date": tr("Next follow-up", "下次跟进"),
                "priority": tr("Priority", "优先级"),
            },
        )
    else:
        st.info(tr("No communication history has been recorded.", "暂无沟通历史。"))
