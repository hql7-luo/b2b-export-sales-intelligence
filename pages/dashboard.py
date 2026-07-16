"""Executive overview of lead quality, pipeline, and follow-up work."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from components.theme import page_header
from services.dashboard import dashboard_snapshot
from utils.i18n import is_chinese, option_label, t, tr


page_header(
    t("page.analytics.title"),
    t("page.analytics.subtitle"),
    t("page.analytics.section"),
)

snapshot = dashboard_snapshot()
metrics = snapshot["metrics"]
grades = snapshot["grades"]

metric_columns = st.columns(4)
metric_columns[0].metric(tr("Customers", "客户总数"), metrics["total_customers"])
metric_columns[1].metric(tr("New inquiries · 30d", "近 30 天新询盘"), metrics["new_inquiries"])
metric_columns[2].metric(tr("Quoted customers", "已报价客户"), metrics["quoted_customers"])
metric_columns[3].metric(tr("Expected sales", "预计销售额"), f"${metrics['expected_sales']:,.0f}")

metric_columns = st.columns(4)
metric_columns[0].metric(tr("A-grade", "A 级客户"), grades["A"])
metric_columns[1].metric("B / C / D", f"{grades['B']} / {grades['C']} / {grades['D']}")
metric_columns[2].metric(tr("Sample / Won", "样品阶段 / 成交"), f"{metrics['sample_customers']} / {metrics['won_customers']}")
metric_columns[3].metric(tr("Overdue follow-ups", "逾期跟进"), metrics["overdue_follow_ups"])

left, right = st.columns([1.25, 1])
with left:
    st.subheader(tr("Sales funnel", "销售漏斗"))
    funnel_frame = pd.DataFrame(snapshot["funnel"])
    funnel_frame["display_stage"] = funnel_frame["stage"].map(option_label)
    if funnel_frame["customers"].sum():
        figure = px.funnel(
            funnel_frame,
            x="customers",
            y="display_stage",
            color_discrete_sequence=["#0F6B78"],
        )
        figure.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=430)
        st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})
    else:
        st.info(tr("The funnel will appear after customer stages are recorded.", "录入客户阶段后，这里将显示销售漏斗。"))
with right:
    st.subheader(tr("Lead quality", "线索质量"))
    grade_frame = pd.DataFrame({tr("Grade", "等级"): list(grades), tr("Customers", "客户数"): list(grades.values())})
    figure = px.bar(
        grade_frame,
        x=tr("Grade", "等级"),
        y=tr("Customers", "客户数"),
        color=tr("Grade", "等级"),
        color_discrete_map={"A": "#0F6B78", "B": "#4D929A", "C": "#E5A332", "D": "#9AA9AC"},
        text_auto=True,
    )
    figure.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10), height=430)
    st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})

country_col, source_col = st.columns(2)
with country_col:
    st.subheader(tr("Customer countries", "客户国家与地区"))
    country_frame = pd.DataFrame(snapshot["countries"]).head(10)
    figure = px.bar(
        country_frame.sort_values("value"),
        x="value",
        y="label",
        orientation="h",
        color_discrete_sequence=["#0F6B78"],
        labels={"value": tr("Customers", "客户数"), "label": tr("Country", "国家与地区")},
    )
    figure.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=390)
    st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})
with source_col:
    st.subheader(tr("Lead sources", "线索来源"))
    source_frame = pd.DataFrame(snapshot["sources"])
    if is_chinese():
        source_frame["label"] = source_frame["label"].map(option_label)
    figure = px.pie(
        source_frame,
        names="label",
        values="value",
        hole=0.56,
        color_discrete_sequence=["#0F6B78", "#4D929A", "#E5A332", "#6B7D82", "#9CB9BD", "#C9D7D8"],
    )
    figure.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=390, legend=dict(orientation="h"))
    st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})

st.subheader(tr("Follow-up queue · due within 7 days", "未来 7 天跟进队列"))
follow_ups = snapshot["follow_ups"]
if follow_ups:
    frame = pd.DataFrame(follow_ups)
    frame["status"] = frame["overdue"].map(
        {True: tr("OVERDUE", "已逾期"), False: tr("DUE SOON", "即将到期")}
    )
    if is_chinese():
        frame["current_stage"] = frame["current_stage"].map(option_label)
    st.dataframe(
        frame[["status", "company_name", "contact_name", "country", "lead_grade", "current_stage", "next_follow_up_date"]],
        width="stretch",
        hide_index=True,
        column_config={
            "status": tr("Status", "状态"),
            "company_name": tr("Company", "公司"),
            "contact_name": tr("Contact", "联系人"),
            "lead_grade": tr("Grade", "等级"),
            "current_stage": tr("Stage", "阶段"),
            "next_follow_up_date": tr("Next Follow-up", "下次跟进"),
        },
    )
else:
    st.info(tr("No follow-ups are due in the next seven days.", "未来七天没有待跟进事项。"))

st.caption(tr(
    "Expected sales uses each active customer's estimated purchase volume. All demo amounts and records are fictional.",
    "预计销售额基于活跃客户的预估采购金额；所有演示金额和记录均为虚拟数据。",
))
