# B2B Export Sales Workspace

[![Tests](https://github.com/hql7-luo/b2b-export-sales-intelligence/actions/workflows/tests.yml/badge.svg)](https://github.com/hql7-luo/b2b-export-sales-intelligence/actions/workflows/tests.yml)

**A bilingual Python / Streamlit workspace that turns a buyer RFQ into a linked
customer record, USD quotation, follow-up task and sales analysis.**

**Problem:** export teams lose context when inquiries, costs and next actions
live in separate inboxes and spreadsheets.

**Input → output:** English buyer message + product / cost records → reviewed
requirements, a traceable quotation and a prioritized next action.

[Live demo](https://b2b-export-sales-intelligence-qtonipxh5e4bwnfst2a5zj.streamlit.app/) ·
[Colab walkthrough](https://colab.research.google.com/github/hql7-luo/b2b-export-sales-intelligence/blob/main/notebooks/export_sales_intelligence_demo.ipynb) ·
[Local setup](#installation)

## One complete sales workflow

<picture>
  <source media="(max-width: 640px)" srcset="docs/visuals/sales-workflow-mobile.png">
  <img src="docs/visuals/sales-workflow.png" alt="Six actual UI steps: buyer inquiry, structured analysis, customer record, quotation, follow-up and sales analytics. All data is fictional.">
</picture>

**Analyze Inquiry → Prepare Quotation → Follow Up** is backed by SQLite:
customer, inquiry, product, quotation and task IDs stay linked across pages.
The montage shows the current application using fictional seed data;
[view its source crops and regeneration method](docs/visuals/README.md).

**What I built:** local inquiry parsing and information-gap checks; SQL-backed
customer prioritization; CNY-to-USD pricing with explicit Gross Margin / Markup;
linked follow-up tasks; and Pandas / Plotly sales analytics.

**Skills demonstrated:** Python · SQL / SQLite · Pandas · Streamlit · business
logic · workflow design · decision support.

**Business value:** review missing details before quoting, avoid re-entering
customer facts, and make the next sales action visible. These are capabilities
of the prototype, not measured revenue or productivity gains.

## See where sales effort should go

![Current sales analytics: sales-stage distribution, Lead Quality, overdue work and conversion ratios, calculated from fictional demo records](docs/visuals/sources/analytics.png)

The funnel shows **current stage counts**, not a historical cohort conversion
funnel. Lead Quality uses commercial signals separately from profile
completeness. The conversion ratios are calculated from persisted inquiry /
quotation / customer links; **all figures are fictional demonstration data,
not real business performance**.

## Demo scope

The [public workspace](https://b2b-export-sales-intelligence-qtonipxh5e4bwnfst2a5zj.streamlit.app/)
runs the full local-rules workflow without an API key. All bundled companies,
contacts, products, costs and outcomes are fictional. Community Cloud can
restart and reset its SQLite database, and may sleep after inactivity. If a
sleep screen appears, use the public wake-up button. Treat it as a demonstration
and do not enter confidential customer information. Optional enhanced analysis is
available locally; the core workflow does not need it.

## How to use it

1. Open **Analyze Inquiry** and load the fictional demo inquiry or paste an
   English RFQ.
2. Review the request summary, missing information, risks, recommended
   questions, product match, and editable professional English reply.
3. Link an existing customer or create a new customer, then save the inquiry.
4. Open **Create Quotation**. Customer, inquiry, product, quantity,
   specification, destination, and database IDs are inherited automatically.
5. Enter costs, exchange rate, pricing method, terms, and validity, then save
   the quotation.
6. Create a linked follow-up. The customer, inquiry, quotation, stage, and
   recommended follow-up date are inherited.

The language control in the upper-right switches the interface between English
and Simplified Chinese without clearing the current workflow context or form
inputs. Customer-facing suggested replies remain professional English.

## Core capabilities

| Area | What is included |
|---|---|
| Inquiry | Demo inquiry, structured summary, graded information gaps, risk categories, recommended questions, editable English reply |
| Customers | Independent Data Completeness and commercial Lead Quality, filters, next action, editing, import/export, business timeline |
| Products | Compact specification, MOQ, cost, packaging, sample lead time, production lead time, and match-usage management |
| Quotations | EXW, FOB, CIF, DDP, CNY-to-USD conversion, Gross Margin or Markup, per-quotation exchange rate, Excel export |
| Follow-ups | Overdue/today/future task queue, customer/stage/priority/date filters, Inquiry and Quotation references |
| Analytics | Customer count, Lead Quality distribution, overdue work, conversion rates, funnel, source, and country distributions |
| Settings | Editable default exchange rate, concise analysis status, fictional demo-data ensure/reset controls |

### Professional customer portfolio

Data Completeness measures whether the customer record is usable. Lead Quality
is separate and uses commercial value: purchase potential, buying progress,
persisted inquiry/quotation evidence, and engagement.

### Follow-up task queue

Tasks are grouped into overdue, today, and future work. Each persisted task
shows its customer, stage, priority, Inquiry ID, and Quotation ID.

### Unmatched product handling

An older inquiry without a matched product can be rematched, assigned manually,
or used to calculate an unmatched draft. Formal saving requires explicit
product verification.

## Quotation logic

All costs are entered in CNY. The exchange-rate definition is:

```text
1 USD = X CNY
USD quote = CNY quote ÷ X
```

The workspace setting supplies a default exchange rate. Each quotation can
override it without changing the default.

### Gross Margin — default

```text
Selling price = Cost ÷ (1 - Gross Margin rate)
```

Gross Margin measures profit as a percentage of selling price.

### Markup — alternative

```text
Selling price = Cost × (1 + Markup rate)
```

Markup measures profit as a percentage of cost. A 25% Gross Margin and a 25%
Markup do not produce the same selling price, so the selected method is labeled
and persisted.

Estimated DDP results retain an explicit warning because destination-country
tariff, tax, customs, and final-delivery assumptions require verification.

## Architecture

```mermaid
flowchart LR
    U["Export salesperson"] --> P["Streamlit pages"]
    P --> W["Workflow services"]
    W --> R["Parameterized repositories"]
    R --> DB[("SQLite")]
    W --> Q["Quotation engine"]
    W --> I["Local inquiry rules"]
    I --> O["Optional enhanced analysis"]
    W --> X["Excel import/export"]
```

- `pages/` owns presentation and user interaction.
- `services/` owns inquiry, customer-quality, matching, quotation, follow-up,
  analytics, and workflow rules.
- `database/` owns initialization, forward migrations, repositories, and
  fictional demo data.
- `locales/` contains stable English and Simplified Chinese translation keys.
- `components/` contains the approved visual system and workflow context.
- [Original design and acceptance notes](docs/design/README.md) preserve the
  development brief and rubric; they are not measured benchmark results.

## Database relationships

```mermaid
erDiagram
    CUSTOMERS ||--o{ INQUIRIES : receives
    PRODUCTS ||--o{ INQUIRIES : matched_to
    CUSTOMERS ||--o{ QUOTATIONS : receives
    INQUIRIES ||--o{ QUOTATIONS : produces
    PRODUCTS ||--o{ QUOTATIONS : quoted_as
    CUSTOMERS ||--o{ FOLLOW_UPS : has
    INQUIRIES ||--o{ FOLLOW_UPS : references
    QUOTATIONS ||--o{ FOLLOW_UPS : triggers
    CUSTOMERS ||--o{ ACTIVITIES : timeline
    INQUIRIES ||--o{ ACTIVITIES : timeline
    QUOTATIONS ||--o{ ACTIVITIES : timeline
```

Core persisted links:

- `inquiries.customer_id`
- `inquiries.matched_product_id`
- `quotations.customer_id`
- `quotations.inquiry_id`
- `quotations.product_id`
- `follow_ups.customer_id`
- `follow_ups.inquiry_id`
- `follow_ups.quotation_id`
- optional `activities.inquiry_id` and `activities.quotation_id`

Migrations are forward-only and idempotent. They preserve existing records,
avoid duplicate columns/indexes, and are tested with SQLite integrity and
foreign-key checks.

## Fictional demo data

All bundled companies, people, domains, phone numbers, products, inquiries,
costs, quotations, follow-ups, and business outcomes are fictional.

The clean demo contains:

- 20 customers
- 10 inquiries
- 8 quotations
- 10 follow-ups
- 6 products

**Ensure demo data** adds missing bundled records. **Reset fictional demo data**
replaces only bundled demo records and preserves user-created records. Browser
QA data is created in temporary databases and is not part of the seed.

## Installation

Python 3.11 and 3.12 are tested in CI; Python 3.12 is recommended for local use.
`requirements.txt` locks all direct and transitive dependencies with hashes.
`requirements.in` retains the supported dependency ranges for maintenance.

```bash
git clone https://github.com/hql7-luo/b2b-export-sales-intelligence.git
cd b2b-export-sales-intelligence

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements.txt

cp .env.example .env
python -m database.init_db
```

Windows activation:

```powershell
.venv\Scripts\activate
```

`OPENAI_API_KEY` is optional. Leave it empty to use local inquiry rules.

## Run

```bash
source .venv/bin/activate
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501).

To use a separate database:

```bash
DATABASE_PATH=data/another-workspace.db streamlit run app.py
```

A new database initializes automatically and receives fictional demo data on
its first application run.

## Test

```bash
python -m pytest
```

Optional coverage:

```bash
python -m pytest --cov=services --cov=database --cov-report=term-missing
```

Tests cover pricing formulas, inquiry analysis, repository safety, migrations,
workflow relationships, translation keys, demo reset behavior, release files,
application smoke rendering, contact-identifier preservation and missing values
in customer imports. CSV contact fields stay text, and ambiguous normalized
column names are rejected instead of silently replacing customer data.

To refresh dependencies within the existing supported ranges, use
[uv](https://docs.astral.sh/uv/) from the repository root:

```bash
uv pip compile --python-version 3.11 --universal --generate-hashes --no-emit-index-url requirements.in -o requirements.txt
python -m pip install --require-hashes -r requirements.txt
python -m pytest
```

Review the generated lock and run both supported Python versions before release.

## Deployment

### GitHub Actions

`.github/workflows/tests.yml` installs the hash-locked `requirements.txt` with
Python 3.11 and 3.12, checks compilation and runs the complete pytest suite with
coverage on pushes and pull requests.

### Streamlit Community Cloud

The repository includes the root `requirements.txt` and
`.streamlit/config.toml` expected by Streamlit Community Cloud.

The public demonstration is available at:

**[b2b-export-sales-intelligence-qtonipxh5e4bwnfst2a5zj.streamlit.app](https://b2b-export-sales-intelligence-qtonipxh5e4bwnfst2a5zj.streamlit.app/)**

To deploy another instance:

1. Select `app.py` as the entrypoint.
2. Select Python 3.11 in Advanced settings.
3. Leave `OPENAI_API_KEY` empty to use the complete local-rules workflow.
4. Add secrets only when optional enhanced analysis is intentionally enabled.

References:
[Streamlit deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy),
[dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies),
and [secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).

The online Demo uses Streamlit-local SQLite and may reset or reinitialize when
the container restarts or the app is redeployed. It is suitable for a
demonstration, not durable multi-user production data. Use a managed database
and authentication before handling real customer information.

### Colab demo

Open the
[Google Colab demo](https://colab.research.google.com/github/hql7-luo/b2b-export-sales-intelligence/blob/main/notebooks/export_sales_intelligence_demo.ipynb)
to run seven code cells directly from the GitHub `main` branch. Its setup cell
installs the same locked dependencies in Colab before importing the project. It demonstrates
customer scoring, inquiry analysis, Gross Margin versus Markup, quotation
outputs, and decision-focused business charts using only fictional data. No API
key is required.

## Limitations

- This is a portfolio-grade single-workspace application, not a multi-tenant
  production system.
- SQLite has no built-in user authentication and is plaintext at rest.
- Streamlit Community Cloud storage may be ephemeral.
- DDP is an estimate until destination-country tariff, tax, customs, and
  final-delivery inputs are verified.
- Product matching is explainable keyword matching, not a product feasibility
  guarantee.
- Local inquiry rules are deterministic and do not replace salesperson review.
- External analysis, when enabled, sends inquiry text to the configured
  provider; confidential data requires authorization and an appropriate data
  policy.
- ERP, order execution, customs-data feeds, automated email/calendar actions,
  and advanced predictive models are intentionally out of scope.

## Project structure

```text
.
├── app.py
├── pages/
│   ├── inquiry_analyzer.py
│   ├── customers.py
│   ├── quotation_calculator.py
│   ├── follow_up_tracker.py
│   ├── products.py
│   ├── dashboard.py
│   └── settings.py
├── services/
│   ├── inquiry_analyzer.py
│   ├── inquiry_brief.py
│   ├── customer_intelligence.py
│   ├── product_match.py
│   ├── quotation.py
│   ├── workflow.py
│   ├── followup.py
│   └── dashboard.py
├── database/
│   ├── connection.py
│   ├── init_db.py
│   ├── migrations.py
│   ├── repository.py
│   └── seed_data.py
├── components/
├── locales/
├── tests/
├── docs/screenshots/
├── docs/design/
├── notebooks/export_sales_intelligence_demo.ipynb
├── .github/workflows/tests.yml
├── .streamlit/
├── LICENSE
├── requirements.txt
├── requirements.in
└── README.md
```

## Resume description

- Built a bilingual Streamlit and SQLite export-sales workspace that persists
  the complete Inquiry → Quotation → Follow-up relationship and customer
  timeline.
- Implemented a tested quotation engine for EXW, FOB, CIF, DDP, Gross Margin,
  Markup, per-quotation exchange rates, and Excel output.
- Designed decision-focused customer quality, follow-up queue, product
  reference, and sales analytics modules using Python, SQL, Pandas, and Plotly.
