"""Inquiry and RFQ analysis workspace."""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from components.theme import page_header
from components.workflow import update_workflow_context, workflow_rail
from database.repository import create_inquiry, list_customers, list_inquiries, list_products
from services.inquiry_analyzer import analyze_inquiry
from services.product_match import recommend_products
from utils.i18n import field_label, localize_error, t, tr


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
    if st.button(tr("Load fictional demo inquiry", "载入虚拟演示询盘"), key="load_demo_inquiry"):
        st.session_state["inquiry_input"] = sample
    inquiry_text = st.text_area(
        tr("English inquiry or RFQ *", "英文询盘或 RFQ *"),
        height=210,
        max_chars=20_000,
        help=tr("Maximum 20,000 characters. Remove confidential personal or company data before external processing.", "最多 20,000 个字符；如使用外部处理，请先移除个人或公司的机密信息。"),
        key="inquiry_input",
    )
    use_ai = st.toggle(tr("Use enhanced analysis when available", "可用时使用增强分析"), value=False, disabled=not api_key, key="use_enhanced_analysis")
    ai_consent = False
    if use_ai:
        st.warning(tr("Enhanced analysis sends the inquiry text to the configured external service. Remove confidential data first.", "增强分析会将询盘文本发送到已配置的外部服务；请先移除机密信息。"))
        ai_consent = st.checkbox(tr("I confirm this text is authorized for external processing", "我确认该文本已获授权，可用于外部处理"), key="external_processing_consent")
    if st.button(tr("Analyze requirements", "分析需求"), type="primary", key="analyze_inquiry"):
        if use_ai and not ai_consent:
            st.error(tr("Confirm external processing or turn off enhanced analysis.", "请确认外部处理授权，或关闭增强分析。"))
        else:
            try:
                run = analyze_inquiry(inquiry_text, api_key=api_key if use_ai else None, model=model)
                st.session_state["inquiry_run"] = run
                st.session_state["inquiry_text"] = inquiry_text
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
        mode_col, score_col, missing_col = st.columns(3)
        mode_col.metric(tr("Analysis mode", "分析模式"), tr("Enhanced" if run.mode == "ai" else "Local rules", "增强分析" if run.mode == "ai" else "本地规则"))
        score_col.metric(tr("Completeness", "完整度"), f"{result['completeness_score']}/100")
        missing_col.metric(tr("Missing fields", "缺失字段"), len(result["missing_info"]))
        st.caption(tr("Analysis completed using enhanced processing." if run.mode == "ai" else "Analysis completed using local rules.", "分析已完成；当前使用增强处理。" if run.mode == "ai" else "分析已完成；当前使用本地规则。"))

        st.subheader(tr("Extracted requirements", "提取的需求"))
        extracted = pd.DataFrame(
            [
                {tr("Field", "字段"): field_label(key), tr("Extracted value", "提取结果"): value or tr("— Not mentioned", "— 未提及")}
                for key, value in result["extracted_fields"].items()
            ]
        )
        st.dataframe(extracted, width="stretch", hide_index=True)

        confirmed_col, missing_info_col = st.columns(2)
        with confirmed_col:
            st.markdown(tr("#### Confirmed information", "#### 已确认信息"))
            if result["confirmed_info"]:
                for item in result["confirmed_info"]:
                    st.write(f"- {field_label(item)}")
            else:
                st.write(tr("No commercial fields were explicit.", "询盘中没有明确的商务字段。"))
        with missing_info_col:
            st.markdown(tr("#### Missing information", "#### 缺失信息"))
            for item in result["missing_info"]:
                st.write(f"- {field_label(item)}")

        risk_col, question_col = st.columns(2)
        with risk_col:
            st.markdown(tr("#### Potential risks", "#### 潜在风险"))
            if result["risks"]:
                for item in result["risks"]:
                    st.warning(item)
            else:
                st.success(tr("No rule-based risk flags were triggered.", "规则引擎未发现明显风险。"))
        with question_col:
            st.markdown(tr("#### Next questions", "#### 下一步追问"))
            for index, item in enumerate(result["next_questions"], start=1):
                st.write(f"{index}. {item}")

        products = list_products()
        matches = recommend_products(st.session_state["inquiry_text"], products)
        st.subheader(tr("Potential product matches", "潜在匹配产品"))
        if matches:
            for match in matches:
                st.write(
                    f"**{match['product_name']}** · {match['match_score']}% {tr('keyword match', '关键词匹配')} · "
                    + ", ".join(reason.replace("Shared keyword: ", "") for reason in match["match_reasons"])
                )
        else:
            st.caption(tr("No knowledge-base product shared enough keywords with this inquiry.", "产品知识库中暂无足够匹配的产品。"))

        st.subheader(tr("Suggested English reply", "英文回复建议"))
        st.code(result["suggested_reply"], language=None)

        customers = list_customers()
        options = {None: tr("No customer linked", "不关联客户"), **{row["id"]: row["company_name"] for row in customers}}
        linked_customer = st.selectbox(tr("Link to customer", "关联客户"), list(options), format_func=options.get)
        if st.button(tr("Save analysis", "保存分析")):
            inquiry_id = create_inquiry(
                customer_id=linked_customer,
                raw_text=st.session_state["inquiry_text"],
                analysis=result,
                analysis_mode=run.mode,
            )
            st.success(tr(f"Inquiry analysis #{inquiry_id} saved.", f"询盘分析 #{inquiry_id} 已保存。"))

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
