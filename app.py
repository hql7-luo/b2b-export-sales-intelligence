"""Application entrypoint and navigation router."""

from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv

from components.theme import apply_theme
from database.connection import DEFAULT_DB_PATH
from database.init_db import initialize_database
from database.seed_data import seed_demo_data
from utils.i18n import LANGUAGE_KEY, tr

load_dotenv()
st.session_state.setdefault(LANGUAGE_KEY, "en")

st.set_page_config(
    page_title=tr("Export Sales Intelligence", "出口销售智能系统"),
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 首次启动时创建演示库；之后尊重用户对数据的修改和删除。
is_first_run = not DEFAULT_DB_PATH.exists()
initialize_database()
if is_first_run:
    seed_demo_data()
apply_theme()

language_space, language_control = st.columns([8.5, 1.5], vertical_alignment="center")
with language_control:
    st.segmented_control(
        "Language / 语言",
        options=["en", "zh"],
        format_func=lambda value: "EN" if value == "en" else "中文",
        key=LANGUAGE_KEY,
        label_visibility="collapsed",
        width="stretch",
    )

with st.sidebar:
    st.markdown(tr("## Export Intelligence", "## 出口销售智能"))
    st.caption(tr("Lead-to-order decision workspace", "从线索到订单的决策工作台"))

pages = {
    tr("Sales workspace", "销售工作台"): [
        st.Page("pages/dashboard.py", title=tr("Dashboard", "仪表盘"), icon="📊", default=True),
        st.Page("pages/customers.py", title=tr("Customer Management", "客户管理"), icon="🏢"),
        st.Page("pages/inquiry_analyzer.py", title=tr("Inquiry Analyzer", "询盘分析"), icon="🔎"),
        st.Page("pages/quotation_calculator.py", title=tr("Quotation Calculator", "报价计算器"), icon="🧮"),
        st.Page("pages/follow_up_tracker.py", title=tr("Follow-up Tracker", "客户跟进"), icon="📅"),
    ],
    tr("Reference", "业务资料"): [
        st.Page("pages/products.py", title=tr("Product Knowledge Base", "产品知识库"), icon="📚"),
        st.Page("pages/settings.py", title=tr("Settings", "设置"), icon="⚙️"),
    ],
}

current_page = st.navigation(pages, expanded=True)
current_page.run()
