"""Aggregation layer — turns the book into dashboards, and into next moves.

Nothing renders here. UI reads these dicts; tests assert on them.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from . import comms, crm, finance, projects
from .models import (
    add_months,
    days_since,
    find,
    money,
    month_start,
    pct,
)
from .store import load, today as _today


# ---------------------------------------------------------------- loads

def book() -> dict[str, Any]:
    return {
        "settings": load("settings", {}),
        "clients": load("clients", []),
        "invoices": load("invoices", []),
        "projects": load("projects", []),
        "messages": load("messages", []),
    }


def base_book(b: dict[str, Any] | None = None) -> dict[str, Any]:
    """The book with all money in the base currency — the only book you sum."""
    b = b or book()
    settings = b["settings"]
    out = dict(b)
    out["invoices"] = [finance.to_base_invoice(i, settings) for i in b["invoices"]]
    out["clients"] = [finance.to_base_client(c, settings) for c in b["clients"]]
    out["base_currency"] = finance.base_currency(settings)
    return out


def currency_breakdown(by_currency: dict[str, float]) -> str:
    """["USD": 4800, "EUR": 7200] -> "$4,800 · €7,200" — native amounts, biggest first."""
    parts = [money(value, code) for code, value in sorted(by_currency.items(), key=lambda kv: -kv[1]) if value]
    return " · ".join(parts) if parts else "—"


def native_pipeline_breakdown(clients: list[dict]) -> dict[str, float]:
    out: dict[str, float] = {}
    for client in clients:
        code = client.get("currency", "USD")
        out[code] = round(out.get(code, 0.0) + float(client.get("deal_value", 0) or 0), 2)
    return out


def client_name(client: dict | None) -> str:
    if not client:
        return "—"
    return client.get("company") or client.get("name") or "—"


def client_options(book_: dict[str, Any] | None = None, stages: list[str] | None = None) -> list[tuple[str, str]]:
    b = book_ or book()
    rows = b["clients"]
    if stages:
        rows = [c for c in rows if c.get("stage") in stages]
    return [(c["id"], f"{client_name(c)} · {c.get('stage', '—')}") for c in sorted(rows, key=client_name)]


def currency_of(book_: dict[str, Any], client_id: str | None = None) -> str:
    client = find(book_["clients"], "id", client_id) if client_id else None
    return (client or {}).get("currency") or book_.get("settings", {}).get("currency", "USD")


# ---------------------------------------------------------------- pulse

def pulse(book_: dict[str, Any] | None = None, today: date | None = None) -> dict[str, Any]:
    native = book_ or book()
    today = today or _today()
    b = base_book(native)
    settings, clients, invoices, projs = b["settings"], b["clients"], b["invoices"], b["projects"]

    rev = finance.revenue_summary(invoices, today)
    port = projects.portfolio_summary(projs, today)
    target = float((settings.get("targets") or {}).get("monthly_revenue", 0) or 0)
    collected = rev["collected_mtd"]
    gaps = crm.communication_gaps(clients, settings, today)
    forecast = finance.cash_flow_forecast(invoices, clients, settings, today, 1)

    by_currency: dict[str, float] = {}
    for inv in finance.open_invoices(native["invoices"], today):
        cur = inv.get("currency", "USD")
        by_currency[cur] = round(by_currency.get(cur, 0.0) + finance.invoice_balance(inv), 2)

    return {
        "date": today.isoformat(),
        "base_currency": b["base_currency"],
        "outstanding_by_currency": by_currency,
        "clients": len(clients),
        "active_clients": sum(1 for c in clients if c.get("stage") == "Active"),
        "pipeline": crm.weighted_pipeline(clients),
        "pipeline_raw": sum(float(c.get("deal_value", 0) or 0) for c in clients),
        "collected_mtd": collected,
        "collected_ytd": rev["collected_ytd"],
        "billed_mtd": rev["billed_mtd"],
        "outstanding": rev["outstanding"],
        "overdue": rev["overdue"],
        "overdue_count": rev["overdue_count"],
        "draft_value": rev["draft_value"],
        "target": target,
        "gap_to_target": round(max(target - collected, 0), 2),
        "target_pct": round(collected / target * 100, 0) if target else None,
        "avg_days_to_pay": rev["avg_days_to_pay"],
        "projects_active": port["active"],
        "projects_at_risk": port["at_risk"],
        "projects_critical": port["critical"],
        "scope_exposure": port["scope_exposure"],
        "unbilled": port["unbilled"],
        "unbilled_hours": port["unbilled_hours"],
        "comm_gaps": len([g for g in gaps if g["severity"] == "Critical"]),
        "pending_approvals": len(projects.pending_approvals(projs, clients, today)),
        "win_rate": crm.win_rate(clients),
        "avg_deal": crm.avg_deal(clients),
        "expected_month": forecast[0]["expected"] if forecast else 0.0,
        "sample": bool(settings.get("sample_data")),
    }


# ---------------------------------------------------------------- next moves

def next_moves(book_: dict[str, Any] | None = None, today: date | None = None, limit: int = 2) -> list[dict[str, Any]]:
    """Every signal in the book, ranked by money at stake x urgency.

    Values are scored in the base currency; message text stays in the client's own
    currency, because that is the number you say out loud on the call.
    """
    native = book_ or book()
    today = today or _today()
    b = base_book(native)
    settings, clients, invoices, projs = b["settings"], b["clients"], b["invoices"], b["projects"]
    base = b["base_currency"]
    moves: list[dict[str, Any]] = []

    def add(move: str, why: str, value: float = 0.0, urgency: float = 1.0,
            where: str = "Dashboard", kind: str = "general", ref: str = "",
            currency: str | None = None) -> None:
        moves.append({
            "move": move, "why": why, "value": round(float(value or 0), 2),
            "urgency": urgency, "score": round(float(value or 0) * urgency, 2),
            "where": where, "kind": kind, "ref": ref, "currency": currency or base,
        })

    def native_amount(client_id: str | None, invoice_id: str | None = None) -> str:
        """The amount as the client sees it, in their currency."""
        if invoice_id:
            inv = find(native["invoices"], "id", invoice_id)
            if inv:
                return money(finance.invoice_balance(inv), inv.get("currency", base), 2 if _is_small(finance.invoice_balance(inv)) else 0)
        client = find(native["clients"], "id", client_id) if client_id else None
        if client:
            return money(client.get("deal_value", 0), client.get("currency", base))
        return money(0, base)

    # 1. Collections — overdue money, weighted by lateness.
    for row in finance.collection_queue(invoices, clients, today):
        if row["days_overdue"] <= 0:
            continue
        tier_urgency = {1: 1.2, 2: 1.8, 3: 2.6}[row["tier"]]
        tone = {1: "soft", 2: "firm", 3: "final notice"}[row["tier"]]
        add(
            f"Chase {row['invoice']} — {native_amount(row.get('client_id'), row['invoice'])} from {row['client']}",
            f"{row['days_overdue']} days past due. Tone: {tone}.",
            row["balance"], tier_urgency, "Invoices", "collection", row["invoice"],
        )
    # 2. Draft invoices sitting on the shelf.
    drafts = [i for i in invoices if i.get("status") == "draft"]
    if drafts:
        value = sum(finance.invoice_total(i) for i in drafts)
        add(
            f"Send {len(drafts)} draft invoice(s) — {money(value, base)}",
            "Drafts are revenue on the shelf. Send or delete.",
            value, 1.4, "Invoices", "draft",
        )
    # 3. Approved, unbilled change orders.
    for project in projs:
        convo_rate = finance.fx_rate(settings, project.get("currency"))
        for co in project.get("change_orders", []):
            if co.get("status") == "Approved":
                add(
                    f"Invoice change order {co.get('id')} — {money(co.get('amount', 0), project.get('currency', base))}",
                    f"{co.get('title')} approved {co.get('date')} on {project.get('name')}.",
                    float(co.get("amount", 0) or 0) * convo_rate, 2.0, "Projects", "change_order", project.get("id"),
                )
    # 4. Unbilled time — the cheapest cash in the building.
    unbilled = [row for row in projects.unbilled_by_client(projs, clients) if row["value"] > 0]
    if unbilled:
        top = unbilled[0]
        rate = finance.fx_rate(settings, top.get("currency"))
        extra = (f" Plus {top['out_of_scope_hours']}h outside scope — change order first."
                 if top["out_of_scope_value"] > 0 else "")
        add(
            f"Bill {top['hours']}h to {top['client']} — {money(top['value'], top.get('currency', base))} uninvoiced",
            "Delivered work, no invoice. This is the cheapest cash in the building." + extra,
            top["value"] * rate, 1.6, "Projects", "unbilled", top.get("client_id"),
        )
    # 5. Approvals blocking delivery.
    for row in projects.pending_approvals(projs, clients, today):
        add(
            f"Chase approval: {row['deliverable']} ({row['client']})",
            f"Waiting {row['waiting_days']} days — {row['chase']}.",
            500.0, 1.0 + min(row["waiting_days"], 10) / 10, "Projects", "approval", row.get("project_id"),
        )
    # 6. Deadline risk.
    for row in projects.portfolio(projs, clients, today):
        if row["risk"] in ("Critical", "At Risk"):
            project = find(projs, "id", row["id"]) or {}
            rate = finance.fx_rate(settings, project.get("currency"))
            add(
                f"Fix schedule: {row['project']} ({row['client']})",
                f"{row['risk']} — {row['progress']:.0f}% done, due {row['due']}.",
                float(row.get("budget", 0) or 0) * 0.25 * rate, 2.2 if row["risk"] == "Critical" else 1.3,
                "Projects", "deadline", row.get("id"),
            )
    # 7. Scope creep.
    for project in projs:
        rate = finance.fx_rate(settings, project.get("currency"))
        for flag in projects.scope_flags(project):
            if flag["severity"] == "High":
                add(
                    f"Raise change order: {flag['type']} on {project.get('name')}",
                    flag["action"],
                    float(flag.get("exposure", 0) or 0) * rate, 1.7, "Projects", "scope", project.get("id"),
                )
    # 8. Communication gaps.
    for gap in crm.communication_gaps(clients, settings, today):
        client = find(clients, "id", gap["client_id"]) or {}
        urgency = 1.9 if gap["severity"] == "Critical" else 0.9
        weight = float(client.get("deal_value", 0) or 0) if client.get("stage") in ("Proposal Sent", "Upsell") else 0.0
        add(
            f"Re-open {gap['client']} — {gap['days_silent']}d silent",
            gap["action"],
            weight, urgency, "Clients", "comm_gap", gap.get("client_id"),
        )
    # 9. Proposals in play.
    for client in clients:
        if client.get("stage") == "Proposal Sent":
            silent = days_since(client.get("last_contact"), today) or 0
            add(
                f"Nudge the proposal at {client_name(client)}",
                f"{native_amount(client.get('id'))} in play, {silent}d since last touch.",
                float(client.get("deal_value", 0) or 0), 1.5, "Clients", "proposal", client.get("id"),
            )
    # 10. Upsell windows.
    for row in crm.upsell_candidates(clients, projs, settings, today):
        add(
            f"Pitch phase two to {row['client']} — {money(row['suggested'], base)}",
            row["trigger"],
            float(row["suggested"]), 1.1, "Clients", "upsell", row.get("client_id"),
        )
    # 11. Revenue target.
    snap = pulse(native, today)
    if snap["target"] and snap["collected_mtd"] < snap["target"]:
        days_left = (add_months(month_start(today), 1) - today).days
        add(
            f"Close {money(snap['gap_to_target'], base)} this month to hit target",
            f"{pct(snap['target_pct'])} of {money(snap['target'], base)} collected, {days_left} days left in the month.",
            snap["gap_to_target"], 1.0, "Finance", "target",
        )
    # 12. Client next-actions you set and blew past.
    for row in crm.next_actions_due(clients, today):
        if row["state"] == "Overdue":
            add(
                f"{row['action']} — {row['client']}",
                f"Own next-action overdue since {row['due']}.",
                0.0, 1.6, "Clients", "next_action", row.get("client_id"),
            )

    moves.sort(key=lambda m: -m["score"])

    # One move per client across the "relationship" kinds — never tell the operator to
    # do two things to the same person on the same morning.
    relationship = {"comm_gap", "proposal", "next_action", "upsell"}
    seen_clients: set[str] = set()
    seen_text: set[str] = set()
    ranked: list[dict[str, Any]] = []
    for move in moves:
        key = move["move"].lower()[:60]
        if key in seen_text:
            continue
        if move["kind"] in relationship:
            ref = str(move.get("ref") or "")
            if ref and ref in seen_clients:
                continue
            if ref:
                seen_clients.add(ref)
        seen_text.add(key)
        ranked.append(move)
    return ranked[:limit] if limit else ranked


def _is_small(amount: float) -> bool:
    return abs(float(amount or 0)) < 1000


def next_move_markdown(book_: dict[str, Any] | None = None, today: date | None = None) -> str:
    """The ▶ NEXT MOVE block. Markdown, ready to paste anywhere."""
    moves = next_moves(book_, today, limit=2)
    if not moves:
        return "▶ **NEXT MOVE** — Book is clean. Build pipeline: book 3 discovery calls this week."
    lines = []
    for move in moves:
        value = f" · {money(move['value'], move.get('currency', 'USD'))} at stake" if move["value"] else ""
        lines.append(f"▶ **NEXT MOVE** — {move['move']}{value}  \n&nbsp;&nbsp;&nbsp;&nbsp;*{move['why']}*  \n&nbsp;&nbsp;&nbsp;&nbsp;→ {move['where']}")
    return "\n\n".join(lines)


# ---------------------------------------------------------------- dashboards

def client_dashboard(book_: dict[str, Any] | None = None, today: date | None = None) -> list[dict]:
    b = book_ or book()
    today = today or _today()
    rows = []
    for client in b["clients"]:
        h = crm.health(client, b["invoices"], b["projects"], b["settings"], today)
        value = crm.client_value(client, b["invoices"], today)
        silence = days_since(client.get("last_contact"), today)
        rows.append({
            "id": client["id"],
            "company": client_name(client),
            "contact": client.get("name", "—"),
            "stage": client.get("stage", "—"),
            "deal_value": client.get("deal_value", 0),
            "currency": client.get("currency", "USD"),
            "language": client.get("language", "EN"),
            "health": h["score"],
            "band": h["band"],
            "why": " · ".join(h["reasons"][:2]),
            "silent_days": silence if silence is not None else 9999,
            "outstanding": value["outstanding"],
            "lifetime": value["lifetime_billed"],
            "next_action": (client.get("next_action") or {}).get("note", "—"),
            "next_action_due": (client.get("next_action") or {}).get("due", "—"),
        })
    return sorted(rows, key=lambda r: r["health"])


def finance_dashboard(book_: dict[str, Any] | None = None, today: date | None = None, months: int = 6, horizon: int = 3) -> dict:
    b = book_ or book()
    today = today or _today()
    invoices, clients, settings = b["invoices"], b["clients"], b["settings"]
    aging = finance.aging_report(invoices, clients, today)
    currency = settings.get("currency", "USD")
    return {
        "revenue": finance.revenue_summary(invoices, today),
        "aging": aging,
        "aging_totals": {bucket: round(sum(r[bucket] for r in aging), 2)
                         for bucket in ("Current", "1-30", "31-60", "61-90", "90+")},
        "trend": finance.month_revenue(invoices, months, today),
        "forecast": finance.cash_flow_forecast(invoices, clients, settings, today, horizon),
        "queue": finance.collection_queue(invoices, clients, today),
        "currency": currency,
        "target": (settings.get("targets") or {}).get("monthly_revenue", 0),
    }


def _client_of(b: dict, cid: str | None) -> dict | None:
    return find(b["clients"], "id", cid) if cid else None


def client_rows(book_: dict[str, Any] | None = None, today: date | None = None) -> list[dict]:
    b = book_ or book()
    today = today or _today()
    rows = []
    for client in b["clients"]:
        h = crm.health(client, b["invoices"], b["projects"], b["settings"], today)
        value = crm.client_value(client, b["invoices"], today)
        rows.append({**client, "health": h["score"], "band": h["band"], "why": h["reasons"],
                     "outstanding": value["outstanding"], "lifetime_billed": value["lifetime_billed"],
                     "lifetime_collected": value["lifetime_collected"], "invoice_count": value["invoices"]})
    return rows
