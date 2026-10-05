"""Tests run against a throwaway data directory — never the operator's real book."""

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="mim-test-book-"))
os.environ["MIM_DATA_DIR"] = str(_TMP)
os.environ.pop("MIM_TODAY", None)
os.environ.pop("MIM_ACCESS_CODE", None)

import pytest  # noqa: E402

from mim import store  # noqa: E402


@pytest.fixture()
def book():
    store.bootstrap(force=True)
    return store.dump()


@pytest.fixture()
def sample_client(book):
    return book["clients"][0]


@pytest.fixture()
def sample_invoice(book):
    return next(i for i in book["invoices"] if i["id"] == "MEM-2026-003")
