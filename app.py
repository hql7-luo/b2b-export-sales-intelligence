"""Application entrypoint and navigation router."""

from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv

from components.theme import apply_theme
from components.workflow import ensure_workflow_context
from database.connection import DEFAULT_DB_PATH
from database.init_db import initialize_database
from database.seed_data import seed_demo_data
from utils.i18n import LANGUAGE_KEY, t

load_dotenv()
st.session_state.setdefault(LANGUAGE_KEY, "en")
language_control_key = "_ui_language_control"
control_language = st.session_state.get(language_control_key)
if control_language in {"en", "zh"}:
    st.session_state[LANGUAGE_KEY] = control_language
st.session_state[language_control_key] = st.session_state[LANGUAGE_KEY]
ensure_workflow_context()

st.set_page_config(
    page_title=t("app.page_title"),
    layout="wide",
    initial_sidebar_state="auto",
)

# 首次启动时创建演示库；之后尊重用户对数据的修改和删除。
is_first_run = not DEFAULT_DB_PATH.exists()
initialize_database()
if is_first_run:
    seed_demo_data()
apply_theme()

language_space, language_control = st.columns([8.5, 1.5], vertical_alignment="center")
with language_space:
    st.markdown(
        f'<div class="workspace-brand"><strong>{t("app.sidebar.title")}</strong><span>{t("app.sidebar.subtitle")}</span></div>',
        unsafe_allow_html=True,
    )
with language_control:
    selected_language = st.segmented_control(
        t("app.language.label"),
        options=["en", "zh"],
        format_func=lambda value: "EN" if value == "en" else "中文",
        key=language_control_key,
        label_visibility="collapsed",
        width="stretch",
    )
    if selected_language in {"en", "zh"}:
        st.session_state[LANGUAGE_KEY] = selected_language

pages = {
    t("nav.group.workflow"): [
        st.Page("pages/inquiry_analyzer.py", title=t("nav.analyze"), default=True),
        st.Page("pages/customers.py", title=t("nav.customers")),
        st.Page("pages/quotation_calculator.py", title=t("nav.quotations")),
        st.Page("pages/follow_up_tracker.py", title=t("nav.followups")),
    ],
    t("nav.group.reference"): [
        st.Page("pages/products.py", title=t("nav.products")),
        st.Page("pages/dashboard.py", title=t("nav.analytics")),
        st.Page("pages/settings.py", title=t("nav.settings")),
    ],
}

current_page = st.navigation(pages, expanded=True)
current_page.run()
