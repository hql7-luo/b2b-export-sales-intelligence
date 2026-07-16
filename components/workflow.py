"""Shared workflow context and the core three-stage process rail."""

from __future__ import annotations

from typing import Any

import streamlit as st

from utils.i18n import t


WORKFLOW_CONTEXT_KEY = "workflow_context"

WORKFLOW_DEFAULTS = {
    "stage": "analyze",
    "customer_id": None,
    "inquiry_id": None,
    "product_id": None,
    "quotation_id": None,
    "customer_name": "",
    "country": "",
    "product": "",
    "quantity": "",
    "specification": "",
    "destination": "",
    "analysis_result": None,
    "edited_reply": "",
}


def ensure_workflow_context() -> dict[str, Any]:
    """Return a stable cross-page context without overwriting existing values."""
    current = st.session_state.get(WORKFLOW_CONTEXT_KEY)
    if not isinstance(current, dict):
        current = {}
    context = {**WORKFLOW_DEFAULTS, **current}
    st.session_state[WORKFLOW_CONTEXT_KEY] = context
    return context


def update_workflow_context(**changes: Any) -> dict[str, Any]:
    """Update only the supplied temporary hand-off values."""
    context = ensure_workflow_context()
    context.update(changes)
    st.session_state[WORKFLOW_CONTEXT_KEY] = context
    return context


def workflow_rail(active: str) -> None:
    """Render the compact process signature used by the P0 workflow pages."""
    stages = (
        ("analyze", t("workflow.analyze")),
        ("prepare", t("workflow.prepare")),
        ("follow_up", t("workflow.follow_up")),
    )
    stage_keys = [item[0] for item in stages]
    active_index = stage_keys.index(active) if active in stage_keys else 0
    items = []
    for index, (key, label) in enumerate(stages, start=1):
        stage_index = index - 1
        state = "active" if stage_index == active_index else "complete" if stage_index < active_index else "pending"
        items.append(
            f'<div class="workflow-step {state}"><span>{index}</span><strong>{label}</strong></div>'
        )
    st.markdown(
        f'<div class="workflow-rail" aria-label="{t("workflow.aria_label")}">' + "".join(items) + "</div>",
        unsafe_allow_html=True,
    )
