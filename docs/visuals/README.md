# Workflow visual provenance

The six panels are crops from the current Streamlit application, not UI mockups.
The capture uses only `database/seed_data.py` and the built-in fictional inquiry
in `pages/inquiry_analyzer.py`. Enhanced analysis is disabled, and no customer
information or API key is used. The analytics panel is captured before the
walkthrough adds an inquiry and quotation; its metrics describe fictional seed
records, never measured sales performance.

`capture-manifest.json` records the source commit, capture date, viewport,
page paths, crop dimensions and SHA-256 hashes. `scripts/build_workflow_visual.py`
uses Pillow (already included in the locked application dependencies) to resize
and arrange these real UI crops. It does not generate scores, prices or KPI data.
The narrow-screen version uses the same six source images and workflow.

## Regenerate

Install the locked application dependencies as documented in the main README.
Start with a **fresh disposable** database outside the repository:

```bash
OPENAI_API_KEY="" DATABASE_PATH=/tmp/b2b-workflow-capture.db \
  .venv/bin/streamlit run app.py --server.port 8514 --server.headless true
```

In another terminal, install Playwright in a temporary tool directory and run:

```bash
npm install --prefix /tmp/b2b-visual-tools playwright
npx --prefix /tmp/b2b-visual-tools playwright install chrome
PLAYWRIGHT_MODULE=/tmp/b2b-visual-tools/node_modules/playwright \
  node scripts/capture_workflow.mjs
.venv/bin/python scripts/build_workflow_visual.py
```

`B2B_CAPTURE_URL` can override the local URL. The script drives the real UI:
load the built-in RFQ, analyze it, link the seeded customer, save the inquiry,
calculate and save a quotation, then open the linked follow-up form. Application
code defines this workflow in `services/workflow.py`; analytics is calculated
from SQLite by `services/dashboard.py`.
