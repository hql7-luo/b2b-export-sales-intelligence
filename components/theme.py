"""Streamlit visual system for the export operations console."""

from __future__ import annotations

import streamlit as st

from utils.i18n import tr


def apply_theme() -> None:
    """Apply restrained portfolio-ready styling."""
    st.markdown(
        """
        <style>
        :root {
            --ink: #17313A;
            --harbor: #0F6B78;
            --harbor-dark: #0A4B55;
            --mist: #E8F0F1;
            --paper: #F5F8F8;
            --signal: #E5A332;
            --line: #CEDCDD;
        }
        .stApp { background: var(--paper); color: var(--ink); }
        [data-testid="stSidebar"] { background: #102F38; }
        [data-testid="stSidebar"] * { color: #F6FBFB !important; }
        [data-testid="stSidebarNav"] span { font-weight: 600; }
        h1, h2, h3 { color: var(--ink); letter-spacing: -0.025em; }
        h1 { font-family: "Avenir Next", "Segoe UI", sans-serif; font-weight: 750; }
        p, label, input, textarea, button {
            font-family: "IBM Plex Sans", "PingFang SC", "Noto Sans CJK SC", "Microsoft YaHei", "Segoe UI", sans-serif;
        }
        [data-testid="stSegmentedControl"] {
            background: white;
            border: 1px solid var(--line);
            border-radius: 999px;
            padding: 2px;
            box-shadow: 0 5px 18px rgba(15, 107, 120, .08);
        }
        [data-testid="stMetric"] {
            background: white;
            border: 1px solid var(--line);
            border-top: 3px solid var(--harbor);
            padding: 1rem;
            border-radius: 0.35rem;
        }
        [data-testid="stMetricValue"] { color: var(--harbor-dark); }
        .export-ledger {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 1px;
            background: var(--line);
            border: 1px solid var(--line);
            margin: 0.25rem 0 1.5rem 0;
        }
        .export-ledger > div { background: white; padding: .7rem .9rem; }
        .export-ledger small { display: block; color: #6A7F85; text-transform: uppercase; letter-spacing: .08em; }
        .export-ledger strong { color: var(--ink); font-size: .92rem; }
        .eyebrow { color: var(--harbor); text-transform: uppercase; letter-spacing: .13em; font-size: .72rem; font-weight: 700; }
        .grade-chip { display: inline-block; border-radius: 999px; padding: .16rem .55rem; font-weight: 700; background: var(--mist); color: var(--harbor-dark); }
        .formula-note { background: white; border-left: 4px solid var(--signal); padding: .8rem 1rem; margin-bottom: 1rem; }
        .empty-guide { border: 1px dashed #9FB7BA; background: white; padding: 1.2rem; border-radius: .35rem; }
        .stButton > button, .stDownloadButton > button { border-radius: .3rem; font-weight: 650; }
        .stButton > button[kind="primary"] { background: var(--harbor); border-color: var(--harbor); }
        div[data-testid="stForm"] { background: white; border: 1px solid var(--line); padding: 1rem; border-radius: .4rem; }
        @media (max-width: 760px) {
            .export-ledger { grid-template-columns: 1fr 1fr; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str, section: str) -> None:
    """Render consistent page title and business context."""
    st.markdown(f'<div class="eyebrow">{section}</div>', unsafe_allow_html=True)
    st.title(title)
    st.caption(subtitle)


def operations_ledger() -> None:
    """Signature element: a compact export-decision ledger."""
    st.markdown(
        f"""
        <div class="export-ledger">
          <div><small>{tr("Workflow", "业务流程")}</small><strong>{tr("Lead → Order", "线索 → 订单")}</strong></div>
          <div><small>{tr("Pricing base", "计价基础")}</small><strong>{tr("CNY costs", "人民币成本")}</strong></div>
          <div><small>{tr("Quote currency", "报价币种")}</small><strong>{tr("USD default", "默认美元")}</strong></div>
          <div><small>{tr("Decision model", "决策模型")}</small><strong>{tr("Explainable rules", "可解释规则")}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
