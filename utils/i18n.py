"""Small session-based English/Chinese UI localization helpers."""

from __future__ import annotations

from typing import Any

import streamlit as st


LANGUAGE_KEY = "ui_language"

VALUE_LABELS_ZH = {
    "New Lead": "新线索",
    "Contacted": "已联系",
    "Replied": "已回复",
    "Requirement Confirmed": "需求已确认",
    "Quoted": "已报价",
    "Sample": "样品阶段",
    "Negotiation": "商务谈判",
    "Order Confirmed": "订单已确认",
    "Lost": "已流失",
    "Trade Show": "展会",
    "B2B Platform": "B2B 平台",
    "Website": "官网",
    "Referral": "客户转介绍",
    "LinkedIn": "领英",
    "Marketplace": "电商平台",
    "Cold Outreach": "主动开发",
    "Social Media": "社交媒体",
    "Outbound Research": "市场调研开发",
    "Other": "其他",
    "Unknown": "未知",
    "One-time": "一次性",
    "Annual": "每年",
    "Biannual": "每半年",
    "Quarterly": "每季度",
    "Monthly": "每月",
    "Weekly": "每周",
    "Gross Margin": "毛利率",
    "Markup": "加成率",
    "High": "高",
    "Medium": "中",
    "Low": "低",
    "Email": "邮件",
    "Phone": "电话",
    "Video Call": "视频会议",
    "Meeting": "会议",
    "WhatsApp / Chat": "WhatsApp / 在线沟通",
}

FIELD_LABELS_ZH = {
    "product": "产品",
    "specification": "规格",
    "quantity": "数量",
    "application": "用途",
    "customization_requirement": "定制要求",
    "packaging_requirement": "包装要求",
    "destination": "目的地",
    "required_delivery_time": "要求交期",
    "target_price": "目标价格",
    "sample_requirement": "样品要求",
    "payment_requirement": "付款要求",
}

SCORE_DIMENSION_LABELS_ZH = {
    "company_authenticity": "公司真实性",
    "product_fit": "产品匹配度",
    "requirement_clarity": "需求清晰度",
    "purchasing_capacity": "采购能力",
    "communication_engagement": "沟通参与度",
}


def is_chinese() -> bool:
    """Return whether the active Streamlit session uses Chinese UI text."""
    return st.session_state.get(LANGUAGE_KEY, "en") == "zh"


def tr(english: str, chinese: str) -> str:
    """Choose one of two explicit interface strings for the active language."""
    return chinese if is_chinese() else english


def option_label(value: Any) -> str:
    """Localize stored business-enum values without changing database values."""
    text = str(value)
    return VALUE_LABELS_ZH.get(text, text) if is_chinese() else text


def field_label(value: Any) -> str:
    """Localize known inquiry field identifiers."""
    text = str(value)
    if is_chinese():
        return FIELD_LABELS_ZH.get(text, text.replace("_", " ").title())
    return text.replace("_", " ").title()


def score_dimension_label(value: Any) -> str:
    """Localize scoring dimension keys used in audit evidence."""
    text = str(value)
    return SCORE_DIMENSION_LABELS_ZH.get(text, text.replace("_", " ").title()) if is_chinese() else text.replace("_", " ").title()


def localize_error(message: str) -> str:
    """Keep errors actionable in Chinese while retaining unexpected details."""
    if not is_chinese():
        return message
    known = {
        "Company Name is required.": "公司名称为必填项。",
        "Email format is invalid.": "邮箱格式无效。",
        "Website must begin with http:// or https://.": "网站地址必须以 http:// 或 https:// 开头。",
        "Product Name is required.": "产品名称为必填项。",
        "company_name is required": "公司名称为必填项。",
        "product_name is required": "产品名称为必填项。",
        "follow_up_date is required": "联系日期为必填项。",
        "content is required": "沟通内容为必填项。",
    }
    return known.get(message, f"操作未完成：{message}")
