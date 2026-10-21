from tools import make_preview
from mim import store


def test_preview_initializes_sample_book_before_building_sections(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)

    make_preview.initialize()

    assert make_preview.BOOK["settings"]["sample_data"] is True
    assert len(make_preview.BOOK["clients"]) == 5
    assert "Nordwind Media" in make_preview.clients_body()
