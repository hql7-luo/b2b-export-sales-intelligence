"""Inquiry and RFQ analysis workspace."""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from components.theme import page_header
from components.workflow import update_workflow_context, workflow_rail
from database.repository import create_inquiry, list_customers, list_inquiries, list_products
from services.inquiry_analyzer import analyze_inquiry
from services.inquiry_brief import build_inquiry_brief
from services.product_match import recommend_products
from utils.i18n import LANGUAGE_KEY, localize_error, t, tr


page_header(
    t("page.inquiry.title"),
    t("page.inquiry.subtitle"),
    t("page.inquiry.section"),
)
workflow_rail("analyze")

api_key = os.getenv("OPENAI_API_KEY", "").strip()
model = os.getenv("OPENAI_MODEL", "gpt-5-mini").strip() or "gpt-5-mini"
analyze_tab, history_tab = st.tabs([tr("Analyze inquiry", "分析询盘"), tr("Saved analyses", "已保存分析")])

with analyze_tab:
    sample = (
        "Hello, we need 5,000 custom hardcover notebooks with our logo, A5 size and recycled paper. "
        "Please pack each notebook in a paper sleeve and deliver to Hamburg, Germany by 15 October. "
        "Could you quote a pre-production sample and advise T/T payment terms?"
    )
    st.session_state.setdefault("inquiry_input", "")
    if st.button(t("inquiry.demo.load"), key="load_demo_inquiry"):
        st.session_state["inquiry_input"] = sample
        st.session_state.pop("inquiry_run", None)
        st.session_state.pop("saved_inquiry_id", None)
        st.session_state.pop("matched_product_id", None)
        st.toast(t("inquiry.demo.loaded"))
    inquiry_text = st.text_area(
        t("inquiry.input.label"),
        height=210,
        max_chars=20_000,
        help=t("inquiry.input.help"),
        key="inquiry_input",
    )
    use_ai = st.toggle(tr("Use enhanced analysis when available", "可用时使用增强分析"), value=False, disabled=not api_key, key="use_enhanced_analysis")
    ai_consent = False
    if use_ai:
        st.warning(tr("Enhanced analysis sends the inquiry text to the configured external service. Remove confidential data first.", "增强分析会将询盘文本发送到已配置的外部服务；请先移除机密信息。"))
        ai_consent = st.checkbox(tr("I confirm this text is authorized for external processing", "我确认该文本已获授权，可用于外部处理"), key="external_processing_consent")
    if st.button(t("inquiry.action.analyze"), type="primary", key="analyze_inquiry"):
        if use_ai and not ai_consent:
            st.error(tr("Confirm external processing or turn off enhanced analysis.", "请确认外部处理授权，或关闭增强分析。"))
        else:
            try:
                run = analyze_inquiry(inquiry_text, api_key=api_key if use_ai else None, model=model)
                st.session_state["inquiry_run"] = run
                st.session_state["inquiry_text"] = inquiry_text
                st.session_state["suggested_reply_editor"] = run.result.get(
                    "suggested_reply",
                    "",
                )
                st.session_state.pop("saved_inquiry_id", None)
                st.session_state.pop("matched_product_id", None)
                update_workflow_context(
                    stage="analyze",
                    product=run.result["extracted_fields"].get("product") or "",
                    quantity=run.result["extracted_fields"].get("quantity") or "",
                    specification=run.result["extracted_fields"].get("specification") or "",
                    destination=run.result["extracted_fields"].get("destination") or "",
                    analysis_result=run.result,
                    edited_reply=run.result.get("suggested_reply", ""),
                )
            except ValueError as exc:
                st.error(localize_error(str(exc)))

    if "inquiry_run" in st.session_state:
        run = st.session_state["inquiry_run"]
        result = run.result
        language = st.session_state.get(LANGUAGE_KEY, "en")
        brief = build_inquiry_brief(
            result,
            raw_text=st.session_state.get("inquiry_text", inquiry_text),
            language=language,
        )
        is_enhanced = run.mode == "AI"
        mode_col, score_col, missing_col = st.columns(3)
        mode_col.metric(
            t("inquiry.analysis.mode"),
            t(
                "inquiry.analysis.enhanced"
                if is_enhanced
                else "inquiry.analysis.local"
            ),
        )
        score_col.metric(
            t("inquiry.metric.completeness"),
            f"{result['completeness_score']}/100",
        )
        missing_count = sum(
            len(group["items"]) for group in brief["missing_groups"]
        )
        missing_col.metric(t("inquiry.metric.missing"), missing_count)
        st.caption(
            t(
                "inquiry.analysis.complete_enhanced"
                if is_enhanced
                else "inquiry.analysis.complete_local"
            )
        )

        st.subheader(t("inquiry.summary.title"))
        st.caption(t("inquiry.summary.caption"))
        summary_frame = pd.DataFrame(
            [
                {
                    t("inquiry.summary.field"): t(f"inquiry.field.{field}"),
                    t("inquiry.summary.value"): value,
                }
                for field, value in brief["summary"].items()
            ]
        )
        st.dataframe(summary_frame, width="stretch", hide_index=True)

        st.subheader(t("inquiry.missing.title"))
        missing_columns = st.columns(3)
        for column, group in zip(missing_columns, brief["missing_groups"]):
            with column:
                with st.container(border=True):
                    st.markdown(f"**{group['title']}**")
                    st.caption(group["description"])
                    if group["items"]:
                        for item in group["items"]:
                            st.write(f"- {item['label']}")
                    else:
                        st.caption(t("inquiry.missing.none"))

        risk_col, question_col = st.columns(2)
        with risk_col:
            st.subheader(t("inquiry.risks.title"))
            if brief["risks"]:
                for risk in brief["risks"]:
                    message = (
                        f"**{risk['category_label']} · "
                        f"{risk['severity_label']}** — {risk['message']}"
                    )
                    if risk["severity"] == "high":
                        st.error(message)
                    elif risk["severity"] == "medium":
                        st.warning(message)
                    else:
                        st.info(message)
            else:
                st.success(t("inquiry.risks.none"))
        with question_col:
            st.subheader(t("inquiry.questions.title"))
            for index, question in enumerate(brief["questions"], start=1):
                st.write(f"{index}. {question['text']}")

        products = list_products()
        matches = recommend_products(st.session_state["inquiry_text"], products)
        st.subheader(t("inquiry.products.title"))
        st.caption(t("inquiry.products.caption"))
        if matches:
            match_by_id = {match["id"]: match for match in matches}
            match_ids = list(match_by_id)
            context_product_id = st.session_state.get("workflow_context", {}).get(
                "product_id"
            )
            if (
                "matched_product_id" not in st.session_state
                or st.session_state["matched_product_id"] not in match_ids
            ):
                st.session_state["matched_product_id"] = (
                    context_product_id
                    if context_product_id in match_ids
                    else match_ids[0]
                )
            selected_product_id = st.selectbox(
                t("inquiry.products.select"),
                match_ids,
                format_func=lambda product_id: match_by_id[product_id][
                    "product_name"
                ],
                key="matched_product_id",
            )
            selected_match = match_by_id[selected_product_id]
            shared_terms = ", ".join(
                reason.replace("Shared keyword: ", "")
                for reason in selected_match["match_reasons"]
            )
            st.write(
                f"**{selected_match['product_name']}** · "
                f"{t('inquiry.products.score', score=selected_match['match_score'])}"
            )
            st.caption(t("inquiry.products.reason", terms=shared_terms))
            update_workflow_context(
                product_id=selected_product_id,
                product=selected_match["product_name"],
            )
        else:
            selected_product_id = None
            st.caption(t("inquiry.products.none"))
            update_workflow_context(product_id=None)

        st.subheader(t("inquiry.reply.title"))
        st.caption(t("inquiry.reply.caption"))
        st.session_state.setdefault(
            "suggested_reply_editor",
            result.get("suggested_reply", ""),
        )
        edited_reply = st.text_area(
            t("inquiry.reply.label"),
            height=260,
            key="suggested_reply_editor",
        )
        update_workflow_context(edited_reply=edited_reply)

        st.subheader(t("inquiry.next.title"))
        next_action_columns = st.columns(3)
        for column, action in zip(next_action_columns, brief["next_actions"]):
            with column:
                with st.container(border=True):
                    st.markdown(f"**{action['title']}**")
                    st.caption(action["text"])

        customers = list_customers()
        customer_by_id = {row["id"]: row for row in customers}
        options = {
            0: t("inquiry.customer.none"),
            **{
                customer_id: customer["company_name"]
                for customer_id, customer in customer_by_id.items()
            },
        }
        context_customer_id = st.session_state.get("workflow_context", {}).get(
            "customer_id"
        )
        if (
            "inquiry_customer_selection" not in st.session_state
            or st.session_state["inquiry_customer_selection"] not in options
        ):
            st.session_state["inquiry_customer_selection"] = (
                context_customer_id if context_customer_id in options else 0
            )
        selected_customer = st.selectbox(
            t("inquiry.customer.select"),
            list(options),
            format_func=options.get,
            key="inquiry_customer_selection",
        )
        linked_customer = selected_customer or None
        update_workflow_context(
            customer_id=linked_customer,
            customer_name=(
                customer_by_id[linked_customer]["company_name"]
                if linked_customer in customer_by_id
                else ""
            ),
        )
        save_column, quote_column = st.columns(2)
        if save_column.button(
            t("inquiry.action.save"),
            type="primary",
            width="stretch",
            key="save_inquiry",
        ):
            analysis_to_save = {**result, "suggested_reply": edited_reply}
            inquiry_id = create_inquiry(
                customer_id=linked_customer,
                raw_text=st.session_state["inquiry_text"],
                analysis=analysis_to_save,
                analysis_mode=run.mode,
            )
            st.session_state["saved_inquiry_id"] = inquiry_id
            update_workflow_context(
                inquiry_id=inquiry_id,
                customer_id=linked_customer,
                product_id=selected_product_id,
                analysis_result=analysis_to_save,
                edited_reply=edited_reply,
            )
            st.success(t("inquiry.save.success", inquiry_id=inquiry_id))
        saved_inquiry_id = st.session_state.get("saved_inquiry_id")
        if quote_column.button(
            t("inquiry.action.prepare_quote"),
            width="stretch",
            key="prepare_quotation",
            disabled=not (saved_inquiry_id and linked_customer),
        ):
            update_workflow_context(stage="prepare")
            st.switch_page("pages/quotation_calculator.py")
        if saved_inquiry_id and not linked_customer:
            st.info(t("inquiry.save.customer_required"))
        elif not saved_inquiry_id:
            st.caption(t("inquiry.save.first"))

with history_tab:
    saved = list_inquiries()
    if saved:
        display = pd.DataFrame(saved)
        columns = [
            column
            for column in ("id", "inquiry_date", "product", "quantity", "destination", "completeness_score", "analysis_mode")
            if column in display.columns
        ]
        st.dataframe(
            display[columns],
            width="stretch",
            hide_index=True,
            column_config={
                "inquiry_date": tr("Inquiry date", "询盘日期"),
                "product": tr("Product", "产品"),
                "quantity": tr("Quantity", "数量"),
                "destination": tr("Destination", "目的地"),
                "completeness_score": tr("Completeness", "完整度"),
                "analysis_mode": tr("Analysis mode", "分析模式"),
            },
        )
    else:
        st.info(tr("No inquiry analyses have been saved.", "暂无已保存的询盘分析。"))
