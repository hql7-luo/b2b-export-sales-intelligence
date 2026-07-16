"""Application-level startup coverage for the Streamlit navigation pages."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


PAGE_FILES = [
    Path("app.py"),
    *sorted(path for path in Path("pages").glob("*.py") if path.name != "__init__.py"),
]


@pytest.mark.smoke
@pytest.mark.parametrize("page_file", PAGE_FILES, ids=lambda path: path.stem)
def test_streamlit_page_starts_without_exceptions(page_file: Path) -> None:
    app = AppTest.from_file(str(page_file)).run(timeout=20)

    assert list(app.exception) == []


@pytest.mark.smoke
@pytest.mark.parametrize("page_file", PAGE_FILES, ids=lambda path: f"zh-{path.stem}")
def test_streamlit_page_starts_in_chinese(page_file: Path) -> None:
    app = AppTest.from_file(str(page_file))
    app.session_state["ui_language"] = "zh"
    app.run(timeout=20)

    assert list(app.exception) == []


@pytest.mark.smoke
def test_language_switch_changes_dashboard_copy() -> None:
    app = AppTest.from_file("app.py").run(timeout=20)

    app.segmented_control[0].set_value("zh").run(timeout=20)

    assert list(app.exception) == []
    assert app.title[0].value == "销售智能仪表盘"
    assert app.segmented_control[0].value == "zh"

    app.segmented_control[0].set_value("en").run(timeout=20)

    assert list(app.exception) == []
    assert app.title[0].value == "Sales Intelligence Dashboard"
    assert app.segmented_control[0].value == "en"
