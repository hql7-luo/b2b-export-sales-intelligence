"""Decision-focused sales analytics."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from components.theme import page_header
from services.dashboard import dashboard_snapshot
from utils.i18n import is_chinese, option_label, t


QUALITY_BANDS = (
    "high_potential",
    "qualified",
    "developing",
    "low_signal",
)


page_header(
    t("page.analytics.title"),
    t("page.analytics.subtitle"),
    t("page.analytics.section"),
)

snapshot = dashboard_snapshot()
metrics = snapshot["metrics"]
if snapshot["demo_data_notice"]:
    st.warning(t("analytics.demo.limit"))

metric_columns = st.columns(4)
metric_columns[0].metric(
    t("analytics.metric.customers"),
    metrics["total_customers"],
)
metric_columns[1].metric(
    t("analytics.metric.overdue"),
    metrics["overdue_follow_ups"],
)
metric_columns[2].metric(
    t("analytics.metric.inquiry_to_quote"),
    f"{metrics['inquiry_to_quote_conversion']:.1f}%",
)
metric_columns[3].metric(
    t("analytics.metric.quote_to_won"),
    f"{metrics['quotation_to_won_conversion']:.1f}%",
)

left, right = st.columns([1.2, 1])
with left:
    st.subheader(t("analytics.funnel.title"))
    funnel_frame = pd.DataFrame(snapshot["funnel"])
    if not funnel_frame.empty and funnel_frame["customers"].sum():
        funnel_frame["display_stage"] = funnel_frame["stage"].map(option_label)
        figure = px.funnel(
            funnel_frame,
            x="customers",
            y="display_stage",
            color_discrete_sequence=["#2563EB"],
        )
        figure.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=390,
            yaxis_title=None,
        )
        st.plotly_chart(
            figure,
            width="stretch",
            config={"displayModeBar": False},
        )
    else:
        st.info(t("analytics.funnel.empty"))

with right:
    st.subheader(t("analytics.quality.title"))
    quality_frame = pd.DataFrame(
        [
            {
                "band": t(f"lead_quality.band.{band}"),
                "customers": snapshot["lead_quality"][band],
            }
            for band in QUALITY_BANDS
        ]
    )
    figure = px.bar(
        quality_frame,
        x="band",
        y="customers",
        color="band",
        text_auto=True,
        color_discrete_sequence=[
            "#155EEF",
            "#0E9384",
            "#F79009",
            "#667085",
        ],
    )
    figure.update_layout(
        showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10),
        height=390,
        xaxis_title=None,
        yaxis_title=t("analytics.axis.customers"),
    )
    st.plotly_chart(
        figure,
        width="stretch",
        config={"displayModeBar": False},
    )
    st.caption(t("analytics.quality.caption"))

country_column, source_column = st.columns(2)
with country_column:
    st.subheader(t("analytics.country.title"))
    country_frame = pd.DataFrame(snapshot["countries"]).head(10)
    if country_frame.empty:
        st.info(t("analytics.country.empty"))
    else:
        figure = px.bar(
            country_frame.sort_values("value"),
            x="value",
            y="label",
            orientation="h",
            color_discrete_sequence=["#2563EB"],
            labels={
                "value": t("analytics.axis.customers"),
                "label": t("analytics.axis.country"),
            },
        )
        figure.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=360,
        )
        st.plotly_chart(
            figure,
            width="stretch",
            config={"displayModeBar": False},
        )

with source_column:
    st.subheader(t("analytics.source.title"))
    source_frame = pd.DataFrame(snapshot["sources"])
    if source_frame.empty:
        st.info(t("analytics.source.empty"))
    else:
        if is_chinese():
            source_frame["label"] = source_frame["label"].map(option_label)
        figure = px.bar(
            source_frame.sort_values("value"),
            x="value",
            y="label",
            orientation="h",
            color_discrete_sequence=["#0E9384"],
            labels={
                "value": t("analytics.axis.customers"),
                "label": t("analytics.axis.source"),
            },
        )
        figure.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=360,
        )
        st.plotly_chart(
            figure,
            width="stretch",
            config={"displayModeBar": False},
        )

st.caption(t("analytics.definition.caption"))
