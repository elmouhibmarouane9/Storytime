"""Schema constants, id generation and date arithmetic. No I/O lives here."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Iterable, Sequence

STAGES: list[str] = ["Lead", "Contacted", "Proposal Sent", "Active", "Completed", "Upsell"]

# Probability a deal in this stage turns into cash. Used by the cash-flow forecast.
STAGE_PROBABILITY: dict[str, float] = {
    "Lead": 0.10,
    "Contacted": 0.25,
    "Proposal Sent": 0.50,
    "Active": 1.00,
    "Completed": 1.00,
    "Upsell": 0.35,
}

TASK_STATUS: list[str] = ["Not Started", "In Progress", "Blocked", "In Review", "Done"]
DELIVERABLE_STATUS: list[str] = ["Planned", "In Progress", "In Review", "Awaiting Approval", "Approved", "Delivered"]
APPROVAL_STATE: list[str] = ["none", "pending", "approved", "changes requested"]
INVOICE_STATUS: list[str] = ["draft", "sent", "partial", "paid", "overdue", "void"]
CHANGE_ORDER_STATUS: list[str] = ["Draft", "Sent", "Approved", "Declined", "Billed"]

CURRENCY_SYMBOLS: dict[str, str] = {"USD": "$", "EUR": "€", "GBP": "£", "AED": "AED ", "MAD": "MAD ", "MXN": "MX$ "}

# Contact cadence per stage, in days. Blow through it and MIM flags a comm gap.
DEFAULT_CADENCE: dict[str, int] = {
    "Lead": 3,
    "Contacted": 5,
    "Proposal Sent": 4,
    "Active": 7,
    "Completed": 21,
    "Upsell": 14,
}

AGING_BUCKETS: list[str] = ["Current", "1-30", "31-60", "61-90", "90+"]


# ---------------------------------------------------------------- ids & dates

def next_id(prefix: str, existing: Sequence[str], width: int = 3, year: bool = False) -> str:
    """MEM-2026-007 style ids, collision-proof against the existing book."""
    stem = f"{prefix}-{date.today().year}-" if year else f"{prefix}-"
    top = 0
    for raw in existing:
        if not raw.startswith(stem):
            continue
        tail = raw[len(stem):]
        if tail.isdigit():
            top = max(top, int(tail))
    return f"{stem}{top + 1:0{width}d}"


def parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def as_str(value: date | None) -> str:
    return value.isoformat() if value else ""


def days_between(start: Any, end: Any) -> int | None:
    a, b = parse_date(start), parse_date(end)
    if a is None or b is None:
        return None
    return (b - a).days


def days_since(value: Any, ref: date) -> int | None:
    d = parse_date(value)
    return None if d is None else (ref - d).days


def month_key(value: Any) -> str:
    d = parse_date(value)
    return d.strftime("%Y-%m") if d else "—"


def month_label(key: str) -> str:
    try:
        return datetime.strptime(key, "%Y-%m").strftime("%b %Y")
    except ValueError:
        return key


def add_months(d: date, months: int) -> date:
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1
    day = min(d.day, [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return date(year, month, day)


def month_start(d: date) -> date:
    return d.replace(day=1)


def month_series(start: date, months: int) -> list[str]:
    return [month_key(add_months(month_start(start), i)) for i in range(months)]


# ---------------------------------------------------------------- money

def money(amount: float, currency: str = "USD", decimals: int = 0) -> str:
    sym = CURRENCY_SYMBOLS.get(currency, f"{currency} ")
    try:
        body = f"{abs(float(amount)):,.{decimals}f}"
    except (TypeError, ValueError):
        body = "0"
    sign = "-" if float(amount or 0) < 0 else ""
    return f"{sign}{sym}{body}"


def pct(value: float, decimals: int = 0) -> str:
    return f"{float(value or 0):.{decimals}f}%"


def index_by(rows: Iterable[dict], key: str = "id") -> dict[str, dict]:
    return {row[key]: row for row in rows if key in row}


def find(rows: Iterable[dict], key: str, value: Any) -> dict | None:
    for row in rows:
        if row.get(key) == value:
            return row
    return None
