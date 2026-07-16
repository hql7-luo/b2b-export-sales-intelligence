"""Translation resource and workflow-state regression tests."""

import re
from pathlib import Path

from locales.en_US import STRINGS as EN_US
from locales.zh_CN import STRINGS as ZH_CN
from utils.i18n import translate


UI_FILES = [Path("app.py"), *Path("pages").glob("*.py"), *Path("components").glob("*.py")]


def test_translation_resources_have_identical_keys() -> None:
    assert set(EN_US) == set(ZH_CN)


def test_translation_uses_requested_language_and_formats_values() -> None:
    assert translate("nav.analyze", language="en") == "Analyze Inquiry"
    assert translate("nav.analyze", language="zh") == "分析询盘"
    assert translate("settings.demo.ready", language="zh", counts="customers=20") == "虚拟演示数据已就绪：customers=20"


def test_translation_falls_back_to_english_without_showing_key() -> None:
    assert translate("nav.analyze", language="unsupported") == "Analyze Inquiry"
    assert translate("missing.translation.key", language="zh") == "Unavailable text"


def test_every_referenced_stable_translation_key_exists() -> None:
    referenced = set()
    for path in UI_FILES:
        source = path.read_text(encoding="utf-8")
        referenced.update(re.findall(r"\bt\(\s*['\"]([^'\"]+)", source))
    assert referenced <= set(EN_US)


def test_professional_interface_has_no_emoji_or_priority_labels() -> None:
    forbidden_text = ("Operations Ledger", "operations_ledger", "P0 ·", "P1 ·", "P2 ·")
    emoji_pattern = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u26FF\u2700-\u27BF]")
    for path in UI_FILES:
        source = path.read_text(encoding="utf-8")
        assert not any(item in source for item in forbidden_text), path
        assert emoji_pattern.search(source) is None, path


def test_interface_and_readme_do_not_expose_local_absolute_paths() -> None:
    paths = [*UI_FILES, Path("README.md")]
    for path in paths:
        source = path.read_text(encoding="utf-8")
        assert "/Users/" not in source, path
        assert "/home/" not in source, path


def test_core_quotation_fields_are_inherited_without_duplicate_input_widgets() -> None:
    source = Path("pages/quotation_calculator.py").read_text(encoding="utf-8")
    forbidden_widget_keys = (
        "quote_customer",
        "quote_product_name",
        "quote_quantity",
        "quote_specification",
        "quote_destination",
        "quote_inquiry_id",
        "quote_product_id",
        "quote_customer_id",
    )
    assert not any(key in source for key in forbidden_widget_keys)
    assert "build_quotation_context" in source


def test_core_follow_up_relationships_are_inherited_without_duplicate_widgets() -> None:
    source = Path("pages/follow_up_tracker.py").read_text(encoding="utf-8")
    forbidden_widget_keys = (
        "followup_customer_id",
        "followup_inquiry_id",
        "followup_quotation_id",
        "followup_customer_stage",
    )
    assert not any(key in source for key in forbidden_widget_keys)
    assert "build_follow_up_context" in source
    assert "save_follow_up_for_quotation" in source
