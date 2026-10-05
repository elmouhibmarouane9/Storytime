"""Pillar 2 — Invoicing, collections, and cash-flow forecasting.

Every function is pure: give it the book plus a reference date, get answers back.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .models import (
    AGING_BUCKETS,
    STAGE_PROBABILITY,
    add_months,
    days_between,
    days_since,
    index_by,
    month_key,
    month_label,
    month_series,
    money,
    month_start,
    parse_date,
)

# ---------------------------------------------------------------- invoice math


def line_total(item: dict) -> float:
    return round(float(item.get("qty", 1) or 0) * float(item.get("rate", 0) or 0), 2)


def invoice_subtotal(invoice: dict) -> float:
    return round(sum(line_total(i) for i in invoice.get("items", [])), 2)


def invoice_discount(invoice: dict) -> float:
    return round(float(invoice.get("discount", 0) or 0), 2)


def invoice_tax(invoice: dict) -> float:
    base = max(invoice_subtotal(invoice) - invoice_discount(invoice), 0.0)
    return round(base * float(invoice.get("tax_rate", 0) or 0), 2)


def invoice_total(invoice: dict) -> float:
    return round(invoice_subtotal(invoice) - invoice_discount(invoice) + invoice_tax(invoice), 2)


def invoice_paid(invoice: dict) -> float:
    return round(sum(float(p.get("amount", 0) or 0) for p in invoice.get("payments", [])), 2)


def invoice_balance(invoice: dict) -> float:
    return round(invoice_total(invoice) - invoice_paid(invoice), 2)


def last_payment_date(invoice: dict) -> date | None:
    dates = [parse_date(p.get("date")) for p in invoice.get("payments", [])]
    clean = [d for d in dates if d]
    return max(clean) if clean else None


def effective_status(invoice: dict, today: date) -> str:
    """Truth over labels: payments and the clock decide the status, not the field."""
    if invoice.get("status") in ("draft", "void"):
        return invoice["status"]
    balance = invoice_balance(invoice)
    if balance <= 0.005 and invoice_total(invoice) > 0:
        return "paid"
    due = parse_date(invoice.get("due_date"))
    if due and due < today and balance > 0:
        return "overdue"
    if invoice_paid(invoice) > 0:
        return "partial"
    return "sent"


def days_overdue(invoice: dict, today: date) -> int:
    due = parse_date(invoice.get("due_date"))
    if not due or invoice_balance(invoice) <= 0:
        return 0
    return max((today - due).days, 0)


def days_to_due(invoice: dict, today: date) -> int:
    due = parse_date(invoice.get("due_date"))
    return 9999 if not due else (due - today).days


def aging_bucket(invoice: dict, today: date) -> str:
    overdue = days_overdue(invoice, today)
    if overdue <= 0:
        return "Current"
    if overdue <= 30:
        return "1-30"
    if overdue <= 60:
        return "31-60"
    if overdue <= 90:
        return "61-90"
    return "90+"


def open_invoices(invoices: list[dict], today: date) -> list[dict]:
    return [i for i in invoices if effective_status(i, today) in ("sent", "partial", "overdue")]


def reminder_tier(invoice: dict, today: date) -> int:
    """0 = pre-due nudge · 1 = 1-7 days · 2 = 8-21 days · 3 = 22+ days."""
    overdue = days_overdue(invoice, today)
    if overdue <= 0:
        return 0
    if overdue <= 7:
        return 1
    if overdue <= 21:
        return 2
    return 3


# ---------------------------------------------------------------- multi-currency

def base_currency(settings: dict) -> str:
    return (settings.get("agency") or {}).get("base_currency") or settings.get("currency", "USD")


def fx_rate(settings: dict, currency: str | None) -> float:
    rates = settings.get("fx_rates") or {}
    base = base_currency(settings)
    if not currency or currency == base:
        return 1.0
    return float(rates.get(currency, 1.0) or 1.0)


def to_base(amount: float, currency: str | None, settings: dict) -> float:
    return round(float(amount or 0) * fx_rate(settings, currency), 2)


def to_base_invoice(invoice: dict, settings: dict) -> dict:
    """A copy of the invoice with every amount expressed in the base currency.

    Reports sum this copy; the invoice itself always renders in its own currency.
    """
    import copy as _copy

    rate = fx_rate(settings, invoice.get("currency"))
    if rate == 1.0:
        return invoice
    out = _copy.deepcopy(invoice)
    for item in out.get("items", []):
        item["rate"] = round(float(item.get("rate", 0) or 0) * rate, 2)
    for payment in out.get("payments", []):
        payment["amount"] = round(float(payment.get("amount", 0) or 0) * rate, 2)
    out["discount"] = round(float(out.get("discount", 0) or 0) * rate, 2)
    out["currency"] = base_currency(settings)
    out["native_currency"] = invoice.get("currency")
    out["fx_rate"] = rate
    return out


def to_base_client(client: dict, settings: dict) -> dict:
    import copy as _copy

    rate = fx_rate(settings, client.get("currency"))
    if rate == 1.0:
        return client
    out = _copy.deepcopy(client)
    out["deal_value"] = round(float(out.get("deal_value", 0) or 0) * rate, 2)
    out["native_currency"] = client.get("currency")
    out["currency"] = base_currency(settings)
    return out


# ---------------------------------------------------------------- reports


def aging_report(invoices: list[dict], clients: list[dict], today: date) -> list[dict]:
    by_id = index_by(clients)
    rows: dict[str, dict] = {}
    for inv in invoices:
        if effective_status(inv, today) not in ("sent", "partial", "overdue"):
            continue
        cid = inv.get("client_id", "—")
        row = rows.setdefault(
            cid,
            {"client": by_id.get(cid, {}).get("company") or by_id.get(cid, {}).get("name", "Unassigned"),
             "currency": inv.get("currency", "USD"),
             **{b: 0.0 for b in AGING_BUCKETS}, "balance": 0.0, "worst": 0, "invoices": 0},
        )
        bal = invoice_balance(inv)
        bucket = aging_bucket(inv, today)
        row[bucket] = round(row[bucket] + bal, 2)
        row["balance"] = round(row["balance"] + bal, 2)
        row["worst"] = max(row["worst"], days_overdue(inv, today))
        row["invoices"] += 1
    return sorted(rows.values(), key=lambda r: (-r["worst"], -r["balance"]))


def collection_queue(invoices: list[dict], clients: list[dict], today: date) -> list[dict]:
    """What to chase, in the order MIM would chase it."""
    by_id = index_by(clients)
    rows = []
    for inv in open_invoices(invoices, today):
        balance = invoice_balance(inv)
        overdue = days_overdue(inv, today)
        client = by_id.get(inv.get("client_id"), {})
        urgency = 1.0 + min(overdue, 90) / 30 + (0.5 if balance >= 2000 else 0)
        rows.append({
            "invoice": inv.get("id", "—"),
            "client": client.get("company") or client.get("name", "—"),
            "client_id": inv.get("client_id"),
            "due": inv.get("due_date", "—"),
            "days_overdue": overdue,
            "balance": balance,
            "currency": inv.get("currency", "USD"),
            "tier": reminder_tier(inv, today),
            "status": effective_status(inv, today),
            "priority": round(balance * urgency, 2),
        })
    return sorted(rows, key=lambda r: -r["priority"])


def avg_days_to_pay(invoices: list[dict]) -> float | None:
    gaps: list[int] = []
    for inv in invoices:
        if effective_status(inv, parse_date(inv.get("due_date")) or date.today()) != "paid":
            continue
        paid_on = last_payment_date(inv)
        issued = parse_date(inv.get("issue_date"))
        if paid_on and issued:
            gaps.append((paid_on - issued).days)
    return round(sum(gaps) / len(gaps), 1) if gaps else None


def revenue_summary(invoices: list[dict], today: date) -> dict:
    mtd = month_start(today)
    ytd_start = date(today.year, 1, 1)
    billed_mtd = billed_ytd = collected_mtd = collected_ytd = 0.0
    draft_value = 0.0
    for inv in invoices:
        status = effective_status(inv, today)
        if status == "void":
            continue
        issued = parse_date(inv.get("issue_date"))
        total = invoice_total(inv)
        if status == "draft":
            draft_value += total
            continue
        if issued and issued >= mtd:
            billed_mtd += total
        if issued and issued >= ytd_start:
            billed_ytd += total
        for payment in inv.get("payments", []):
            pd = parse_date(payment.get("date"))
            if not pd:
                continue
            if pd >= mtd:
                collected_mtd += float(payment.get("amount", 0) or 0)
            if pd >= ytd_start:
                collected_ytd += float(payment.get("amount", 0) or 0)
    outstanding = sum(invoice_balance(i) for i in open_invoices(invoices, today))
    overdue_list = [i for i in open_invoices(invoices, today) if days_overdue(i, today) > 0]
    return {
        "billed_mtd": round(billed_mtd, 2),
        "billed_ytd": round(billed_ytd, 2),
        "collected_mtd": round(collected_mtd, 2),
        "collected_ytd": round(collected_ytd, 2),
        "outstanding": round(outstanding, 2),
        "overdue": round(sum(invoice_balance(i) for i in overdue_list), 2),
        "overdue_count": len(overdue_list),
        "draft_value": round(draft_value, 2),
        "avg_days_to_pay": avg_days_to_pay(invoices),
        "open_count": len(open_invoices(invoices, today)),
    }


def month_revenue(invoices: list[dict], months: int, today: date) -> list[dict]:
    """Billed vs collected per month, newest last — the trend table."""
    keys = month_series(add_months(month_start(today), -(months - 1)), months)
    table = {k: {"month": month_label(k), "key": k, "billed": 0.0, "collected": 0.0} for k in keys}
    for inv in invoices:
        if effective_status(inv, today) == "void":
            continue
        issued = parse_date(inv.get("issue_date"))
        if issued and month_key(issued) in table:
            table[month_key(issued)]["billed"] += invoice_total(inv)
        for payment in inv.get("payments", []):
            pd = parse_date(payment.get("date"))
            if pd and month_key(pd) in table:
                table[month_key(pd)]["collected"] += float(payment.get("amount", 0) or 0)
    return [table[k] for k in keys]


# ---------------------------------------------------------------- forecasting


def cash_flow_forecast(
    invoices: list[dict],
    clients: list[dict],
    settings: dict,
    today: date,
    months: int = 3,
) -> list[dict]:
    """Expected cash by month, weighted and explainable.

    Overdue money: assumed to land at 90% within the current month.
    Sent invoices: booked in their due month (or this month if already due), 95%.
    Retainers (Active clients tagged 'retainer'): deal_value / 12 each month.
    Open pipeline: deal_value x stage probability, booked at the expected close month.
    """
    keys = month_series(month_start(today), months)
    table = {k: {"month": month_label(k), "key": k, "recurring": 0.0, "invoices": 0.0, "pipeline": 0.0} for k in keys}
    notes: list[str] = []

    for inv in open_invoices(invoices, today):
        balance = invoice_balance(inv)
        due = parse_date(inv.get("due_date")) or today
        overdue = due < today
        key = keys[0] if overdue else month_key(due)
        if key not in table:
            continue
        weight = 0.90 if overdue else 0.95
        table[key]["invoices"] += balance * weight

    for client in clients:
        if client.get("stage") != "Active" or "retainer" not in (client.get("tags") or []):
            continue
        monthly = round(float(client.get("deal_value", 0) or 0) / 12, 2)
        for key in keys:
            table[key]["recurring"] += monthly

    for client in clients:
        if client.get("stage") not in ("Lead", "Contacted", "Proposal Sent", "Upsell"):
            continue
        prob = STAGE_PROBABILITY.get(client["stage"], 0.0)
        close = parse_date(client.get("expected_close")) or add_months(today, 1)
        key = month_key(close)
        if key in table:
            table[key]["pipeline"] += float(client.get("deal_value", 0) or 0) * prob

    rows = []
    for key in keys:
        row = table[key]
        row["expected"] = round(row["recurring"] + row["invoices"] + row["pipeline"], 2)
        row["committed"] = round(row["recurring"] + row["invoices"], 2)
        rows.append(row)

    target = float((settings.get("targets") or {}).get("monthly_revenue", 0) or 0)
    for row in rows:
        row["target"] = target
        row["gap"] = round(target - row["expected"], 2)
    if target:
        short = [r for r in rows if r["expected"] < target]
        notes.append(
            f"Target {money(target)}/mo — {len(short)} of {months} forecast months land short."
            if short else f"Target {money(target)}/mo is covered across all {months} months."
        )
    return rows


def forecast_notes(rows: list[dict], settings: dict) -> list[str]:
    target = float((settings.get("targets") or {}).get("monthly_revenue", 0) or 0)
    if not target or not rows:
        return []
    shortfalls = [r for r in rows if r["gap"] > 0]
    notes = []
    if shortfalls:
        first = shortfalls[0]
        notes.append(
            f"{first['month']} is {money(first['gap'])} under target — pipeline coverage is the lever, not discounting."
        )
    else:
        notes.append("Forecast clears target in every month. Protect the pipeline, don't touch the price list.")
    return notes


def pipeline_covered_ratio(rows: list[dict]) -> float | None:
    """How much of the target the next 90 days already covers, %."""
    if not rows or not rows[0].get("target"):
        return None
    expected = sum(r["expected"] for r in rows)
    target = rows[0]["target"] * len(rows)
    return round(expected / target * 100, 0) if target else None


def reminder_due(invoice: dict, today: date, last_reminder: date | None = None) -> bool:
    tier = reminder_tier(invoice, today)
    if tier == 0:
        return days_to_due(invoice, today) <= 2
    if last_reminder is None:
        return True
    spacing = {1: 4, 2: 7, 3: 10}[tier]
    return (today - last_reminder).days >= spacing


def urgency_score(invoice: dict, today: date, client: dict | None = None) -> float:
    """0-100 collection urgency. Money x lateness, adjusted by how the client pays."""
    balance = invoice_balance(invoice)
    overdue = days_overdue(invoice, today)
    if balance <= 0:
        return 0.0
    base = min(balance / 50, 45) + min(overdue / 2, 35)
    if client and (client.get("payment_behaviour") or "").lower().startswith("slow"):
        base += 10
    return round(min(base, 100), 1)


def days_out(value: Any, today: date) -> str:
    delta = days_since(value, today)
    if delta is None:
        return "—"
    if delta == 0:
        return "today"
    return f"{delta}d ago" if delta > 0 else f"in {abs(delta)}d"


def due_label(value: Any, today: date) -> str:
    d = parse_date(value)
    if not d:
        return "—"
    delta = (d - today).days
    if delta == 0:
        return "due today"
    if delta < 0:
        return f"{abs(delta)}d late"
    return f"in {delta}d"


def next_invoice_number(settings: dict) -> str:
    inv = settings.get("invoice") or {}
    prefix = inv.get("prefix", "MEM")
    year = today().year
    seq = int(inv.get("next_number", 1) or 1)
    return f"{prefix}-{year}-{seq:03d}"


def bump_invoice_number(settings: dict) -> None:
    inv = settings.setdefault("invoice", {})
    inv["next_number"] = int(inv.get("next_number", 1) or 1) + 1
