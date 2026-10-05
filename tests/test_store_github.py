"""The github backend: the same book, committed to a repo you own.

A fake GitHub API stands in for the network so the tests are deterministic and offline.
The important behaviours: reads are cached, writes mirror locally first, and a failing
remote never silently eats a change.
"""

from __future__ import annotations

import base64
import json
import urllib.error

import pytest

from mim import store

CFG = {"token": "ghp_fake", "repo": "mem/mim-book", "branch": "main", "path": "data"}


class FakeGitHub:
    """Minimal in-memory stand-in for the Contents API."""

    def __init__(self):
        self.files: dict[str, dict] = {}
        self.puts: list[str] = []
        self.reads: list[str] = []
        self.fail_reads = False
        self.fail_writes = False
        self.conflict_once: set[str] = set()

    def request(self, url: str, token: str, method: str = "GET", payload: dict | None = None,
                timeout: int = 15) -> dict:
        assert token == CFG["token"], "token must be passed through"
        name = url.split("/")[-1].split("?")[0]

        if method == "GET":
            if self.fail_reads:
                raise urllib.error.HTTPError(url, 401, "unauthorized", {}, None)  # type: ignore[arg-type]
            self.reads.append(name)
            if name not in self.files:
                raise urllib.error.HTTPError(url, 404, "not found", {}, None)  # type: ignore[arg-type]
            entry = self.files[name]
            return {"content": base64.b64encode(json.dumps(entry["body"]).encode()).decode(), "sha": entry["sha"]}

        if method == "PUT":
            if self.fail_writes:
                raise urllib.error.URLError("network down")
            if name in self.conflict_once:
                self.conflict_once.discard(name)
                raise urllib.error.HTTPError(url, 409, "conflict", {}, None)  # type: ignore[arg-type]
            body = json.loads(base64.b64decode(payload["content"]).decode())
            if payload.get("sha") and self.files.get(name, {}).get("sha") != payload["sha"]:
                raise urllib.error.HTTPError(url, 409, "stale sha", {}, None)  # type: ignore[arg-type]
            self.puts.append(name)
            sha = f"sha-{len(self.puts):03d}"
            self.files[name] = {"body": body, "sha": sha}
            return {"content": {"sha": sha}}
        raise AssertionError(method)


@pytest.fixture()
def gh(monkeypatch, tmp_path):
    fake = FakeGitHub()
    monkeypatch.setenv("MIM_DATA_DIR", str(tmp_path / "mirror"))
    monkeypatch.setenv("GITHUB_TOKEN", CFG["token"])
    monkeypatch.setenv("MIM_DATA_REPO", CFG["repo"])
    monkeypatch.setenv("MIM_DATA_BRANCH", CFG["branch"])
    monkeypatch.setenv("MIM_DATA_PATH", CFG["path"])
    monkeypatch.setattr(store, "_gh_request", fake.request)
    store._CACHE.clear()
    store._SHAS.clear()
    store._clear_error()
    yield fake
    store._CACHE.clear()
    store._SHAS.clear()
    for key in ("GITHUB_TOKEN", "MIM_DATA_REPO", "MIM_DATA_BRANCH", "MIM_DATA_PATH"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("MIM_DATA_DIR", str(store.DATA_DIR))


# ---------------------------------------------------------------- config

def test_backend_is_local_without_credentials(monkeypatch):
    for key in ("GITHUB_TOKEN", "MIM_DATA_REPO"):
        monkeypatch.delenv(key, raising=False)
    assert store.backend() == "local"
    assert store.github_config() is None


def test_backend_is_github_with_both_credentials(gh):
    assert store.backend() == "github"
    assert store.status()["repo"] == "mem/mim-book"
    assert "token" not in json.dumps(store.status()), "the token must never be exposed"


def test_half_configured_backend_stays_local(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_fake")
    monkeypatch.delenv("MIM_DATA_REPO", raising=False)
    assert store.backend() == "local", "a token without a repo must not switch backends"


# ---------------------------------------------------------------- read path

def test_first_run_seeds_the_remote_repo(gh):
    store.bootstrap()
    assert set(gh.files) == {"settings.json", "clients.json", "invoices.json", "projects.json", "messages.json"}
    assert store.load("clients")[0]["id"] == "C-001"
    assert store.status()["last_error"] is None


def test_bootstrap_does_not_clobber_an_existing_remote_book(gh):
    store.bootstrap()
    store.save("clients", [{"id": "C-900", "name": "Only mine", "stage": "Active"}])
    store.bootstrap()
    assert [c["id"] for c in store.load("clients")] == ["C-900"]


def test_reads_are_cached_between_renders(gh):
    store.bootstrap()
    reads_after_seed = len([r for r in gh.reads if r == "clients.json"])
    for _ in range(5):
        store.load("clients")
    assert len([r for r in gh.reads if r == "clients.json"]) == reads_after_seed, "cache must absorb repeat reads"


def test_sync_now_forces_a_fresh_pull(gh):
    store.bootstrap()
    store.sync_now()
    assert "clients.json" in gh.reads


# ---------------------------------------------------------------- write path

def test_save_pushes_to_github_and_mirrors_locally(gh):
    store.bootstrap()
    store.save("clients", [{"id": "C-777", "name": "Pushed", "stage": "Lead"}])
    assert gh.files["clients.json"]["body"][0]["id"] == "C-777"
    mirrored = json.loads((store.DATA_DIR / "clients.json").read_text())
    assert mirrored[0]["id"] == "C-777", "the local mirror is the safety net"
    assert store.status()["last_sync"] is not None


def test_service_writes_reach_the_remote_repo(gh):
    from mim import service

    store.bootstrap()
    cid = service.new_client({"name": "Remote Person", "company": "Remote Co", "stage": "Lead"})
    remote_ids = [c["id"] for c in gh.files["clients.json"]["body"]]
    assert cid in remote_ids


def test_read_after_write_is_consistent(gh):
    store.bootstrap()
    store.save("invoices", [{"id": "MEM-2099-001", "status": "draft"}])
    assert store.load("invoices")[0]["id"] == "MEM-2099-001"


def test_write_conflict_refreshes_the_sha_and_retries(gh):
    store.bootstrap()
    gh.conflict_once.add("clients.json")
    store.save("clients", [{"id": "C-555", "name": "Retried", "stage": "Lead"}])
    assert gh.files["clients.json"]["body"][0]["id"] == "C-555"
    assert store.status()["last_error"] is None


# ---------------------------------------------------------------- failure modes

def test_read_failure_falls_back_to_the_local_mirror_and_reports(gh):
    store.bootstrap()
    store.save("clients", [{"id": "C-123", "name": "Mirrored", "stage": "Active"}])
    store._CACHE.clear()
    gh.fail_reads = True
    rows = store.load("clients")
    assert rows[0]["id"] == "C-123", "the mirror keeps the console usable offline"
    assert "token" in (store.status()["last_error"] or "").lower()


def test_write_failure_keeps_the_change_locally_and_flags_it(gh):
    store.bootstrap()
    gh.fail_writes = True
    store.save("clients", [{"id": "C-321", "name": "Survives", "stage": "Lead"}])
    assert store.status()["last_error"] is not None
    assert store.status()["pending_push"] == ["clients"]
    store._CACHE.clear()
    assert store.load("clients")[0]["id"] == "C-321", "the operator's write must not appear to vanish"
    gh.fail_writes = False
    store.sync_now()
    assert gh.files["clients.json"]["body"][0]["id"] == "C-321", "sync_now flushes the pending push"
    assert store.status()["pending_push"] == []
    assert store.status()["last_error"] is None


def test_expired_token_message_is_actionable(gh):
    gh.fail_reads = True
    store.load("clients")
    message = store.status()["last_error"] or ""
    assert "token" in message.lower() and "Contents" in message


def test_writable_true_when_the_data_repo_is_configured(gh):
    assert store.writable() is True


def test_import_book_pushes_a_restored_export(gh):
    store.bootstrap()
    exported = store.dump()
    exported["clients"] = exported["clients"][:1]
    written = store.import_book(exported)
    assert written["clients"] == 1
    assert len(gh.files["clients.json"]["body"]) == 1
