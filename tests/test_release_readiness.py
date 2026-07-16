from __future__ import annotations

import json
from pathlib import Path

from database.connection import get_connection
from database.init_db import initialize_database


ROOT = Path(__file__).resolve().parents[1]


def test_release_files_are_present_and_documented() -> None:
    required = (
        ROOT / ".github/workflows/tests.yml",
        ROOT / ".streamlit/secrets.toml.example",
        ROOT / "output/jupyter-notebook/colab-demo.ipynb",
        ROOT / ".env.example",
        ROOT / "requirements.txt",
    )
    assert all(path.exists() for path in required)

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Analyze Inquiry → Prepare Quotation → Follow Up" in readme
    assert "fictional" in readme.lower()
    assert "Limitations" in readme
    assert "docs/screenshots/phase4-en-analytics.png" in readme
    assert "docs/screenshots/phase4-en-customers.png" in readme


def test_github_actions_runs_the_complete_pytest_suite() -> None:
    workflow = (ROOT / ".github/workflows/tests.yml").read_text(
        encoding="utf-8"
    )
    assert "python -m pytest" in workflow
    assert "requirements.txt" in workflow
    assert "push:" in workflow
    assert "pull_request:" in workflow


def test_streamlit_cloud_and_environment_examples_do_not_contain_secrets() -> None:
    secrets_example = (
        ROOT / ".streamlit/secrets.toml.example"
    ).read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert 'OPENAI_API_KEY = ""' in secrets_example
    assert "OPENAI_API_KEY=" in env_example
    assert "DEFAULT_EXCHANGE_RATE=7.20" in env_example
    assert "sk-" not in secrets_example
    assert "sk-" not in env_example


def test_gitignore_excludes_runtime_secrets_databases_and_notebook_checkpoints() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in (
        ".env",
        "data/*.db",
        ".streamlit/secrets.toml",
        ".ipynb_checkpoints/",
    ):
        assert pattern in gitignore


def test_colab_notebook_is_clean_structured_and_uses_fictional_examples() -> None:
    notebook_path = ROOT / "output/jupyter-notebook/colab-demo.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))

    assert notebook["nbformat"] == 4
    assert len(notebook["cells"]) >= 8
    source = "\n".join(
        "".join(cell.get("source") or []) for cell in notebook["cells"]
    )
    assert "Audience" in source
    assert "Learning goals" in source
    assert "Gross Margin" in source
    assert "Markup" in source
    assert "fictional" in source.lower()
    assert "/Users/" not in source
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            assert cell.get("execution_count") is None
            assert cell.get("outputs") == []


def test_fresh_database_initializes_without_api_key(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    db_path = tmp_path / "fresh-release.db"

    initialize_database(db_path)

    connection = get_connection(db_path)
    try:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute(
            "SELECT setting_value FROM app_settings "
            "WHERE setting_key = 'default_exchange_rate'"
        ).fetchone()["setting_value"]
    finally:
        connection.close()
