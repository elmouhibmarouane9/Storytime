"""JSON persistence layer. Every record MIM touches lives in data/*.json.

Writes are atomic (temp file + replace) so a crash mid-save can never corrupt
the book. `today()` is the single clock for the whole system — override it with
MIM_TODAY=YYYY-MM-DD to time-travel the dashboards for forecasting demos.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("MIM_DATA_DIR", ROOT / "data"))

COLLECTIONS = ("settings", "clients", "invoices", "projects", "messages")


def path_for(name: str) -> Path:
    return DATA_DIR / f"{name}.json"


def today() -> date:
    override = os.environ.get("MIM_TODAY", "").strip()
    if override:
        return datetime.strptime(override, "%Y-%m-%d").date()
    return date.today()


def load(name: str, default: Any = None) -> Any:
    p = path_for(name)
    if not p.exists():
        return default if default is not None else ({} if name == "settings" else [])
    with p.open(encoding="utf-8") as fh:
        return json.load(fh)


def save(name: str, payload: Any) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    p = path_for(name)
    fd, tmp = tempfile.mkstemp(dir=str(DATA_DIR), prefix=f".{name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return p


def bootstrap(force: bool = False) -> None:
    """Create the book on first run. Sample data is clearly labelled as such."""
    from . import seed

    if force:
        for name in COLLECTIONS:
            save(name, seed.build(name))
        return
    if not all(path_for(n).exists() for n in COLLECTIONS):
        for name in COLLECTIONS:
            if force or not path_for(name).exists():
                save(name, seed.build(name))


def dump() -> dict[str, Any]:
    return {name: load(name) for name in COLLECTIONS}
