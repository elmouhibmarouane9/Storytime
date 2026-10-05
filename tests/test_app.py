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
