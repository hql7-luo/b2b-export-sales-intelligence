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
def test_language_switch_changes_copy_without_losing_inquiry_context() -> None:
    app = AppTest.from_file("app.py").run(timeout=20)

    assert app.title[0].value == "Analyze Inquiry"
    app.text_area[0].set_value("Please quote 2,000 fictional sample cartons to Rotterdam.").run(timeout=20)
    workflow_context = dict(app.session_state["workflow_context"])
    workflow_context["customer_id"] = 42
    workflow_context["inquiry_id"] = 84
    workflow_context["product_id"] = 21
    workflow_context["quotation_id"] = 126
    workflow_context["follow_up_id"] = 168
    app.session_state["workflow_context"] = workflow_context

    app.segmented_control[0].set_value("zh").run(timeout=20)

    assert list(app.exception) == []
    assert app.title[0].value == "分析询盘"
    assert app.segmented_control[0].value == "zh"
    assert app.text_area[0].value == "Please quote 2,000 fictional sample cartons to Rotterdam."
    assert app.session_state["workflow_context"]["customer_id"] == 42
    assert app.session_state["workflow_context"]["inquiry_id"] == 84
    assert app.session_state["workflow_context"]["product_id"] == 21
    assert app.session_state["workflow_context"]["quotation_id"] == 126
    assert app.session_state["workflow_context"]["follow_up_id"] == 168

    app.segmented_control[0].set_value("en").run(timeout=20)

    assert list(app.exception) == []
    assert app.title[0].value == "Analyze Inquiry"
    assert app.segmented_control[0].value == "en"
    assert app.text_area[0].value == "Please quote 2,000 fictional sample cartons to Rotterdam."
    assert app.session_state["workflow_context"]["customer_id"] == 42
    assert app.session_state["workflow_context"]["inquiry_id"] == 84
    assert app.session_state["workflow_context"]["product_id"] == 21
    assert app.session_state["workflow_context"]["quotation_id"] == 126
    assert app.session_state["workflow_context"]["follow_up_id"] == 168


@pytest.mark.smoke
def test_analyzed_inquiry_and_edited_reply_survive_language_switch() -> None:
    app = AppTest.from_file("app.py").run(timeout=20)

    app.button(key="load_demo_inquiry").click().run(timeout=20)
    assert "5,000 custom hardcover notebooks" in app.text_area(key="inquiry_input").value

    app.button(key="analyze_inquiry").click().run(timeout=20)
    assert "inquiry_run" in app.session_state
    assert app.session_state["workflow_context"]["analysis_result"]

    reply = "Dear Customer,\n\nThank you. Please confirm the delivery postcode.\n\nBest regards"
    app.text_area(key="suggested_reply_editor").set_value(reply).run(timeout=20)
    app.segmented_control[0].set_value("zh").run(timeout=20)

    assert list(app.exception) == []
    assert app.text_area(key="suggested_reply_editor").value == reply
    assert app.session_state["workflow_context"]["analysis_result"]
    assert app.session_state["workflow_context"]["edited_reply"] == reply

    app.segmented_control[0].set_value("en").run(timeout=20)

    assert list(app.exception) == []
    assert app.title[0].value == "Analyze Inquiry"
    assert app.segmented_control[0].value == "en"
    assert app.text_area(key="suggested_reply_editor").value == reply
    assert app.session_state["workflow_context"]["analysis_result"]
    assert app.session_state["workflow_context"]["edited_reply"] == reply
