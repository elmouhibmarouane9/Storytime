"""Mutations. Everything the UI writes goes through here — one audit trail, no drift."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from . import finance
from .models import STAGES, next_id, parse_date
from .store import load, save, today as _today


def _reload() -> dict[str, Any]:
    return {
        "settings": load("settings", {}),
        "clients": load("clients", []),
        "invoices": load("invoices", []),
        "projects": load("projects", []),
        "messages": load("messages", []),
    }


def _commit(book: dict[str, Any], keys: list[str]) -> None:
    for key in keys:
        save(key, book[key])


# ---------------------------------------------------------------- clients

def new_client(payload: dict[str, Any]) -> str:
    book = _reload()
    cid = payload.get("id") or next_id("C", [c["id"] for c in book["clients"]])
    client = {
        "id": cid,
        "name": payload.get("name", "").strip() or "Unnamed",
        "company": payload.get("company", "").strip() or payload.get("name", "Unnamed"),
        "email": payload.get("email", ""),
        "phone": payload.get("phone", ""),
        "role": payload.get("role", ""),
        "location": payload.get("location", ""),
        "language": payload.get("language", "EN"),
        "stage": payload.get("stage", "Lead"),
        "tags": payload.get("tags", []),
        "deal_value": float(payload.get("deal_value", 0) or 0),
        "currency": payload.get("currency", "USD"),
        "since": payload.get("since") or _today().isoformat(),
        "source": payload.get("source", ""),
        "timezone": payload.get("timezone", ""),
        "communication_style": payload.get("communication_style", ""),
        "preferences": payload.get("preferences", []),
        "payment_behaviour": payload.get("payment_behaviour", ""),
        "notes": payload.get("notes", ""),
        "last_contact": payload.get("last_contact") or _today().isoformat(),
        "next_action": payload.get("next_action", {}),
        "stage_history": [{"from": "—", "to": payload.get("stage", "Lead"),
                           "date": _today().isoformat(), "value": float(payload.get("deal_value", 0) or 0)}],
    }
    book["clients"].append(client)
    _commit(book, ["clients"])
    return cid


def update_client(client_id: str, payload: dict[str, Any]) -> None:
    book = _reload()
    for client in book["clients"]:
        if client["id"] == client_id:
            client.update({k: v for k, v in payload.items() if k not in ("id", "stage", "stage_history")})
            break
    _commit(book, ["clients"])


def set_stage(client_id: str, stage: str, value: float | None = None, note: str = "") -> None:
    book = _reload()
    for client in book["clients"]:
        if client["id"] != client_id:
            continue
        old = client.get("stage", "Lead")
        if old == stage:
            return
        client["stage"] = stage
        if value is not None:
            client["deal_value"] = float(value)
        history = client.setdefault("stage_history", [])
        entry = {"from": old, "to": stage, "date": _today().isoformat(),
                 "value": float(client.get("deal_value", 0) or 0)}
        if note:
            entry["note"] = note
        history.append(entry)
        client["last_contact"] = _today().isoformat()
        break
    _commit(book, ["clients"])


def set_next_action(client_id: str, note: str, due: str) -> None:
    book = _reload()
    for client in book["clients"]:
        if client["id"] == client_id:
            client["next_action"] = {"note": note, "due": due}
            break
    _commit(book, ["clients"])


def log_communication(client_id: str, payload: dict[str, Any]) -> str:
    book = _reload()
    mid = next_id("M", [m["id"] for m in book["messages"]])
    when = payload.get("date") or _today().isoformat()
    message = {
        "id": mid,
        "client_id": client_id,
        "date": when,
        "channel": payload.get("channel", "email"),
        "direction": payload.get("direction", "out"),
        "subject": payload.get("subject", ""),
        "summary": payload.get("summary", ""),
    }
    if payload.get("reminder_tier"):
        message["reminder_tier"] = int(payload["reminder_tier"])
    book["messages"].append(message)
    for client in book["clients"]:
        if client["id"] == client_id:
            client["last_contact"] = when
            break
    _commit(book, ["messages", "clients"])
    return mid


def update_message(message_id: str, payload: dict[str, Any]) -> None:
    book = _reload()
    for message in book["messages"]:
        if message["id"] == message_id:
            message.update(payload)
            message.pop("_edit", None)
            break
    _commit(book, ["messages"])


# ---------------------------------------------------------------- invoices

def create_invoice(payload: dict[str, Any]) -> str:
    book = _reload()
    settings = book["settings"]
    issued = payload.get("issue_date") or _today().isoformat()
    terms_days = int(payload.get("terms_days", 14) or 14)
    due = payload.get("due_date") or (parse_date(issued) + timedelta(days=terms_days)).isoformat()
    inv_id = next_id("MEM", [i["id"] for i in book["invoices"]], width=3, year=True)
    invoice = {
        "id": inv_id,
        "client_id": payload.get("client_id"),
        "project_id": payload.get("project_id"),
        "issue_date": issued,
        "due_date": due,
        "currency": payload.get("currency") or book_settings_currency(settings, payload.get("client_id"), book),
        "terms": payload.get("terms", (settings.get("invoice") or {}).get("default_terms", "Net 14")),
        "status": payload.get("status", "draft"),
        "tax_rate": float(payload.get("tax_rate", (settings.get("invoice") or {}).get("tax_rate", 0)) or 0),
        "discount": float(payload.get("discount", 0) or 0),
        "notes": payload.get("notes", ""),
        "items": payload.get("items", []),
        "payments": [],
        "reminders": [],
    }
    book["invoices"].append(invoice)
    inv_cfg = settings.setdefault("invoice", {})
    inv_cfg["next_number"] = int(inv_cfg.get("next_number", 1) or 1) + 1
    _commit(book, ["invoices", "settings"])
    return inv_id


def book_settings_currency(settings: dict, client_id: str | None, book: dict) -> str:
    for client in book["clients"]:
        if client["id"] == client_id and client.get("currency"):
            return client["currency"]
    return settings.get("currency", "USD")


def record_payment(invoice_id: str, amount: float, when: str | None = None,
                   method: str = "wire", note: str = "") -> None:
    book = _reload()
    for invoice in book["invoices"]:
        if invoice["id"] != invoice_id:
            continue
        invoice.setdefault("payments", []).append({
            "date": when or _today().isoformat(),
            "amount": round(float(amount), 2),
            "method": method,
            "note": note,
        })
        balance = finance.invoice_balance(invoice)
        if balance <= 0.005:
            invoice["status"] = "paid"
        elif invoice["status"] in ("draft", "paid", "void"):
            invoice["status"] = "sent"
        break
    _commit(book, ["invoices"])


def set_invoice_status(invoice_id: str, status: str) -> None:
    book = _reload()
    for invoice in book["invoices"]:
        if invoice["id"] == invoice_id:
            invoice["status"] = status
            break
    _commit(book, ["invoices"])


def log_reminder(invoice_id: str, tier: int, channel: str = "email", when: str | None = None) -> None:
    book = _reload()
    when = when or _today().isoformat()
    invoice = None
    for row in book["invoices"]:
        if row["id"] == invoice_id:
            invoice = row
            break
    if invoice is None:
        return
    invoice.setdefault("reminders", []).append({"date": when, "tier": int(tier), "channel": channel})
    log_communication(invoice.get("client_id", ""), {
        "date": when, "channel": channel, "direction": "out",
        "subject": f"Reminder: invoice {invoice_id}",
        "summary": f"Tier {tier} reminder sent on {invoice_id}.",
        "reminder_tier": int(tier),
    })
    _commit(book, ["invoices"])


def delete_invoice(invoice_id: str) -> None:
    book = _reload()
    book["invoices"] = [i for i in book["invoices"] if i["id"] != invoice_id]
    _commit(book, ["invoices"])


# ---------------------------------------------------------------- projects

def create_project(payload: dict[str, Any]) -> str:
    book = _reload()
    pid = next_id("P", [p["id"] for p in book["projects"]])
    project = {
        "id": pid,
        "client_id": payload.get("client_id"),
        "name": payload.get("name", "New project"),
        "status": payload.get("status", "Active"),
        "start": payload.get("start") or _today().isoformat(),
        "due": payload.get("due"),
        "budget": float(payload.get("budget", 0) or 0),
        "currency": payload.get("currency", "USD"),
        "hourly_rate": float(payload.get("hourly_rate", 0) or 0),
        "included_revisions": int(payload.get("included_revisions", 2) or 2),
        "scope_summary": payload.get("scope_summary", ""),
        "tasks": payload.get("tasks", []),
        "deliverables": payload.get("deliverables", []),
        "time_entries": [],
        "change_orders": [],
        "risks": [],
        "health_flag": "Healthy",
        "scope_exposure": False,
    }
    book["projects"].append(project)
    _commit(book, ["projects"])
    return pid


def update_project(project_id: str, payload: dict[str, Any]) -> None:
    book = _reload()
    for project in book["projects"]:
        if project["id"] == project_id:
            project.update({k: v for k, v in payload.items() if k != "id"})
            break
    _commit(book, ["projects"])


def update_task(project_id: str, task_id: str, payload: dict[str, Any]) -> None:
    book = _reload()
    for project in book["projects"]:
        if project["id"] != project_id:
            continue
        for task in project.get("tasks", []):
            if task["id"] == task_id:
                task.update(payload)
                break
        break
    _commit(book, ["projects"])


def log_time(project_id: str, payload: dict[str, Any]) -> str:
    book = _reload()
    entry_id = None
    for project in book["projects"]:
        if project["id"] != project_id:
            continue
        entries = project.setdefault("time_entries", [])
        entry_id = next_id("TE", [e.get("id", "") for e in entries])
        entry = {
            "id": entry_id,
            "date": payload.get("date") or _today().isoformat(),
            "task_id": payload.get("task_id"),
            "hours": round(float(payload.get("hours", 0) or 0), 2),
            "note": payload.get("note", ""),
            "in_scope": bool(payload.get("in_scope", True)),
            "billable": bool(payload.get("billable", True)),
            "invoiced": False,
        }
        entries.append(entry)
        for task in project.get("tasks", []):
            if task.get("id") == payload.get("task_id"):
                task["logged_hours"] = round(float(task.get("logged_hours", 0) or 0) + entry["hours"], 2)
                break
        break
    _commit(book, ["projects"])
    return entry_id or ""


def create_change_order(project_id: str, payload: dict[str, Any]) -> str:
    from .projects import scope_exposure

    book = _reload()
    coid = payload.get("id")
    for project in book["projects"]:
        if project["id"] != project_id:
            continue
        orders = project.setdefault("change_orders", [])
        coid = coid or f"{project['id'].replace('P-', 'CO-')}-{len(orders) + 1:02d}"
        orders.append({
            "id": coid,
            "title": payload.get("title", "Scope change"),
            "amount": round(float(payload.get("amount", 0) or 0), 2),
            "hours": float(payload.get("hours", 0) or 0),
            "status": payload.get("status", "Draft"),
            "date": payload.get("date") or _today().isoformat(),
        })
        project["scope_exposure"] = scope_exposure(project) > 0
        break
    _commit(book, ["projects"])
    return coid or ""


def set_change_order_status(project_id: str, co_id: str, status: str) -> None:
    book = _reload()
    for project in book["projects"]:
        if project["id"] != project_id:
            continue
        for co in project.get("change_orders", []):
            if co["id"] == co_id:
                co["status"] = status
                break
        break
    _commit(book, ["projects"])


def set_approval(project_id: str, deliverable_name: str, state: str, when: str | None = None) -> None:
    book = _reload()
    when = when or _today().isoformat()
    for project in book["projects"]:
        if project["id"] != project_id:
            continue
        for deliverable in project.get("deliverables", []):
            if deliverable["name"] != deliverable_name:
                continue
            approval = deliverable.setdefault("approval", {})
            approval["state"] = state
            if state == "pending":
                approval["requested"] = when
            else:
                approval["decided"] = when
            if state == "approved":
                deliverable["status"] = "Approved"
            elif state == "changes requested":
                deliverable["status"] = "In Review"
            break
        break
    _commit(book, ["projects"])


def bill_time_to_invoice(project_id: str, status: str = "draft") -> str | None:
    """Convert a project's uninvoiced billable time into an invoice, then flag the time."""
    from .projects import bill_time_for_client, mark_time_invoiced

    book = _reload()
    project = next((p for p in book["projects"] if p["id"] == project_id), None)
    if not project:
        return None
    items, entry_ids = bill_time_for_client([project], project.get("client_id"))
    if not items:
        return None
    inv_id = create_invoice({
        "client_id": project.get("client_id"),
        "project_id": project_id,
        "items": items,
        "currency": project.get("currency"),
        "notes": f"Time-based billing — {project.get('name')}",
        "status": status,
    })
    if status == "sent":
        mark_time_invoiced([project], entry_ids)
        update_project(project_id, {"time_entries": project.get("time_entries", [])})
    return inv_id


def mark_project_time_invoiced(project_id: str) -> int:
    from .projects import mark_time_invoiced

    book = _reload()
    for project in book["projects"]:
        if project["id"] == project_id:
            touched = mark_time_invoiced([project], [e.get("id") for e in project.get("time_entries", [])
                                                    if not e.get("invoiced") and e.get("in_scope", True)])
            _commit(book, ["projects"])
            return touched
    return 0


def set_project_status(project_id: str, status: str) -> None:
    payload = {"status": status}
    if status == "Completed":
        payload["health_flag"] = "Healthy"
    update_project(project_id, payload)


# ---------------------------------------------------------------- settings & book

def update_settings(payload: dict[str, Any]) -> None:
    book = _reload()
    settings = book["settings"]
    for key, value in payload.items():
        if isinstance(value, dict) and isinstance(settings.get(key), dict):
            settings[key].update(value)
        else:
            settings[key] = value
    _commit(book, ["settings"])


def wipe_book(sample: bool = False) -> None:
    """Empty book (or reload the labelled sample). Irreversible by design."""
    from . import seed
    from .store import COLLECTIONS

    for name in COLLECTIONS:
        save(name, seed.build(name) if sample else ({} if name == "settings" else []))
    if not sample:
        update_settings({"sample_data": False})


def require_password() -> bool:
    """Optional gate for a public Streamlit deploy. No password set = no gate."""
    import os

    import streamlit as st

    expected = os.environ.get("MIM_ACCESS_CODE", "").strip()
    if not expected:
        return True
    if st.session_state.get("mim_unlocked"):
        return True
    st.markdown("### MIM access")
    entered = st.text_input("Access code", type="password", key="mim_code")
    if st.button("Unlock"):
        if entered.strip() == expected:
            st.session_state["mim_unlocked"] = True
            st.rerun()
        st.error("Wrong code.")
    return False
