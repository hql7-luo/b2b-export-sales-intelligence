"""Read-only runtime settings and safe demo-data controls."""

from __future__ import annotations

import os

import streamlit as st

from components.theme import operations_ledger, page_header
from database.connection import DEFAULT_DB_PATH
from database.seed_data import seed_demo_data
from utils.i18n import tr


page_header(
    tr("Settings", "设置"),
    tr("Review local data, AI availability, and the default quotation convention without exposing secrets.", "查看本地数据、AI 可用状态和默认报价规则，同时避免泄露敏感信息。"),
    tr("P2 · Runtime status", "P2 · 运行状态"),
)
operations_ledger()

api_enabled = bool(os.getenv("OPENAI_API_KEY", "").strip())
status_cols = st.columns(4)
status_cols[0].metric(tr("AI analyzer", "AI 分析器"), tr("Enabled", "已启用") if api_enabled else tr("Rule mode", "规则模式"))
status_cols[1].metric(tr("LLM model", "大模型"), os.getenv("OPENAI_MODEL", "gpt-5-mini"))
status_cols[2].metric(tr("Quote currency", "报价币种"), os.getenv("DEFAULT_CURRENCY", "USD"))
status_cols[3].metric(tr("Pricing default", "默认定价方式"), tr("Gross Margin", "毛利率"))

st.subheader(tr("Local data", "本地数据"))
st.code(str(DEFAULT_DB_PATH), language=None)
st.caption(tr("SQLite stays on this machine. `.env` and database files are excluded from Git by default.", "SQLite 数据仅保存在本机；`.env` 和数据库文件默认不会提交到 Git。"))
if st.button(tr("Ensure fictional demo data is available", "检查并补充虚拟演示数据")):
    counts = seed_demo_data()
    st.success(tr("Demo data ready: ", "演示数据已就绪：") + ", ".join(f"{name}={count}" for name, count in counts.items()))

st.subheader(tr("Quotation convention", "报价规则"))
st.write(tr("Costs are entered in CNY. The exchange rate is expressed as **1 USD = X CNY**. Output defaults to USD.", "成本以人民币输入；汇率表示为 **1 USD = X CNY**；默认输出美元报价。"))
st.write(tr("**Gross Margin:** Selling price = Cost ÷ (1 − margin rate). This is the default.", "**毛利率（默认）：** 售价 = 成本 ÷（1 − 毛利率）。"))
st.write(tr("**Markup:** Selling price = Cost × (1 + markup rate).", "**加成率：** 售价 = 成本 ×（1 + 加成率）。"))

st.subheader(tr("AI configuration", "AI 配置"))
st.code("OPENAI_API_KEY=your-key\nOPENAI_MODEL=gpt-5-mini", language="bash")
st.warning(tr("Store the real API key only in `.env`; never add it to source control. If the API fails, analysis automatically uses deterministic rules.", "真实 API Key 只能保存在 `.env` 中，禁止提交到代码仓库；API 不可用时会自动回退到确定性规则分析。"))

st.subheader(tr("Privacy and demo-data status", "隐私与演示数据"))
st.success(tr("All bundled companies, people, emails, phone numbers, products, costs and transactions are fictional.", "内置公司、联系人、邮箱、电话、产品、成本和交易记录全部为虚拟数据。"))
