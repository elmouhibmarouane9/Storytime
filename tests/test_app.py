"""Headless render of every console page. If a page breaks, this catches it."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from mim.i18n import PAGE_KEYS, nav_labels

APP = Path(__file__).resolve().parent.parent / "streamlit_app.py"
PAGES = ["dashboard", "clients", "invoices", "finance", "projects", "comms", "settings"]


@pytest.fixture(scope="module")
def app():
    at = AppTest.from_file(str(APP), default_timeout=120)
    at.run()
    return at


def test_app_boots_without_exception(app):
    assert not app.exception, app.exception
    assert app.sidebar.radio(key="nav_page").value == nav_labels("EN")[0]


@pytest.mark.parametrize("page", PAGES)
def test_every_page_renders(app, page):
    app.sidebar.radio(key="nav_page").set_value(nav_labels("EN")[PAGE_KEYS.index(page)]).run()
    assert not app.exception, f"{page} raised: {app.exception}"
    assert len(app.markdown) > 3


def test_language_switch_keeps_pages_alive(app):
    app.sidebar.selectbox(key="console_lang").set_value("ES").run()
    assert not app.exception
    app.sidebar.radio(key="nav_page").set_value(nav_labels("ES")[0]).run()
    assert not app.exception
    app.sidebar.selectbox(key="console_lang").set_value("EN").run()
    assert not app.exception


def test_access_gate_blocks_a_public_deployment(monkeypatch, tmp_path):
    monkeypatch.setenv("MIM_ACCESS_CODE", "open-sesame-123")
    monkeypatch.setenv("MIM_DATA_DIR", str(tmp_path / "gated"))
    at = AppTest.from_file(str(APP), default_timeout=120)
    at.run()
    assert not at.exception
    rendered = " ".join(m.value for m in at.markdown)
    assert "Ops pulse" not in rendered, "ledger must not render before the code is entered"
    assert "Cash priority" not in rendered

    at.text_input(key="mim_code").set_value("wrong-code")
    at.button(key="mim_unlock").click().run()
    assert "Ops pulse" not in " ".join(m.value for m in at.markdown)

    at.text_input(key="mim_code").set_value("open-sesame-123")
    at.button(key="mim_unlock").click().run()
    assert "Ops pulse" in " ".join(m.value for m in at.markdown)


def test_gate_absent_means_no_gate(monkeypatch, tmp_path):
    monkeypatch.delenv("MIM_ACCESS_CODE", raising=False)
    monkeypatch.setenv("MIM_DATA_DIR", str(tmp_path / "open"))
    at = AppTest.from_file(str(APP), default_timeout=120)
    at.run()
    assert not at.exception
    assert "Ops pulse" in " ".join(m.value for m in at.markdown)
