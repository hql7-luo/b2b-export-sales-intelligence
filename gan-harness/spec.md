# AI-Powered B2B Export Sales Intelligence System

## Product brief

A portfolio-ready Streamlit application for export sales professionals to manage
leads, score lead quality, analyze inquiries, calculate quotations, track
follow-ups, and review sales analytics. Business fields remain industry-neutral;
all demo records are fictional creative-printing and packaging scenarios.

## Locked implementation decisions

- Python, Streamlit, SQLite, Pandas, Plotly, OpenAI-compatible LLM, openpyxl.
- Simple `pages -> services -> database` architecture.
- P0 stability comes before visual polish or coverage targets.
- Pricing supports Gross Margin and Markup. Gross Margin is the default.
- CNY cost input and USD output use `1 USD = X CNY`.
- No API key or real customer data is stored in source control.
- LLM failures and invalid JSON automatically fall back to deterministic rules.

## Required vertical slices

1. App shell, database, fictional seed data, customer creation and explainable scoring.
2. Complete customer CRUD, filtering, CSV/Excel import, and Excel export.
3. Gross Margin/Markup quotation calculations, persistence, and Excel quotation export.
4. Dashboard KPIs, distributions, funnel, projected sales, and follow-up queue.
5. Rule/AI inquiry analysis with one normalized JSON contract and persistence.
6. Follow-up logging, overdue prioritization, stage advice, and English messages.
7. Searchable product knowledge base and minimal settings/status page.
8. Tests after every slice, security review, smoke test, screenshots, and English README.

## Acceptance floor

- P0 workflows are complete and usable through the UI.
- Exactly 20 customers, 10 inquiries, 8 quotations, 10 follow-ups, and 6 products
  are provided as fictional demo data.
- All required tests pass and the headless Streamlit process starts without error.
- Empty states, invalid inputs, missing environment variables, and failed LLM calls
  produce clear recovery guidance.
