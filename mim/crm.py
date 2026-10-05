"""Pillar 1 — CRM. Pipeline truth, health scoring and communication gaps."""

from __future__ import annotations

from datetime import date
from typing import Any

from .finance import days_overdue, effective_status, invoice_balance, open_invoices
from .models import (
    DEFAULT_CADENCE,
    STAGES,
    STAGE_PROBABILITY,
    days_since,
    index_by,
    parse_date,
)

# ---------------------------------------------------------------- pipeline


def pipeline_summary(clients: list[dict]) -> list[dict]:
    rows = []
    for stage in STAGES:
        in_stage = [c for c in clients if c.get("stage") == stage]
        value = round(sum(float(c.get("deal_value", 0) or 0) for c in in_stage), 2)
        rows.append({
            "stage": stage,
            "clients": len(in_stage),
            "value": value,
            "probability": STAGE_PROBABILITY[stage],
            "weighted": round(value * STAGE_PROBABILITY[stage], 2),
        })
    return rows


def weighted_pipeline(clients: list[dict]) -> float:
    return round(
        sum(float(c.get("deal_value", 0) or 0) * STAGE_PROBABILITY.get(c.get("stage", "Lead"), 0.0) for c in clients),
        2,
    )


def win_rate(clients: list[dict]) -> float | None:
    won = lost = 0
    for client in clients:
        for move in client.get("stage_history", []):
            if move.get("to") == "Active":
                won += 1
            elif move.get("to") == "Lost":
                lost += 1
    total = won + lost
    return round(won / total * 100, 0) if total else None


def avg_deal(clients: list[dict]) -> float:
    active = [float(c.get("deal_value", 0) or 0) for c in clients if c.get("stage") in ("Active", "Completed")]
    return round(sum(active) / len(active), 2) if active else 0.0


def client_value(client: dict, invoices: list[dict], today: date) -> dict:
    mine = [i for i in invoices if i.get("client_id") == client.get("id") and effective_status(i, today) != "void"]
    billed = sum(invoice_balance(i) + sum(float(p.get("amount", 0) or 0) for p in i.get("payments", [])) for i in mine)
    paid = sum(float(p.get("amount", 0) or 0) for i in mine for p in i.get("payments", []))
    outstanding = sum(invoice_balance(i) for i in mine if effective_status(i, today) in ("sent", "partial", "overdue"))
    return {
        "lifetime_billed": round(billed, 2),
        "lifetime_collected": round(paid, 2),
        "outstanding": round(outstanding, 2),
        "invoices": len(mine),
        "avg_invoice": round(billed / len(mine), 2) if mine else 0.0,
    }


# ---------------------------------------------------------------- health


def cadence_for(client: dict, settings: dict) -> int:
    cadence = (settings.get("cadence_days") or {})
    return int(cadence.get(client.get("stage", "Lead"), DEFAULT_CADENCE.get(client.get("stage", "Lead"), 7)))


def communication_gaps(clients: list[dict], settings: dict, today: date) -> list[dict]:
    """Silence is a decision. MIM flags every thread going cold."""
    rows = []
    for client in clients:
        if client.get("stage") in ("Completed",) and client.get("stage") == "Completed" and client.get("nurture") is False:
            continue
        threshold = cadence_for(client, settings)
        delta = days_since(client.get("last_contact"), today)
        if delta is None:
            rows.append({
                "client": client.get("company") or client.get("name", "—"),
                "client_id": client.get("id"),
                "stage": client.get("stage", "—"),
                "last_contact": "never",
                "days_silent": 9999,
                "threshold": threshold,
                "severity": "Critical",
                "action": "First touch. No history on file.",
            })
            continue
        over = delta - threshold
        if over < 0:
            continue
        severity = "Critical" if over >= max(threshold, 7) else "Warning"
        rows.append({
            "client": client.get("company") or client.get("name", "—"),
            "client_id": client.get("id"),
            "stage": client.get("stage", "—"),
            "last_contact": client.get("last_contact", "—"),
            "days_silent": delta,
            "threshold": threshold,
            "severity": severity,
            "action": gap_play(client, delta, threshold),
        })
    return sorted(rows, key=lambda r: (-r["days_silent"], r["client"]))


def gap_play(client: dict, days_silent: int, threshold: int) -> str:
    stage = client.get("stage", "Lead")
    over = days_silent - threshold
    if stage == "Proposal Sent":
        return f"Decision nudge — proposal sat {days_silent}d. Offer a 15-min yes/no call."
    if stage in ("Lead", "Contacted"):
        return f"Re-open the thread with a specific idea, not a check-in. {over}d past cadence."
    if stage == "Upsell":
        return "Send the upsell angle with a deadline attached."
    if stage == "Completed":
        return "Close the loop, ask for a referral and the testimonial while results are fresh."
    return f"Client update due — {over}d past cadence. Ship value before you ask for anything."


def health(client: dict, invoices: list[dict], projects: list[dict], settings: dict, today: date) -> dict:
    """0-100 account health with the reasons spelled out. No black box."""
    score = 100
    reasons: list[str] = []
    delta = days_since(client.get("last_contact"), today)
    threshold = cadence_for(client, settings)
    if delta is None:
        score -= 30
        reasons.append("No contact on record")
    elif delta > threshold * 2:
        score -= 25
        reasons.append(f"{delta}d silent (cadence {threshold}d)")
    elif delta > threshold:
        score -= 12
        reasons.append(f"{delta}d silent (cadence {threshold}d)")

    cid = client.get("id")
    overdue = [i for i in invoices if i.get("client_id") == cid and days_overdue(i, today) > 0]
    if overdue:
        owed = sum(invoice_balance(i) for i in overdue)
        score -= min(30, 10 + len(overdue) * 8)
        reasons.append(f"{len(overdue)} overdue invoice(s) — {owed:,.0f} at risk")

    for project in projects:
        if project.get("client_id") != cid or project.get("status") != "Active":
            continue
        if project.get("health_flag") == "At Risk":
            score -= 12
            reasons.append(f"{project.get('name')} at risk")
        if project.get("scope_exposure"):
            score -= 8
            reasons.append("Unbilled scope exposure")
    if client.get("stage") == "Upsell":
        reasons.append("Upsell window open")
    if not reasons:
        reasons.append("Clean: on cadence, nothing overdue")

    score = max(0, min(100, score))
    band = "Healthy" if score >= 80 else "Watch" if score >= 60 else "At Risk" if score >= 40 else "Critical"
    return {"score": score, "band": band, "reasons": reasons}


def comm_gap_queue(clients: list[dict], settings: dict, today: date) -> list[dict]:
    return [g for g in communication_gaps(clients, settings, today) if g["severity"] == "Critical"]


def next_actions_due(clients: list[dict], today: date) -> list[dict]:
    rows = []
    for client in clients:
        action = client.get("next_action") or {}
        if not action.get("note"):
            continue
        due = parse_date(action.get("due"))
        days = (due - today).days if due else None
        rows.append({
            "client": client.get("company") or client.get("name", "—"),
            "client_id": client.get("id"),
            "stage": client.get("stage", "—"),
            "action": action.get("note", "—"),
            "due": action.get("due", "—"),
            "in_days": days,
            "state": "Overdue" if (days is not None and days < 0) else "Today" if days == 0 else "Scheduled",
        })
    return sorted(rows, key=lambda r: (r["in_days"] is None, r["in_days"] if r["in_days"] is not None else 999))


def upsell_candidates(clients: list[dict], projects: list[dict], settings: dict, today: date) -> list[dict]:
    """Hit the window while the work is still fresh."""
    rows = []
    for client in clients:
        cid = client.get("id")
        mine = [p for p in projects if p.get("client_id") == cid]
        done = [p for p in mine if p.get("status") in ("Completed", "Delivered")]
        active = [p for p in mine if p.get("status") == "Active"]
        trigger = None
        if client.get("stage") == "Completed":
            trigger = "Project delivered — upsell/retainer window"
        elif active and any((p.get("progress") or 0) >= 80 for p in active):
            trigger = "Active project past 80% — line up the next phase"
        elif done and not active:
            trigger = "No live scope. Reactivate with a phase 2."
        if not trigger:
            continue
        rows.append({
            "client": client.get("company") or client.get("name", "—"),
            "client_id": cid,
            "stage": client.get("stage", "—"),
            "trigger": trigger,
            "deal_value": client.get("deal_value", 0),
            "suggested": round(float(client.get("deal_value", 0) or 0) * 0.4, 2),
            "language": client.get("language", "EN"),
        })
    return rows


def stage_history_rows(clients: list[dict]) -> list[dict]:
    rows = []
    for client in clients:
        for move in client.get("stage_history", []):
            rows.append({
                "date": move.get("date", "—"),
                "client": client.get("company") or client.get("name", "—"),
                "from": move.get("from", "—"),
                "to": move.get("to", "—"),
                "value": move.get("value", client.get("deal_value", 0)),
            })
    return sorted(rows, key=lambda r: r["date"], reverse=True)


def at_risk_accounts(clients: list[dict], invoices: list[dict], projects: list[dict], settings: dict, today: date) -> list[dict]:
    rows = []
    for client in clients:
        h = health(client, invoices, projects, settings, today)
        if h["band"] in ("At Risk", "Critical") or days_overdue_check(client, invoices, today):
            rows.append({
                "client": client.get("company") or client.get("name", "—"),
                "client_id": client.get("id"),
                "stage": client.get("stage", "—"),
                "deal_value": client.get("deal_value", 0),
                "health": h["score"],
                "band": h["band"],
                "why": " · ".join(h["reasons"][:2]),
            })
    return sorted(rows, key=lambda r: r["health"])


def days_overdue_check(client: dict, invoices: list[dict], today: date) -> bool:
    cid = client.get("id")
    return any(days_overdue(i, today) > 0 for i in invoices if i.get("client_id") == cid)
