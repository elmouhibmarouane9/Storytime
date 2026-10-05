"""JSON persistence layer — local disk by default, your own Git repo on request.

Two backends, same interface:

* **local** (default) — atomic writes to `MIM_DATA_DIR`, temp file + replace so a
  crash mid-save can never corrupt the book.
* **github** — the same JSON files committed to a private repo you own. This is how
  a free host with an ephemeral disk (Streamlit Cloud, Hugging Face Spaces) keeps
  your book across restarts, and it gives you version history for free.

Configure the github backend with `GITHUB_TOKEN` + `MIM_DATA_REPO` (env or Streamlit
secrets). Writes mirror locally first, so a network failure never loses the change —
the error surfaces in Settings and the sidebar instead of silently eating data.

`today()` is the single clock for the whole system — override with MIM_TODAY=YYYY-MM-DD
to time-travel the dashboards for forecasting demos.
"""

from __future__ import annotations

import base64
import copy
import json
import os
import tempfile
import time
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("MIM_DATA_DIR", ROOT / "data"))

COLLECTIONS = ("settings", "clients", "invoices", "projects", "messages")

GITHUB_API = "https://api.github.com"
_CACHE: dict[str, tuple[float, Any]] = {}
_SHAS: dict[str, str] = {}
_DIRTY: set[str] = set()   # collections written locally that the remote has not accepted yet
_CACHE_TTL = 5.0
LAST_ERROR: str | None = None
LAST_SYNC: float | None = None


class StorageError(RuntimeError):
    """Raised when the configured backend cannot be reached or authorised."""


def path_for(name: str) -> Path:
    return DATA_DIR / f"{name}.json"


def today() -> date:
    override = os.environ.get("MIM_TODAY", "").strip()
    if override:
        return datetime.strptime(override, "%Y-%m-%d").date()
    return date.today()


# ---------------------------------------------------------------- backend config


def _setting(key: str, default: str = "") -> str:
    """Read a config value from the environment first, then Streamlit secrets."""
    value = os.environ.get(key, "").strip()
    if value:
        return value
    try:
        import streamlit as st

        found = st.secrets.get(key, "")
        return str(found).strip() if found else default
    except Exception:  # no secrets.toml, or running outside Streamlit — both fine
        return default


def github_config() -> dict[str, str] | None:
    """None unless a token and a data repo are both configured."""
    token = _setting("GITHUB_TOKEN")
    repo = _setting("MIM_DATA_REPO")
    if not token or not repo:
        return None
    return {
        "token": token,
        "repo": repo,
        "branch": _setting("MIM_DATA_BRANCH", "main"),
        "path": _setting("MIM_DATA_PATH", "data").strip("/"),
    }


def backend() -> str:
    return "github" if github_config() else "local"


def _note(error: Exception | str) -> None:
    global LAST_ERROR
    LAST_ERROR = str(error)


def _clear_error() -> None:
    global LAST_ERROR
    LAST_ERROR = None


# ---------------------------------------------------------------- github transport


def _gh_request(url: str, token: str, method: str = "GET", payload: dict | None = None,
                timeout: int = 15) -> dict:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=body, method=method)
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    request.add_header("User-Agent", "MIM-MEM-Digital")
    if body:
        request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw) if raw else {}


def _gh_read(name: str, cfg: dict[str, str]) -> tuple[Any, str]:
    url = f"{GITHUB_API}/repos/{cfg['repo']}/contents/{cfg['path']}/{name}.json?ref={cfg['branch']}"
    try:
        payload = _gh_request(url, cfg["token"])
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise FileNotFoundError(f"{name}.json not in {cfg['repo']}") from exc
        if exc.code in (401, 403):
            raise StorageError(f"GitHub refused the token ({exc.code}). Check that it can read/write "
                               f"Contents on {cfg['repo']}.") from exc
        raise StorageError(f"GitHub error {exc.code} reading {name}.json") from exc
    except urllib.error.URLError as exc:
        raise StorageError(f"No route to api.github.com: {exc.reason}") from exc
    content = base64.b64decode(payload.get("content", "")).decode("utf-8")
    return json.loads(content or ("{}" if name == "settings" else "[]")), payload.get("sha", "")


def _gh_write(name: str, payload: Any, cfg: dict[str, str], sha: str | None = None) -> str:
    url = f"{GITHUB_API}/repos/{cfg['repo']}/contents/{cfg['path']}/{name}.json"
    body: dict[str, Any] = {
        "message": f"MIM sync: {name} ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
        "content": base64.b64encode(json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")).decode("ascii"),
        "branch": cfg["branch"],
        "committer": {"name": "MIM", "email": "mim@memdigital.studio"},
    }
    if sha:
        body["sha"] = sha
    try:
        result = _gh_request(url, cfg["token"], method="PUT", payload=body)
    except urllib.error.HTTPError as exc:
        if exc.code == 409:
            _, fresh_sha = _gh_read(name, cfg)
            return _gh_write(name, payload, cfg, fresh_sha)
        raise StorageError(f"GitHub error {exc.code} writing {name}.json") from exc
    except urllib.error.URLError as exc:
        raise StorageError(f"No route to api.github.com: {exc.reason}") from exc
    return result.get("content", {}).get("sha", "")


# ---------------------------------------------------------------- load / save


def load(name: str, default: Any = None) -> Any:
    fallback = default if default is not None else ({} if name == "settings" else [])
    cfg = github_config()
    if cfg:
        if name in _DIRTY:
            # A push failed earlier. Serve what the operator actually wrote, not the
            # stale remote — otherwise their edit appears to vanish mid-session.
            return _local_load(name, fallback)
        cached = _CACHE.get(name)
        if cached and (time.time() - cached[0]) < _CACHE_TTL:
            return copy.deepcopy(cached[1])
        try:
            payload, sha = _gh_read(name, cfg)
        except FileNotFoundError:
            return fallback
        except StorageError as exc:
            _note(exc)
            return _local_load(name, fallback)
        else:
            _CACHE[name] = (time.time(), payload)
            _SHAS[name] = sha
            _clear_error()
            return copy.deepcopy(payload)
    return _local_load(name, fallback)


def _local_load(name: str, fallback: Any) -> Any:
    p = path_for(name)
    if not p.exists():
        return fallback
    with p.open(encoding="utf-8") as fh:
        return json.load(fh)


def save(name: str, payload: Any) -> Path:
    global LAST_SYNC
    path = _local_save(name, payload)
    _CACHE[name] = (time.time(), copy.deepcopy(payload))
    cfg = github_config()
    if cfg:
        try:
            _SHAS[name] = _gh_write(name, payload, cfg, _SHAS.get(name))
            LAST_SYNC = time.time()
            _DIRTY.discard(name)
            _clear_error()
        except StorageError as exc:
            # Local mirror already holds the change; the operator sees the failure.
            _DIRTY.add(name)
            _note(exc)
    return path


def sync_now() -> None:
    """Push anything the remote rejected, then pull fresh state for every collection."""
    cfg = github_config()
    if not cfg:
        _CACHE.clear()
        return

    for name in sorted(_DIRTY):          # retry the failed pushes first
        payload = _local_load(name, {} if name == "settings" else [])
        try:
            _SHAS[name] = _gh_write(name, payload, cfg, _SHAS.get(name))
            LAST_SYNC = time.time()
            _DIRTY.discard(name)
            _clear_error()
        except StorageError as exc:
            _note(exc)

    _CACHE.clear()
    _SHAS.clear()
    for name in COLLECTIONS:
        if name not in _DIRTY:
            load(name)


def status() -> dict[str, Any]:
    cfg = github_config()
    return {
        "backend": "github" if cfg else "local",
        "repo": cfg["repo"] if cfg else None,      # never the token
        "branch": cfg["branch"] if cfg else None,
        "path": cfg["path"] if cfg else str(DATA_DIR),
        "last_error": LAST_ERROR,
        "last_sync": datetime.fromtimestamp(LAST_SYNC).isoformat(timespec="seconds") if LAST_SYNC else None,
        "cached": sorted(_CACHE),
        "pending_push": sorted(_DIRTY),
    }


def _local_save(name: str, payload: Any) -> Path:
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
    """Create the book on first run — locally, or in your data repo when configured."""
    from . import seed

    if force:
        for name in COLLECTIONS:
            save(name, seed.build(name))
        return

    if github_config():
        for name in COLLECTIONS:
            if not load(name):          # nothing on the remote yet: seed it and push
                save(name, seed.build(name))
        return

    if not all(path_for(n).exists() for n in COLLECTIONS):
        for name in COLLECTIONS:
            if not path_for(name).exists():
                save(name, seed.build(name))


def dump() -> dict[str, Any]:
    return {name: load(name) for name in COLLECTIONS}


def import_book(payload: dict[str, Any], merge: bool = False) -> dict[str, int]:
    """Restore a book from an exported JSON. `merge` appends instead of replacing.

    Returns {collection: records written}. Unknown keys are ignored, never guessed at.
    """
    written: dict[str, int] = {}
    for name in COLLECTIONS:
        if name not in payload:
            continue
        incoming = payload[name]
        if merge and name != "settings":
            existing = load(name, [])
            seen = {row.get("id") for row in existing}
            combined = existing + [row for row in incoming if row.get("id") not in seen]
            save(name, combined)
            written[name] = len(combined) - len(existing)
        else:
            save(name, incoming)
            written[name] = len(incoming) if isinstance(incoming, list) else 1
    return written


def writable() -> bool:
    """Can this process persist? A configured data repo counts as writable storage."""
    if github_config():
        return True
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        probe = DATA_DIR / ".mim-write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False
