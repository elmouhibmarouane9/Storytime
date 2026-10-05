"""Pillar 3 — Projects. Progress, deadline risk, scope creep and billable time."""

from __future__ import annotations

from datetime import date
from typing import Any

from .models import TASK_STATUS, days_since, parse_date

STATUS_WEIGHT = {"Not Started": 0.0, "Blocked": 0.0, "In Progress": 0.5, "In Review": 0.8, "Done": 1.0}


# ---------------------------------------------------------------- progress

def task_progress(task: dict) -> float:
    if task.get("progress") is not None:
        return max(0.0, min(100.0, float(task.get("progress") or 0)))
    return round(STATUS_WEIGHT.get(task.get("status", "Not Started"), 0.0) * 100, 1)


def task_weight(task: dict) -> float:
    for field in ("weight", "estimated_hours"):
        value = task.get(field)
        if value:
            return float(value)
    return 1.0


def project_progress(project: dict) -> float:
    tasks = project.get("tasks", [])
    if not tasks:
        return float(project.get("progress", 0) or 0)
    total = sum(task_weight(t) for t in tasks)
    if total <= 0:
        return 0.0
    return round(sum(task_progress(t) * task_weight(t) for t in tasks) / total, 1)


def project_hours(project: dict) -> dict:
    tasks = project.get("tasks", [])
    est = round(sum(float(t.get("estimated_hours", 0) or 0) for t in tasks), 1)
    logged = round(sum(float(t.get("logged_hours", 0) or 0) for t in tasks), 1)
    entries = project.get("time_entries", [])
    if entries:
        logged = round(sum(float(e.get("hours", 0) or 0) for e in entries), 1)
        est = round(sum(float(e.get("estimated_hours", 0) or 0) for e in entries), 1) or est
    rate = float(project.get("hourly_rate", 0) or 0)
    return {
        "estimated": est,
        "logged": logged,
        "remaining": round(max(est - logged, 0), 1),
        "burn_pct": round(logged / est * 100, 0) if est else 0.0,
        "logged_value": round(logged * rate, 2),
    }


def deadline_risk(project: dict, today: date) -> dict:
    start, due = parse_date(project.get("start")), parse_date(project.get("due"))
    progress = project_progress(project)
    if project.get("status") in ("Completed", "Delivered"):
        return {"status": "Delivered", "days_left": None, "expected": 100.0, "progress": progress, "message": "Shipped."}
    if not due:
        return {"status": "No Deadline", "days_left": None, "expected": None, "progress": progress, "message": "Date not set."}
    days_left = (due - today).days
    if start and due > start:
        elapsed = (today - start).days / (due - start).days
        expected = round(max(0.0, min(elapsed, 1.0)) * 100, 1)
    else:
        expected = None
    gap = None if expected is None else round(progress - expected, 1)
    if progress >= 100:
        status = "Delivered"
    elif days_left < 0:
        status = "Critical"
    elif gap is not None and gap <= -25:
        status = "Critical"
    elif gap is not None and gap <= -10:
        status = "At Risk"
    elif days_left <= 7 and progress < 85:
        status = "At Risk"
    else:
        status = "On Track"
    message = {
        "Delivered": "Shipped.",
        "Critical": f"{abs(days_left)}d {'overdue' if days_left < 0 else 'left'} at {progress:.0f}% — {gap if gap is not None else 0:+.0f}pts vs schedule.",
        "At Risk": f"{days_left}d left at {progress:.0f}% — needs a push this week.",
        "On Track": f"{days_left}d left, tracking {gap if gap is not None else 0:+.0f}pts vs schedule.",
        "No Deadline": "No date on file.",
    }[status]
    return {"status": status, "days_left": days_left, "expected": expected, "progress": progress, "gap": gap, "message": message}


def deliverable_rows(project: dict, today: date) -> list[dict]:
    rows = []
    for d in project.get("deliverables", []):
        approval = d.get("approval") or {}
        state = approval.get("state", "none")
        rows.append({
            "deliverable": d.get("name", "—"),
            "status": d.get("status", "Planned"),
            "due": d.get("due", "—"),
            "days_left": days_since(d.get("due"), today) * -1 if d.get("due") else None,
            "approval": state,
            "waiting": days_since(approval.get("requested"), today) if state == "pending" else None,
        })
    return rows


def pending_approvals(projects: list[dict], clients: list[dict], today: date) -> list[dict]:
    by_id = {c.get("id"): c for c in clients}
    rows = []
    for project in projects:
        for d in project.get("deliverables", []):
            approval = d.get("approval") or {}
            if approval.get("state") != "pending":
                continue
            waiting = days_since(approval.get("requested"), today) or 0
            client = by_id.get(project.get("client_id"), {})
            rows.append({
                "project": project.get("name", "—"),
                "project_id": project.get("id"),
                "client": client.get("company") or client.get("name", "—"),
                "client_id": project.get("client_id"),
                "deliverable": d.get("name", "—"),
                "requested": approval.get("requested", "—"),
                "waiting_days": waiting,
                "chase": "Second chase" if waiting >= 5 else "First chase" if waiting >= 2 else "Give it 24h",
                "language": client.get("language", "EN"),
            })
    return sorted(rows, key=lambda r: -r["waiting_days"])


# ---------------------------------------------------------------- scope & billing

def uninvoiced_time(project: dict) -> dict:
    """Billable hours still on the table, split from work that was never in scope."""
    rate = float(project.get("hourly_rate", 0) or 0)
    hours = value = out_hours = out_value = 0.0
    for entry in project.get("time_entries", []):
        if entry.get("invoiced") or not entry.get("billable", True):
            continue
        h = float(entry.get("hours", 0) or 0)
        entry_rate = float(entry.get("rate", rate) or rate)
        if entry.get("in_scope", True):
            hours += h
            value += h * entry_rate
        else:
            out_hours += h
            out_value += h * entry_rate
    return {
        "hours": round(hours, 1),
        "value": round(value, 2),
        "out_of_scope_hours": round(out_hours, 1),
        "out_of_scope_value": round(out_value, 2),
        "rate": rate,
    }


def scope_flags(project: dict) -> list[dict]:
    """Scope creep in four flavours: out-of-scope work, extra revisions,
    hours past estimate, and approved change orders not yet billed."""
    flags: list[dict] = []
    rate = float(project.get("hourly_rate", 0) or 0)

    out_of_scope = [
        e for e in project.get("time_entries", [])
        if e.get("in_scope") is False and not e.get("invoiced")
    ]
    if out_of_scope:
        hours = round(sum(float(e.get("hours", 0) or 0) for e in out_of_scope), 1)
        flags.append({
            "type": "Out-of-scope work",
            "detail": f"{hours}h delivered outside the signed scope",
            "exposure": round(hours * rate, 2),
            "action": "Raise a change order before the next delivery.",
            "severity": "High",
        })

    included = int(project.get("included_revisions", 0) or 0)
    extra_revisions = []
    for d in project.get("deliverables", []):
        used = int(d.get("revisions", 0) or 0)
        if included and used > included:
            extra_revisions.append((d.get("name", "—"), used - included))
    if extra_revisions:
        total_extra = sum(n for _, n in extra_revisions)
        billable = round(total_extra * rate * 1.0, 2)
        names = ", ".join(f"{n} (+{k})" for n, k in extra_revisions[:3])
        flags.append({
            "type": "Revision overage",
            "detail": f"{names} · {total_extra} extra revision pass(es) vs {included} included",
            "exposure": billable,
            "action": "Bill the extra passes at the revision rate or trade them for a testimonial.",
            "severity": "Medium",
        })

    hours = project_hours(project)
    if hours["estimated"] and hours["logged"] > hours["estimated"] * 1.1:
        over = round(hours["logged"] - hours["estimated"], 1)
        flags.append({
            "type": "Hours over estimate",
            "detail": f"{hours['logged']}h logged vs {hours['estimated']}h estimated (+{over}h)",
            "exposure": round(over * rate, 2),
            "action": "Fix the estimate for phase 2 and recover the overage or cap the scope.",
            "severity": "High" if hours["logged"] > hours["estimated"] * 1.25 else "Medium",
        })

    for co in project.get("change_orders", []):
        if co.get("status") == "Approved":
            flags.append({
                "type": "Approved, unbilled change order",
                "detail": f"{co.get('title', 'Change order')} approved {co.get('date', '')}",
                "exposure": round(float(co.get("amount", 0) or 0), 2),
                "action": "Put it on the next invoice this week.",
                "severity": "High",
            })
    return flags


def scope_exposure(project: dict) -> float:
    return round(sum(f["exposure"] for f in scope_flags(project)), 2)


def portfolio(projects: list[dict], clients: list[dict], today: date) -> list[dict]:
    by_id = {c.get("id"): c for c in clients}
    rows = []
    for project in projects:
        client = by_id.get(project.get("client_id"), {})
        risk = deadline_risk(project, today)
        hours = project_hours(project)
        rows.append({
            "id": project.get("id", "—"),
            "project": project.get("name", "—"),
            "client": client.get("company") or client.get("name", "—"),
            "client_id": project.get("client_id"),
            "status": project.get("status", "—"),
            "progress": project_progress(project),
            "due": project.get("due", "—"),
            "days_left": risk.get("days_left"),
            "risk": risk["status"],
            "open_tasks": sum(1 for t in project.get("tasks", []) if task_progress(t) < 100),
            "hours": f"{hours['logged']}/{hours['estimated']}h",
            "budget": project.get("budget", 0),
            "scope_exposure": scope_exposure(project),
            "unbilled": uninvoiced_time(project)["value"],
        })
    order = {"Critical": 0, "At Risk": 1, "On Track": 2, "Delivered": 3, "No Deadline": 4}
    return sorted(rows, key=lambda r: (order.get(r["risk"], 5), r["days_left"] if r["days_left"] is not None else 999))


def portfolio_summary(projects: list[dict], today: date) -> dict:
    active = [p for p in projects if p.get("status") == "Active"]
    risks = [deadline_risk(p, today)["status"] for p in active]
    return {
        "active": len(active),
        "at_risk": sum(1 for r in risks if r in ("At Risk", "Critical")),
        "critical": sum(1 for r in risks if r == "Critical"),
        "avg_progress": round(sum(project_progress(p) for p in active) / len(active), 1) if active else 0.0,
        "scope_exposure": round(sum(scope_exposure(p) for p in projects), 2),
        "unbilled": round(sum(uninvoiced_time(p)["value"] for p in projects), 2),
        "unbilled_hours": round(sum(uninvoiced_time(p)["hours"] for p in projects), 1),
    }


def unbilled_by_client(projects: list[dict], clients: list[dict]) -> list[dict]:
    by_id = {c.get("id"): c for c in clients}
    buckets: dict[str, dict] = {}
    for project in projects:
        info = uninvoiced_time(project)
        if info["value"] <= 0 and info["hours"] <= 0:
            continue
        cid = project.get("client_id", "—")
        client = by_id.get(cid, {})
        row = buckets.setdefault(cid, {
            "client": client.get("company") or client.get("name", "Unassigned"),
            "client_id": cid,
            "currency": client.get("currency", "USD"),
            "hours": 0.0,
            "value": 0.0,
            "out_of_scope_hours": 0.0,
            "out_of_scope_value": 0.0,
            "projects": [],
        })
        row["hours"] = round(row["hours"] + info["hours"], 1)
        row["value"] = round(row["value"] + info["value"], 2)
        row["out_of_scope_hours"] = round(row["out_of_scope_hours"] + info["out_of_scope_hours"], 1)
        row["out_of_scope_value"] = round(row["out_of_scope_value"] + info["out_of_scope_value"], 2)
        row["projects"].append(project.get("name", "—"))
    return sorted(buckets.values(), key=lambda r: -r["value"])


def bill_time_for_client(projects: list[dict], client_id: str) -> tuple[list[dict], list[str]]:
    """Turn uninvoiced billable time into invoice line items. Returns (items, entry_ids)."""
    items: list[dict] = []
    ids: list[str] = []
    for project in projects:
        if project.get("client_id") != client_id:
            continue
        rate = float(project.get("hourly_rate", 0) or 0)
        by_task: dict[str, dict] = {}
        for entry in project.get("time_entries", []):
            if entry.get("invoiced") or not entry.get("billable", True) or entry.get("in_scope") is False:
                continue
            hours = float(entry.get("hours", 0) or 0)
            if hours <= 0:
                continue
            key = entry.get("task_id") or "Ad hoc"
            bucket = by_task.setdefault(key, {"hours": 0.0, "rate": float(entry.get("rate", rate) or rate), "note": entry.get("note", "")})
            bucket["hours"] += hours
            ids.append(entry.get("id"))
        task_names = {t.get("id"): t.get("name", t.get("id")) for t in project.get("tasks", [])}
        for key, bucket in by_task.items():
            label = task_names.get(key, "Project time") if key != "Ad hoc" else f"{project.get('name', 'Project')} — ad hoc"
            items.append({
                "desc": f"{project.get('name', 'Project')} · {label}" + (f" — {bucket['note']}" if bucket["note"] else ""),
                "qty": round(bucket["hours"], 2),
                "rate": round(bucket["rate"], 2),
                "unit": "hr",
            })
    return items, [i for i in ids if i]


def mark_time_invoiced(projects: list[dict], entry_ids: list[str]) -> int:
    touched = 0
    wanted = set(entry_ids)
    for project in projects:
        for entry in project.get("time_entries", []):
            if entry.get("id") in wanted and not entry.get("invoiced"):
                entry["invoiced"] = True
                touched += 1
    return touched
