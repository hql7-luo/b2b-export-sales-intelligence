"""Streamlit visual system for the export sales workspace."""

from __future__ import annotations

import streamlit as st


def apply_theme() -> None:
    """Apply the compact, document-led visual system."""
    st.markdown(
        """
        <style>
        :root {
            --navy: #14243A;
            --ink: #1D2939;
            --action: #2563EB;
            --canvas: #F7F8FA;
            --surface: #FFFFFF;
            --line: #D0D5DD;
            --muted: #667085;
            --success: #16803C;
            --warning: #B54708;
            --danger: #B42318;
        }
        .stApp { background: var(--canvas); color: var(--ink); }
        .stMainBlockContainer { max-width: 1180px; padding-top: 4.25rem; padding-bottom: 3rem; }
        [data-testid="stSidebar"] { background: var(--navy); border-right: 1px solid #243751; }
        [data-testid="stSidebar"] * { color: #F8FAFC !important; }
        [data-testid="stSidebarNav"] span { font-weight: 590; }
        [data-testid="stSidebarNav"] a { border-radius: 4px; }
        [data-testid="stSidebarNav"] a[aria-current="page"] { background: #203754; }
        h1, h2, h3 { color: var(--ink); letter-spacing: -0.018em; }
        h1 { font-family: "Avenir Next", "Aptos Display", "Segoe UI", sans-serif; font-size: 2rem; font-weight: 700; }
        p, label, input, textarea, button {
            font-family: "IBM Plex Sans", "PingFang SC", "Noto Sans CJK SC", "Microsoft YaHei", "Segoe UI", sans-serif;
        }
        [data-testid="stSegmentedControl"] {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 4px;
            padding: 2px;
        }
        .workspace-brand { display: flex; align-items: baseline; gap: .7rem; min-height: 34px; }
        .workspace-brand strong { color: var(--navy); font-size: .92rem; letter-spacing: -.01em; }
        .workspace-brand span { color: var(--muted); font-size: .78rem; }
        [data-testid="stMetric"] {
            background: var(--surface);
            border: 1px solid var(--line);
            padding: .85rem 1rem;
            border-radius: 4px;
        }
        [data-testid="stMetricValue"] { color: var(--navy); }
        .workflow-rail {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            margin: .65rem 0 1.5rem;
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 4px;
        }
        .workflow-step { position: relative; display: flex; align-items: center; gap: .6rem; min-height: 52px; padding: .75rem 1rem; color: var(--muted); }
        .workflow-step + .workflow-step { border-left: 1px solid var(--line); }
        .workflow-step span { display: grid; place-items: center; width: 24px; height: 24px; flex: 0 0 24px; border: 1px solid var(--line); border-radius: 3px; font-size: .75rem; font-weight: 700; }
        .workflow-step strong { font-size: .86rem; font-weight: 620; }
        .workflow-step.active { color: var(--action); box-shadow: inset 0 -3px 0 var(--action); }
        .workflow-step.active span { color: #FFFFFF; background: var(--action); border-color: var(--action); }
        .workflow-step.complete { color: var(--navy); }
        .workflow-step.complete span { color: var(--success); border-color: #86C69B; background: #ECFDF3; }
        .eyebrow { color: var(--action); text-transform: uppercase; letter-spacing: .11em; font-size: .7rem; font-weight: 700; }
        .grade-chip { display: inline-block; border-radius: 4px; padding: .16rem .48rem; font-weight: 700; background: #EEF4FF; color: #1849A9; }
        .formula-note { background: var(--surface); border: 1px solid var(--line); border-left: 4px solid var(--action); padding: .8rem 1rem; margin-bottom: 1rem; }
        .empty-guide { border: 1px dashed #98A2B3; background: var(--surface); padding: 1.2rem; border-radius: 4px; }
        .stButton > button, .stDownloadButton > button { border-radius: 4px; font-weight: 620; }
        .stButton > button[kind="primary"] { background: var(--action); border-color: var(--action); }
        div[data-testid="stForm"] { background: var(--surface); border: 1px solid var(--line); padding: 1rem; border-radius: 4px; }
        div[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 4px; overflow: hidden; }
        div[data-testid="stAlert"] { border-radius: 4px; }
        :focus-visible { outline: 3px solid rgba(37, 99, 235, .3) !important; outline-offset: 2px; }
        @media (max-width: 760px) {
            .stMainBlockContainer { padding-top: 3.75rem; }
            .workspace-brand span { display: none; }
            .workflow-rail { grid-template-columns: 1fr; }
            .workflow-step + .workflow-step { border-left: 0; border-top: 1px solid var(--line); }
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
