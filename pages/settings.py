"""Workspace settings and safe fictional demo-data controls."""

from __future__ import annotations

import streamlit as st

from components.theme import page_header
from database.seed_data import seed_demo_data
from utils.i18n import t, tr


page_header(
    t("page.settings.title"),
    t("page.settings.subtitle"),
    t("page.settings.section"),
)

status_cols = st.columns(3)
status_cols[0].metric(t("settings.storage.title"), t("settings.storage.value"))
status_cols[1].metric(t("settings.currency"), "USD")
status_cols[2].metric(t("settings.pricing_default"), tr("Gross Margin", "毛利率"))

st.caption(t("settings.storage.caption"))
if st.button(t("settings.demo.button")):
    counts = seed_demo_data()
    st.success(t("settings.demo.ready", counts=", ".join(f"{name}={count}" for name, count in counts.items())))

st.subheader(t("settings.quotation.title"))
st.write(t("settings.quotation.exchange"))
st.write(t("settings.quotation.margin"))
st.write(t("settings.quotation.markup"))

st.subheader(t("settings.privacy.title"))
st.success(t("settings.privacy.message"))
