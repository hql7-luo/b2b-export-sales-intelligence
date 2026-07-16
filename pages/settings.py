"""Workspace settings and safe fictional demo-data controls."""

from __future__ import annotations

import os

import streamlit as st

from components.theme import page_header
from database.repository import get_setting, set_setting
from database.seed_data import reset_demo_data, seed_demo_data
from utils.i18n import localize_error, t


page_header(
    t("page.settings.title"),
    t("page.settings.subtitle"),
    t("page.settings.section"),
)

current_rate = float(get_setting("default_exchange_rate") or "7.20")
status_columns = st.columns(3)
status_columns[0].metric(
    t("settings.storage.title"),
    t("settings.storage.value"),
)
status_columns[1].metric(
    t("settings.exchange.metric"),
    f"{current_rate:.2f}",
    help=t("settings.exchange.definition"),
)
status_columns[2].metric(
    t("settings.api.title"),
    t("settings.api.configured")
    if os.getenv("OPENAI_API_KEY")
    else t("settings.api.local"),
)

st.subheader(t("settings.exchange.title"))
st.caption(t("settings.exchange.definition"))
with st.form("settings_exchange_form"):
    default_exchange_rate = st.number_input(
        t("settings.exchange.input"),
        min_value=0.01,
        value=current_rate,
        step=0.01,
        format="%.4f",
    )
    save_exchange_rate = st.form_submit_button(
        t("settings.exchange.save"),
        type="primary",
    )
if save_exchange_rate:
    try:
        set_setting("default_exchange_rate", default_exchange_rate)
        st.success(t("settings.exchange.saved"))
        st.rerun()
    except ValueError as exc:
        st.error(localize_error(str(exc)))
st.info(t("settings.exchange.quote_override"))

st.subheader(t("settings.demo.title"))
st.caption(t("settings.demo.caption"))
demo_columns = st.columns(2)
if demo_columns[0].button(
    t("settings.demo.ensure"),
    width="stretch",
):
    counts = seed_demo_data()
    st.success(
        t(
            "settings.demo.ready",
            counts=", ".join(
                f"{name}={count}" for name, count in counts.items()
            ),
        )
    )
if demo_columns[1].button(
    t("settings.demo.reset"),
    width="stretch",
):
    st.session_state["confirm_demo_reset"] = True
if st.session_state.get("confirm_demo_reset"):
    st.warning(t("settings.demo.reset_warning"))
    confirm_columns = st.columns(2)
    if confirm_columns[0].button(
        t("settings.demo.confirm"),
        type="primary",
        width="stretch",
    ):
        counts = reset_demo_data()
        st.session_state.pop("confirm_demo_reset", None)
        st.success(
            t(
                "settings.demo.reset_success",
                counts=", ".join(
                    f"{name}={count}" for name, count in counts.items()
                ),
            )
        )
        st.rerun()
    if confirm_columns[1].button(
        t("common.cancel"),
        width="stretch",
    ):
        st.session_state.pop("confirm_demo_reset", None)
        st.rerun()

with st.expander(t("settings.advanced.title"), expanded=False):
    st.write(t("settings.storage.caption"))
    st.write(t("settings.quotation.margin"))
    st.write(t("settings.quotation.markup"))
    st.success(t("settings.privacy.message"))
