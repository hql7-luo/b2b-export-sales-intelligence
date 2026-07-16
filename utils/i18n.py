"""Session-based localization with stable keys and a legacy compatibility layer."""

from __future__ import annotations

from typing import Any

import streamlit as st

from locales import TRANSLATIONS


LANGUAGE_KEY = "ui_language"
DEFAULT_LANGUAGE = "en"

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
    return st.session_state.get(LANGUAGE_KEY, DEFAULT_LANGUAGE) == "zh"


def translate(key: str, language: str = DEFAULT_LANGUAGE, **values: Any) -> str:
    """Translate a stable key, falling back to English and then readable text."""
    selected = TRANSLATIONS.get(language, TRANSLATIONS[DEFAULT_LANGUAGE])
    template = selected.get(key) or TRANSLATIONS[DEFAULT_LANGUAGE].get(key)
    if template is None:
        template = TRANSLATIONS[DEFAULT_LANGUAGE]["i18n.missing"]
    try:
        return template.format(**values)
    except (KeyError, ValueError):
        return template


def t(key: str, **values: Any) -> str:
    """Translate a stable interface key for the active Streamlit session."""
    language = st.session_state.get(LANGUAGE_KEY, DEFAULT_LANGUAGE)
    return translate(key, language=language, **values)


def tr(english: str, chinese: str) -> str:
    """Choose legacy inline copy while pages migrate to stable translation keys."""
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
        "customer is required before saving the inquiry": "保存询盘前必须关联或创建客户。",
        "selected customer was not found": "未找到所选客户，请重新选择。",
        "choose either an existing customer or a new customer": "请选择关联已有客户或创建新客户，不要同时提交两种方式。",
        "quantity is required before creating a quotation": "创建报价前必须确认数量。",
        "saved inquiry was not found": "未找到已保存询盘，请返回询盘页面重新保存。",
        "saved inquiry is not linked to a customer": "该询盘尚未关联客户。",
        "linked customer was not found": "未找到已关联客户。",
        "saved quotation was not found": "未找到已保存报价。",
        "saved quotation is not linked to a customer": "该报价尚未关联客户。",
        "selected product was not found": "未找到所选产品，请重新选择。",
        "unmatched product must be verified before saving": "未匹配产品的报价在正式保存前必须完成产品核实。",
        "exchange rate must be greater than zero": "汇率必须大于 0。",
    }
    return known.get(message, f"操作未完成：{message}")
