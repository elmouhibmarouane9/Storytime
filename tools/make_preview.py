"""Generate the static preview: docs/preview/index.html.

Every number rendered here is produced by the same engine functions the live
console calls — this is a mirror of the app's data and design, not a mockup.

    python3 tools/make_preview.py

Served as a shareable walkthrough (no login, no data): docs/preview/index.html.
"""

from __future__ import annotations

import html
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mim import comms, console, crm, finance, projects, store  # noqa: E402
from mim.models import money, pct  # noqa: E402

OUT = ROOT / "docs" / "preview" / "index.html"
LIVE = "https://8501-i02vfpkg7v59vnvvb6pa2.e2b.app"
BASE_REF = "1d48e82"   # the commit this branch started from (the blank template)

TODAY: date = store.today()
BOOK = console.book()
PULSE = console.pulse(BOOK, TODAY)
MOVES = console.next_moves(BOOK, TODAY, limit=6)
BASE = console.base_book(BOOK)
CUR = PULSE["base_currency"]

FILE_NOTES = {
    "streamlit_app.py": "Router: gate, sidebar with live snapshot, page dispatch, next-move footer",
    "app.py": "Entry shim so both `streamlit run app.py` and `streamlit_app.py` work",
    "README.md": "The four pillars, the engine, permanent-link paths, test map",
    "requirements.txt": "streamlit + pandas",
    "requirements-dev.txt": "pytest for the engine and headless page tests",
    ".streamlit/config.toml": "0.0.0.0 bind, proxy-safe CORS/XSRF, dark theme, websocket tuning",
    ".gitignore": "Keeps .env, secrets and the client book out of Git",
    "mim/console.py": "Pulse snapshot + next_moves(): every signal ranked by money × urgency",
    "mim/finance.py": "Invoice maths, effective status, aging buckets, collection queue, forecast, FX",
    "mim/crm.py": "Pipeline probabilities, 0-100 health with reasons, cadence gaps, upsell triggers",
    "mim/projects.py": "Weighted progress, schedule risk, 4 scope-creep flags, time → invoice",
    "mim/comms.py": "15 brand-voice templates EN/ES, reminder ladder, thread summariser",
    "mim/render.py": "Invoice → Markdown and print-ready HTML",
    "mim/service.py": "Every write path in one place; access gate; storage health",
    "mim/store.py": "Atomic local JSON + optional private-Git data repo with retry",
    "mim/models.py": "Schema constants, id generation, date and money formatting",
    "mim/ui.py": "Theme, KPI cards, next-move blocks, tables, draft surface",
    "mim/i18n.py": "Console chrome in EN/ES/FR/AR with an Arabic-capable layout",
    "mim/seed.py": "Labelled sample book: 5 clients, 8 invoices, 4 projects, 12 messages",
    "mim/views/dashboard.py": "Ops pulse: cash priority, delivery risk, trend, aging, watchlist",
    "mim/views/clients_view.py": "Pipeline board, full client file, comms log, stage moves",
    "mim/views/invoices_view.py": "Build, send, chase, close — ledger, collections, invoice view",
    "mim/views/finance_view.py": "Revenue, aging, cash forecast, unbilled time → draft invoice",
    "mim/views/projects_view.py": "Portfolio, task control, approvals, time, scope & change orders",
    "mim/views/comms_view.py": "Compose, thread summariser, silence radar, history",
    "mim/views/settings_view.py": "Agency, targets, cadence, FX, invoice defaults, book & sync",
    "tests/test_engine.py": "Pillar maths: totals, aging, FX, forecast, health, scope, templates",
    "tests/test_app.py": "Headless render of all 7 pages + the access gate, via Streamlit AppTest",
    "tests/test_store_github.py": "Git data-repo backend against a fake GitHub API, offline",
    "tests/conftest.py": "Throwaway data directory per test run",
    "Dockerfile": "Non-root image, healthcheck, book volume at /app/data",
    "docker-compose.yml": "App + optional Caddy HTTPS, named volume for the book",
    "render.yaml": "Render Blueprint: disk mount + declared secrets",
    "fly.toml": "Fly.io app with a volume, auto-stop when idle",
    "deploy/install.sh": "One command on a fresh VPS: Docker, clone, code, HTTPS",
    "deploy/Caddyfile": "Automatic TLS, websocket-safe reverse proxy",
    "deploy/huggingface.md": "Free permanent Space, paired with the Git backend",
    ".env.example": "Access code, domain, timezone",
    ".dockerignore": "Keeps client data and tests out of the image",
}


# ---------------------------------------------------------------- html helpers

def esc(value) -> str:
    return html.escape(str(value), quote=True)


def pill(text: str, tone: str = "muted") -> str:
    return f'<span class="pill {tone}">{esc(text)}</span>'


def card(label: str, value: str, note: str = "", accent: bool = False, tone: str = "") -> str:
    cls = "card accent" if accent else "card"
    note_html = f'<div class="note {tone}">{esc(note)}</div>' if note else ""
    return f'<div class="{cls}"><div class="label">{esc(label)}</div><div class="value">{esc(value)}</div>{note_html}</div>'


def cards(items: list[dict]) -> str:
    return '<div class="grid">' + "".join(card(**item) for item in items) + "</div>"


def table(headers: list[str], rows: list[list], aligns: list[str] | None = None) -> str:
    if not rows:
        return '<div class="empty">Nothing on the board.</div>'
    aligns = aligns or ["left"] * len(headers)
    head = "".join(f'<th class="{aligns[i]}">{esc(h)}</th>' for i, h in enumerate(headers))
    body = ""
    for row in rows:
        cells = ""
        for i, cell in enumerate(row):
            raw = str(cell)
            rendered = raw if raw.startswith("<span") else esc(raw)
            cells += f'<td class="{aligns[i]}">{rendered}</td>'
        body += f"<tr>{cells}</tr>"
    return f'<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def move_block(move: dict, index: int) -> str:
    label = "▶ NEXT MOVE" if index == 0 else f"▶ NEXT MOVE ({index + 1})"
    value = f' · <b>{esc(money(move["value"], move.get("currency", CUR)))}</b> at stake' if move["value"] else ""
    return (f'<div class="move"><div class="mv-head">{label} — {esc(move["move"])}{value}</div>'
            f'<div class="mv-meta">{esc(move["why"])}</div>'
            f'<div class="mv-where">→ {esc(move["where"])}</div></div>')


def section(sid: str, kicker: str, title: str, body: str) -> str:
    return (f'<section id="{sid}"><div class="kicker">{esc(kicker)}</div>'
            f'<h2>{esc(title)}</h2>{body}</section>')


def draft_block(subject: str, body: str, note: str = "") -> str:
    return (f'<div class="draft"><div class="draft-head">Subject · <code>{esc(subject)}</code></div>'
            f'<pre>{esc(body)}</pre>'
            f'<div class="draft-note">{esc(note) or "Editable in the console. Downloadable as .md / .txt. Never auto-sent."}</div></div>')


# ---------------------------------------------------------------- change manifest

def git_changes() -> tuple[list[dict], dict]:
    try:
        raw = subprocess.run(["git", "diff", "--numstat", BASE_REF, "HEAD"],
                             cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return [], {}
    rows, totals = [], {"added": 0, "removed": 0, "files": 0}
    for line in raw.strip().splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, removed, path = parts
        add = int(added) if added.isdigit() else 0
        rem = int(removed) if removed.isdigit() else 0
        totals["added"] += add
        totals["removed"] += rem
        totals["files"] += 1
        rows.append({"path": path, "added": add, "removed": rem,
                     "status": "new" if rem == 0 and add > 0 else "edited",
                     "note": FILE_NOTES.get(path, "—")})
    rows.sort(key=lambda r: (r["status"] != "new", r["path"]))
    return rows, totals


def tests_summary() -> dict:
    try:
        out = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q", "--no-header"],
                             cwd=ROOT, capture_output=True, text=True).stdout
        line = [ln for ln in out.strip().splitlines() if "passed" in ln or "failed" in ln]
        return {"line": line[-1] if line else "no result"}
    except Exception as exc:  # pragma: no cover
        return {"line": f"unavailable: {exc}"}


# ---------------------------------------------------------------- page bodies

def dashboard_body() -> str:
    rev = finance.revenue_summary(BASE["invoices"], TODAY)
    queue = finance.collection_queue(BASE["invoices"], BASE["clients"], TODAY)[:5]
    portfolio = projects.portfolio(BASE["projects"], BASE["clients"], TODAY)
    trend = finance.month_revenue(BASE["invoices"], 6, TODAY)
    aging = finance.aging_report(BASE["invoices"], BASE["clients"], TODAY)
    totals = {b: round(sum(r[b] for r in aging), 2) for b in ("Current", "1-30", "31-60", "61-90", "90+")}
    peak = max([t["billed"] for t in trend] + [t["collected"] for t in trend] + [1])

    kpis = cards([
        {"label": "Collected this month", "value": money(rev["collected_mtd"], CUR),
         "note": f'{pct(PULSE["target_pct"])} of {money(PULSE["target"], CUR)} target · '
                 f'{money(PULSE["gap_to_target"], CUR)} to close', "accent": True, "tone": "tone-warn"},
        {"label": "Outstanding", "value": money(rev["outstanding"], CUR),
         "note": f'{rev["overdue_count"]} overdue · {money(rev["overdue"], CUR)} late', "tone": "tone-bad"},
        {"label": "Weighted pipeline", "value": money(PULSE["pipeline"], CUR),
         "note": f'Raw {money(PULSE["pipeline_raw"], CUR)} · win rate {pct(PULSE["win_rate"])}', "tone": "tone-info"},
        {"label": "Forecast this month", "value": money(PULSE["expected_month"], CUR),
         "note": "Retainers + invoices + weighted pipeline", "tone": "tone-info"},
    ])
    kpis2 = cards([
        {"label": "Projects at risk", "value": f'{PULSE["projects_at_risk"]}',
         "note": f'{PULSE["projects_critical"]} critical · {PULSE["projects_active"]} active', "tone": "tone-bad"},
        {"label": "Scope exposure", "value": money(PULSE["scope_exposure"], CUR),
         "note": "Unbilled scope + approved change orders", "tone": "tone-warn"},
        {"label": "Unbilled time", "value": money(PULSE["unbilled"], CUR),
         "note": f'{PULSE["unbilled_hours"]}h delivered, not invoiced', "tone": "tone-warn"},
        {"label": "Comms gaps", "value": f'{PULSE["comm_gaps"]}',
         "note": f'{PULSE["pending_approvals"]} approvals pending', "tone": "tone-bad"},
    ])
    queue_table = table(
        ["Invoice", "Client", "Balance", "Late", "Tone"],
        [[q["invoice"], q["client"], money(q["balance"], q["currency"], 2),
          f'{q["days_overdue"]}d' if q["days_overdue"] else "—",
          {0: "Pre-due", 1: "Soft", 2: "Firm", 3: "Final"}[q["tier"]]] for q in queue],
        ["left", "left", "right", "right", "left"])
    risk_table = table(
        ["Project", "Client", "Risk", "Done", "Due", "Open tasks"],
        [[p["project"], p["client"], pill(p["risk"], "bad" if p["risk"] == "Critical" else "warn"),
          f'{p["progress"]:.0f}%', p["due"], p["open_tasks"]] for p in portfolio],
        ["left", "left", "left", "right", "right", "right"])
    bars = ""
    for t in trend:
        billed = int(t["billed"] / peak * 100)
        collected = int(t["collected"] / peak * 100)
        bars += (f'<div class="bar-col"><div class="bars">'
                 f'<div class="bar grey" style="height:{max(billed, 1)}%" title="Billed {esc(money(t["billed"], CUR))}"></div>'
                 f'<div class="bar gold" style="height:{max(collected, 1)}%" title="Collected {esc(money(t["collected"], CUR))}"></div>'
                 f'</div><div class="bar-lab">{esc(t["month"][:3])}</div></div>')
    aging_table = table(["Bucket", "Value"], [[k, money(v, CUR)] for k, v in totals.items()],
                        ["left", "right"])

    watch = crm.at_risk_accounts(BASE["clients"], BASE["invoices"], BASE["projects"], BASE["settings"], TODAY)
    watch_table = table(["Client", "Stage", "Health", "Why"],
                        [[w["client"], w["stage"], str(w["health"]), w["why"]] for w in watch[:4]],
                        ["left", "left", "right", "left"])

    return (kpis + kpis2 +
            '<div class="cols"><div class="col">'
            '<h3>Cash priority</h3><p class="cap">Chase in this order — weighted by balance and lateness.</p>'
            f'{queue_table}</div>'
            '<div class="col"><h3>Delivery priority</h3><p class="cap">Projects in the danger zone, worst first.</p>'
            f'{risk_table}</div></div>'
            '<div class="cols"><div class="col"><h3>Revenue trend</h3>'
            f'<div class="chart">{bars}</div>'
            '<p class="cap">Billed (grey) vs collected (gold) — the gap is your accounts receivable.</p></div>'
            f'<div class="col"><h3>Aging</h3>{aging_table}'
            '<h3 style="margin-top:1.2rem">Relationship watchlist</h3>'
            f'{watch_table}</div></div>')


def clients_body() -> str:
    stages = crm.pipeline_summary(BASE["clients"])
    board = '<div class="board">'
    for s in stages:
        in_stage = [c for c in BASE["clients"] if c.get("stage") == s["stage"]]
        cards_html = "".join(
            f'<div class="mini"><div class="mini-name">{esc(c.get("company"))}</div>'
            f'<div class="mini-meta">{esc(money(c.get("deal_value", 0), CUR))} · {esc(c.get("language", "EN"))}</div></div>'
            for c in in_stage)
        board += (f'<div class="col-stage"><div class="stage-head">{esc(s["stage"])}'
                  f'<div class="stage-value">{esc(money(s["value"], CUR))}</div>'
                  f'<div class="stage-note">{s["clients"]} client(s) · {int(s["probability"] * 100)}% weighted</div></div>'
                  f'{cards_html}</div>')
    board += "</div>"
    kpis = cards([
        {"label": "Clients", "value": str(PULSE["clients"]), "note": f'{PULSE["active_clients"]} active'},
        {"label": f"Pipeline ({CUR})", "value": money(PULSE["pipeline"], CUR),
         "note": f'Raw {money(PULSE["pipeline_raw"], CUR)} · native: '
                 f'{console.currency_breakdown(console.native_pipeline_breakdown(BOOK["clients"]))}', "accent": True},
        {"label": "Avg deal", "value": money(PULSE["avg_deal"], CUR), "note": f'Win rate {pct(PULSE["win_rate"])}'},
        {"label": "Proposals out", "value": "1", "note": "on the table now", "tone": "tone-info"},
    ])
    rows = console.client_dashboard(BOOK, TODAY)
    health = table(["Client", "Contact", "Stage", "Health", "Owed", "Lifetime", "Last touch"],
                   [[r["company"], r["contact"], r["stage"],
                     pill(str(r["health"]), "good" if r["health"] >= 80 else "warn" if r["health"] >= 60 else "bad"),
                     money(r["outstanding"], r["currency"]),
                     money(r["lifetime"], r["currency"]),
                     f'{r["silent_days"]}d' if r["silent_days"] != 9999 else "never"] for r in rows],
                   ["left", "left", "left", "right", "right", "right", "right"])
    detail = crm.health(next(c for c in BASE["clients"] if c["id"] == "C-001"),
                        BASE["invoices"], BASE["projects"], BASE["settings"], TODAY)
    return (kpis + '<h3>Pipeline board</h3>' + board +
            '<h3>Client list — worst health first</h3>' + health +
            '<h3>Why Nordwind scores what it scores</h3>'
            f'<div class="move"><div class="mv-head">Health {detail["score"]}/100 · {esc(detail["band"])}</div>'
            f'<div class="mv-meta">{" · ".join(esc(r) for r in detail["reasons"])}</div>'
            '<div class="mv-where">→ No black box: every point has a named reason</div></div>')


def invoices_body() -> str:
    rev = finance.revenue_summary(BASE["invoices"], TODAY)
    queue = finance.collection_queue(BASE["invoices"], BASE["clients"], TODAY)
    kpis = cards([
        {"label": f"Outstanding ({CUR})", "value": money(rev["outstanding"], CUR),
         "note": f'{rev["open_count"]} open · native: {console.currency_breakdown(PULSE["outstanding_by_currency"])}'},
        {"label": "Overdue", "value": money(rev["overdue"], CUR),
         "note": f'{rev["overdue_count"]} invoices late', "tone": "tone-bad"},
        {"label": "Collected this month", "value": money(rev["collected_mtd"], CUR),
         "note": f'Billed {money(rev["billed_mtd"], CUR)}', "accent": True},
        {"label": "Drafts on the shelf", "value": money(rev["draft_value"], CUR),
         "note": f'Avg days to pay {rev["avg_days_to_pay"] or "—"}', "tone": "tone-warn"},
    ])
    ledger = table(
        ["Invoice", "Client", "Issued", "Due", "Total", "Paid", "Balance", "Status"],
        [[i["id"], next((c["company"] for c in BOOK["clients"] if c["id"] == i.get("client_id")), "—"),
          i.get("issue_date"), i.get("due_date"),
          money(finance.invoice_total(i), i.get("currency", "USD"), 2),
          money(finance.invoice_paid(i), i.get("currency", "USD"), 2),
          money(finance.invoice_balance(i), i.get("currency", "USD"), 2),
          pill(finance.effective_status(i, TODAY), {"paid": "good", "overdue": "bad", "partial": "warn",
                                                    "sent": "info", "draft": "muted"}.get(
              finance.effective_status(i, TODAY), "muted"))]
         for i in BOOK["invoices"]],
        ["left", "left", "left", "left", "right", "right", "right", "left"])
    queue_table = table(
        ["Invoice", "Client", "Balance", "Late", "Tone", "Priority"],
        [[q["invoice"], q["client"], money(q["balance"], q["currency"], 2),
          f'{q["days_overdue"]}d' if q["days_overdue"] else "—",
          {0: "Pre-due", 1: "Soft", 2: "Firm", 3: "Final"}[q["tier"]],
          f'{q["priority"]:,.0f}'] for q in queue],
        ["left", "left", "right", "right", "left", "right"])
    invoice = next(i for i in BOOK["invoices"] if i["id"] == "MEM-2026-003")
    client = next(c for c in BOOK["clients"] if c["id"] == invoice["client_id"])
    en_subject, en_body = comms.reminder_for(invoice, client, TODAY, "EN")
    es_subject, es_body = comms.reminder_for(invoice, client, TODAY, "ES")
    tiers = table(
        ["Tier", "Trigger", "Tone", "Escalation"],
        [[f'Tier {r["tier"]}', r["trigger"], r["tone"], r["escalation"]]
         for r in BOOK["settings"]["reminder_policy"]],
        ["left", "left", "left", "left"])
    return (kpis + '<h3>Ledger — balances in the invoice currency</h3>' + ledger +
            '<h3>Collection queue — work top down</h3>' + queue_table +
            '<h3>Reminder ladder</h3>' + tiers +
            f'<h3>Drafted now: MEM-2026-003 · {esc(money(finance.invoice_balance(invoice), "USD", 2))} '
            f'· {finance.days_overdue(invoice, TODAY)} days late · final-notice tier</h3>'
            '<div class="cols"><div class="col">' + draft_block(en_subject, en_body) + '</div>'
            '<div class="col">' + draft_block(es_subject, es_body) + '</div></div>')


def finance_body() -> str:
    rev = finance.revenue_summary(BASE["invoices"], TODAY)
    aging = finance.aging_report(BASE["invoices"], BASE["clients"], TODAY)
    totals = {b: round(sum(r[b] for r in aging), 2) for b in ("Current", "1-30", "31-60", "61-90", "90+")}
    forecast = finance.cash_flow_forecast(BASE["invoices"], BASE["clients"], BASE["settings"], TODAY, 3)
    trend = finance.month_revenue(BASE["invoices"], 6, TODAY)
    kpis = cards([
        {"label": "Collected MTD", "value": money(rev["collected_mtd"], CUR),
         "note": f'{pct(PULSE["target_pct"])} of {money(PULSE["target"], CUR)} target', "accent": True},
        {"label": "Billed YTD", "value": money(rev["billed_ytd"], CUR),
         "note": f'Collected YTD {money(rev["collected_ytd"], CUR)}'},
        {"label": "Outstanding", "value": money(rev["outstanding"], CUR),
         "note": f'Overdue {money(rev["overdue"], CUR)} on {rev["overdue_count"]} invoice(s)', "tone": "tone-bad"},
        {"label": "Avg days to pay", "value": str(rev["avg_days_to_pay"] or "—"),
         "note": "Across paid invoices", "tone": "tone-warn"},
    ] + [{"label": k, "value": money(v, CUR)} for k, v in totals.items()])
    forecast_table = table(
        ["Month", "Recurring", "Invoices", "Pipeline (weighted)", "Expected", "Committed", "Target", "Gap"],
        [[f["month"], money(f["recurring"], CUR), money(f["invoices"], CUR), money(f["pipeline"], CUR),
          money(f["expected"], CUR), money(f["committed"], CUR), money(f["target"], CUR),
          (f'−{money(abs(f["gap"]), CUR)}' if f["gap"] > 0 else money(abs(f["gap"]), CUR))] for f in forecast],
        ["left", "right", "right", "right", "right", "right", "right", "right"])
    trend_table = table(["Month", "Billed", "Collected", "Gap"],
                        [[t["month"], money(t["billed"], CUR), money(t["collected"], CUR),
                          money(t["billed"] - t["collected"], CUR)] for t in trend],
                        ["left", "right", "right", "right"])
    unbilled = [r for r in projects.unbilled_by_client(BOOK["projects"], BOOK["clients"])
                if r["value"] > 0 or r["out_of_scope_value"] > 0]
    unbilled_table = table(
        ["Client", "Hours", "Billable value", "Out-of-scope hours", "Out-of-scope value"],
        [[r["client"], f'{r["hours"]:g}', money(r["value"], r["currency"]),
          f'{r["out_of_scope_hours"]:g}', money(r["out_of_scope_value"], r["currency"])] for r in unbilled],
        ["left", "right", "right", "right", "right"])
    coverage = finance.pipeline_covered_ratio(forecast)
    notes = finance.forecast_notes(forecast, BASE["settings"])
    return (kpis + '<h3>Cash forecast — how the number is built</h3>' + forecast_table +
            f'<p class="cap">Model: retainers monthly · open invoices at 95% in their due month · overdue at 90% this month '
            f'· pipeline weighted by stage probability. Coverage of target: <b>{pct(coverage)}</b>. {esc(" ".join(notes))}</p>'
            '<h3>Monthly trend</h3>' + trend_table +
            '<h3>Unbilled time — the cheapest cash in the building</h3>' + unbilled_table +
            '<p class="cap">Out-of-scope hours need a change order, not an invoice. Billable hours go straight to a draft invoice.</p>')


def projects_body() -> str:
    port = projects.portfolio_summary(BASE["projects"], TODAY)
    kpis = cards([
        {"label": "Active", "value": str(port["active"]), "note": f'{port["avg_progress"]}% average progress'},
        {"label": "At risk", "value": str(port["at_risk"]), "note": f'{port["critical"]} critical', "tone": "tone-bad"},
        {"label": "Scope exposure", "value": money(port["scope_exposure"], CUR),
         "note": "Unbilled scope + approved change orders", "tone": "tone-warn"},
        {"label": "Unbilled time", "value": money(port["unbilled"], CUR),
         "note": f'{port["unbilled_hours"]}h billable, not invoiced', "tone": "tone-warn"},
    ])
    rows = projects.portfolio(BASE["projects"], BASE["clients"], TODAY)
    portfolio = table(
        ["ID", "Project", "Client", "Status", "Done", "Due", "Days", "Risk", "Open", "Unbilled", "Exposure"],
        [[r["id"], r["project"], r["client"], r["status"], f'{r["progress"]:.0f}%', r["due"],
          (f'{r["days_left"]}d' if r["days_left"] is not None else "—"),
          pill(r["risk"], "bad" if r["risk"] == "Critical" else "warn" if r["risk"] == "At Risk" else "good"),
          r["open_tasks"], money(r["unbilled"], CUR), money(r["scope_exposure"], CUR)] for r in rows],
        ["left", "left", "left", "left", "right", "left", "right", "left", "right", "right", "right"])
    haddad = next(p for p in BASE["projects"] if p["id"] == "P-002")
    flags = projects.scope_flags(haddad)
    flag_table = table(["Flag", "Detail", "Exposure", "Severity"],
                       [[f["type"], f["detail"], money(f["exposure"], CUR), pill(f["severity"], "bad" if f["severity"] == "High" else "warn")]
                        for f in flags], ["left", "left", "right", "left"])
    client = next(c for c in BOOK["clients"] if c["id"] == "C-003")
    subject, body = comms.change_order_from_flag(haddad, flags[0], client, BOOK["settings"], "EN")
    approvals = projects.pending_approvals(BASE["projects"], BASE["clients"], TODAY)
    approval_table = table(["Client", "Project", "Deliverable", "Requested", "Waiting", "Play"],
                           [[a["client"], a["project"], a["deliverable"], a["requested"],
                             f'{a["waiting_days"]}d', a["chase"]] for a in approvals],
                           ["left", "left", "left", "left", "right", "left"])
    risk = projects.deadline_risk(haddad, TODAY)
    return (kpis + '<h3>Portfolio — worst risk first</h3>' + portfolio +
            '<h3>Approvals waiting on the client</h3>' + approval_table +
            f'<h3>Scope creep detected on Haddad — {esc(money(projects.scope_exposure(haddad), "AED"))} of exposure</h3>'
            + flag_table +
            f'<p class="cap">Schedule: {esc(risk["message"])}</p>'
            '<h3>Change order written from the flag</h3>' + draft_block(subject, body))


def comms_body() -> str:
    gaps = crm.communication_gaps(BASE["clients"], BASE["settings"], TODAY)
    approvals = projects.pending_approvals(BASE["projects"], BASE["clients"], TODAY)
    kpis = cards([
        {"label": "Threads gone cold", "value": str(len(gaps)),
         "note": f'{sum(1 for g in gaps if g["severity"] == "Critical")} critical', "tone": "tone-bad"},
        {"label": "Approvals waiting", "value": str(len(approvals)),
         "note": f'{max([a["waiting_days"] for a in approvals], default=0)}d longest', "tone": "tone-warn"},
        {"label": "Logged messages", "value": str(len(BOOK["messages"])),
         "note": f'{sum(1 for m in BOOK["messages"] if m["direction"] == "out")} outbound'},
        {"label": "Clients on cadence", "value": f'{len(BOOK["clients"]) - len(gaps)}/{len(BOOK["clients"])}',
         "note": "Cadence enforced by stage", "accent": True},
    ])
    gap_table = table(["Client", "Stage", "Last contact", "Days silent", "Cadence", "Severity", "Play"],
                      [[g["client"], g["stage"], g["last_contact"], str(g["days_silent"]), f'{g["threshold"]}d',
                        pill(g["severity"], "bad" if g["severity"] == "Critical" else "warn"), g["action"]]
                       for g in gaps], ["left", "left", "left", "right", "right", "left", "left"])
    casa = next(c for c in BOOK["clients"] if c["id"] == "C-002")
    es_subject, es_body = comms.gap_draft(casa, TODAY, "ES")
    thread = """Daniel: Can you confirm the Q4 budget by Monday?
We will send the revised scope tomorrow.
Daniel: Approved — let's go.
Invoice MEM-2026-003 is still unpaid, $4,800 due 2026-08-03.
Lucía: ¿Podemos comprimir el calendario a dos semanas?"""
    summary = comms.summarise_thread(thread)
    thread_html = (f'<div class="draft"><div class="draft-head">Paste anything — emails, WhatsApp, call notes</div>'
                   f'<pre>{esc(thread)}</pre></div>'
                   f'<div class="cols"><div class="col"><h4>Decisions</h4><ul class="tight">'
                   + "".join(f"<li>{esc(d)}</li>" for d in summary["decisions"]) +
                   '</ul><h4>Open questions</h4><ul class="tight">'
                   + "".join(f"<li>{esc(q)}</li>" for q in summary["questions"]) +
                   '</ul></div><div class="col"><h4>Commitments</h4><ul class="tight">'
                   + "".join(f"<li>{esc(c)}</li>" for c in summary["commitments"]) +
                   '</ul><h4>Dates & money detected</h4><ul class="tight">'
                   + "".join(f"<li>{esc(d)}</li>" for d in (summary["dates"] + summary["money"])) +
                   '</ul></div></div>'
                   f'<div class="move"><div class="mv-head">▶ NEXT MOVE — {esc(summary["next_step"])}</div>'
                   f'<div class="mv-meta">{summary["stats"]["lines"]} lines read · {summary["stats"]["questions"]} questions '
                   f'· {summary["stats"]["decisions"]} decisions</div></div>')
    return (kpis + '<h3>Silence radar</h3>' + gap_table +
            '<h3>Drafted re-open — Casa Ferrer, in Spanish because that is her language on file</h3>'
            + draft_block(es_subject, es_body) +
            '<h3>Thread summariser</h3>' + thread_html)


def settings_body() -> str:
    agency = BOOK["settings"].get("agency") or {}
    rows = [
        {"Setting": "Agency details", "Value": f'{agency.get("name")} · {agency.get("owner")} · {agency.get("email")}'},
        {"Setting": "Base currency", "Value": f'{agency.get("base_currency", "USD")} — all reporting converts here'},
        {"Setting": "FX rates", "Value": " · ".join(f'{k} {v}' for k, v in (BOOK["settings"].get("fx_rates") or {}).items())},
        {"Setting": "Monthly target", "Value": money(PULSE["target"], CUR)},
        {"Setting": "Cadence", "Value": " · ".join(f'{k} {v}d' for k, v in (BOOK["settings"].get("cadence_days") or {}).items())},
        {"Setting": "Invoice defaults", "Value": f'prefix {BOOK["settings"]["invoice"]["prefix"]} · '
                                                 f'{BOOK["settings"]["invoice"]["default_terms"]} · tax '
                                                 f'{BOOK["settings"]["invoice"]["tax_rate"] * 100:.1f}%'},
        {"Setting": "Access gate", "Value": "MIM_ACCESS_CODE — the console refuses to render without it"},
        {"Setting": "Book location", "Value": "local JSON by default · optional private Git repo (GITHUB_TOKEN + MIM_DATA_REPO)"},
    ]
    return ('<h3>Every operating rule is editable</h3>'
            + table(["Setting", "Value"], [[r["Setting"], r["Value"]] for r in rows], ["left", "left"])
            + cards([
                {"label": "Export", "value": "JSON", "note": "Whole book, one file"},
                {"label": "Restore", "value": "Upload", "note": "Merge or replace — your choice"},
                {"label": "Sync", "value": "Git", "note": "Every save a commit, every commit a restore point"},
                {"label": "Reset", "value": "Clean book", "note": "Irreversible, confirmed by checkbox"},
            ]))


# ---------------------------------------------------------------- assembly

def build() -> str:
    rows, totals = git_changes()
    tests = tests_summary()
    changes_table = table(
        ["File", "New lines", "Status", "What it does"],
        [[f'<code>{esc(r["path"])}</code>', f'+{r["added"]}', pill("new" if r["status"] == "new" else "edited",
                                                                  "good" if r["status"] == "new" else "info"),
          esc(r["note"])] for r in rows],
        ["left", "right", "left", "left"])
    nav = "".join(f'<a href="#{sid}">{esc(label)}</a>' for sid, label in [
        ("changes", "Changes"), ("dashboard", "Dashboard"), ("clients", "Clients"), ("invoices", "Invoices"),
        ("finance", "Finance"), ("projects", "Projects"), ("comms", "Comms"), ("settings", "Settings"),
        ("live", "Go live"), ("proof", "Proof"), ("gaps", "Honest gaps")])

    body = (
        header_html(tests, totals, rows)
        + nav_html()
        + section("changes", "01 · diff", "What was added",
                  '<p class="cap">' + str(totals.get("files", 0)) + " files · +" + str(totals.get("added", 0))
                  + " / −" + str(totals.get("removed", 0)) + " lines against the template commit <code>"
                  + esc(BASE_REF) + "</code>. Nothing was deleted from your repo — the template files were "
                  "replaced with the console.</p>" + changes_table)
        + section("dashboard", "02 · page", "Dashboard — the whole business on one screen",
                  '<p class="cap">Today\'s two moves, cash priority, delivery risk, revenue trend, aging and the '
                  'relationship watchlist.</p>'
                  + "".join(move_block(m, i) for i, m in enumerate(MOVES[:2])) + dashboard_body())
        + section("clients", "03 · page", "Clients — pipeline, profiles, health",
                  '<p class="cap">Six stages, weighted by real conversion probability. Health is 0-100 and every '
                  'point has a named reason.</p>' + clients_body())
        + section("invoices", "04 · page", "Invoices — build, send, chase, close",
                  '<p class="cap">Effective status ignores labels and trusts the money. Reminders escalate in tiers, '
                  "in the client's language.</p>" + invoices_body())
        + section("finance", "05 · page", "Finance — aging, trend, forecast, unbilled cash",
                  '<p class="cap">Every total in ' + esc(CUR) + " equivalent; every invoice still shown in its own "
                  "currency.</p>" + finance_body())
        + section("projects", "06 · page", "Projects — deadlines, approvals, scope creep",
                  '<p class="cap">Progress weighted by task size, measured against a schedule baseline, with four '
                  "kinds of scope-creep detection.</p>" + projects_body())
        + section("comms", "07 · page", "Comms — drafts, silence radar, thread summariser",
                  '<p class="cap">15 hand-written templates in EN/ES. Nothing sends itself: MIM drafts, you '
                  "sign.</p>" + comms_body())
        + section("settings", "08 · page", "Settings — the operating rules",
                  '<p class="cap">Agency details, targets, cadence per stage, FX rates, invoice defaults, the access '
                  "gate and where the book lives.</p>" + settings_body())
        + section("live", "09 · deploy", "How to make it permanent", live_body())
        + section("proof", "10 · proof", "How you know it works", proof_body(tests))
        + section("gaps", "11 · honesty", "What this is not", GAPS_HTML)
        + footer_html()
    )
    return DOCTYPE + "<html lang=\"en\"><head><meta charset=\"utf-8\">" \
        + '<meta name="viewport" content="width=device-width, initial-scale=1">' \
        + "<title>MIM · MEM Digital — build preview</title>" + CSS + "</head><body>" + body + "</body></html>"



# ---------------------------------------------------------------- page chrome

DOCTYPE = "<!doctype html>"

CSS = """<style>
  :root { --gold:#E9B949; --ink:#0A0D11; --panel:#111823; --line:#1E2733; --muted:#8A97A6; }
  * { box-sizing:border-box; }
  body { margin:0; background:radial-gradient(1100px 520px at 12% -12%, #14202b 0%, rgba(10,13,17,0) 62%),
         radial-gradient(900px 480px at 96% 4%, #1a160c 0%, rgba(10,13,17,0) 58%), #0A0D11;
         color:#F3F6F9; font:15px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif; }
  a { color:var(--gold); text-decoration:none; }
  a:hover { text-decoration:underline; }
  code, pre { font-family:'SF Mono',ui-monospace,Menlo,Consolas,monospace; }
  .wrap { max-width:1180px; margin:0 auto; padding:0 22px 90px; }
  header { padding:52px 0 26px; border-bottom:1px solid var(--line); }
  .word { font-size:1.8rem; font-weight:800; letter-spacing:.3em; color:var(--gold); }
  .sub { color:var(--muted); font-size:.78rem; letter-spacing:.16em; text-transform:uppercase; margin-top:4px; }
  h1 { font-size:2rem; margin:26px 0 8px; letter-spacing:-.02em; }
  h2 { font-size:1.35rem; margin:0 0 14px; letter-spacing:-.01em; }
  h3 { font-size:1.02rem; margin:26px 0 8px; color:#EAEFF5; }
  h4 { font-size:.85rem; margin:14px 0 6px; color:var(--gold); text-transform:uppercase; letter-spacing:.08em; }
  .kicker { color:var(--gold); font-size:.7rem; letter-spacing:.2em; text-transform:uppercase; margin-bottom:6px; }
  section { padding:34px 0; border-bottom:1px solid #141B24; }
  nav { position:sticky; top:0; z-index:9; background:rgba(10,13,17,.92); backdrop-filter:blur(8px);
        border-bottom:1px solid var(--line); padding:10px 0; margin-bottom:6px; font-size:.82rem; }
  nav a { margin-right:18px; color:#B9C3CE; } nav a:hover { color:var(--gold); }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:12px; margin:14px 0; }
  .card { background:linear-gradient(180deg,#111823,#0D131A); border:1px solid var(--line); border-radius:14px; padding:14px 16px; }
  .card.accent { border-color:#3A2F14; background:linear-gradient(180deg,#1B1710,#12100B); }
  .label { font-size:.66rem; letter-spacing:.14em; text-transform:uppercase; color:var(--muted); }
  .value { font-size:1.42rem; font-weight:700; margin-top:5px; }
  .card.accent .value { color:var(--gold); }
  .note { font-size:.75rem; color:var(--muted); margin-top:6px; }
  .tone-bad { color:#E4572E; } .tone-warn { color:#E9B949; } .tone-info { color:#5AA9E6; } .tone-good { color:#2FBF71; }
  .move { background:linear-gradient(180deg,#1A1508,#100E09); border:1px solid #4A3A12; border-left:4px solid var(--gold);
          border-radius:12px; padding:13px 16px; margin:10px 0; }
  .mv-head { font-weight:700; color:#FAF3E0; }
  .mv-meta { color:#B9A46B; font-size:.85rem; margin-top:4px; }
  .mv-where { color:var(--muted); font-size:.7rem; letter-spacing:.12em; text-transform:uppercase; margin-top:6px; }
  table { width:100%; border-collapse:collapse; font-size:.84rem; margin:8px 0 4px; }
  th { text-align:left; color:var(--muted); font-size:.66rem; letter-spacing:.1em; text-transform:uppercase;
       border-bottom:1px solid #26303C; padding:8px; font-weight:600; }
  td { border-bottom:1px solid #161E27; padding:8px; vertical-align:top; }
  .right { text-align:right; font-variant-numeric:tabular-nums; }
  .pill { display:inline-block; padding:2px 8px; border-radius:999px; font-size:.64rem; font-weight:700;
          letter-spacing:.05em; text-transform:uppercase; border:1px solid; }
  .pill.good { color:#2FBF71; border-color:#2FBF7155; background:#2FBF7111; }
  .pill.warn { color:#E9B949; border-color:#E9B94955; background:#E9B94911; }
  .pill.bad  { color:#E4572E; border-color:#E4572E55; background:#E4572E11; }
  .pill.info { color:#5AA9E6; border-color:#5AA9E655; background:#5AA9E611; }
  .pill.muted{ color:#8A97A6; border-color:#8A97A655; background:#8A97A611; }
  .cols { display:grid; grid-template-columns:1fr 1fr; gap:22px; margin-top:8px; }
  .cap { color:var(--muted); font-size:.78rem; margin:2px 0 14px; }
  .empty { color:var(--muted); font-size:.85rem; }
  .board { display:grid; grid-template-columns:repeat(6,1fr); gap:10px; margin:12px 0; }
  .col-stage { background:#0E141B; border:1px solid var(--line); border-radius:12px; padding:10px; }
  .stage-head { font-size:.72rem; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }
  .stage-value { color:#F3F6F9; font-weight:700; font-size:1rem; margin-top:4px; }
  .stage-note { color:#5E6A77; font-size:.66rem; margin-bottom:8px; }
  .mini { background:#131A23; border:1px solid #232D3A; border-radius:9px; padding:8px 10px; margin-bottom:6px; }
  .mini-name { font-size:.82rem; font-weight:600; }
  .mini-meta { color:var(--muted); font-size:.7rem; }
  .chart { display:flex; align-items:flex-end; gap:18px; height:190px; padding:12px 6px 0; border-bottom:1px solid var(--line); }
  .bar-col { flex:1; display:flex; flex-direction:column; align-items:center; height:100%; }
  .bars { display:flex; align-items:flex-end; gap:3px; height:100%; width:100%; justify-content:center; }
  .bar { width:16px; border-radius:4px 4px 0 0; }
  .bar.grey { background:#3C4A5A; } .bar.gold { background:var(--gold); }
  .bar-lab { color:var(--muted); font-size:.7rem; padding-top:6px; }
  .draft { background:#0B1017; border:1px solid var(--line); border-radius:12px; padding:12px 14px; }
  .draft-head { font-size:.8rem; color:var(--muted); margin-bottom:8px; }
  .draft pre { white-space:pre-wrap; font-size:.82rem; color:#DDE5EC; margin:0; }
  .draft-note { color:#5E6A77; font-size:.72rem; margin-top:8px; border-top:1px solid #161E27; padding-top:8px; }
  ul.tight { margin:6px 0 0; padding-left:18px; } ul.tight li { margin-bottom:4px; font-size:.84rem; }
  .callout { border:1px solid #3A2F14; background:#150F06; border-radius:12px; padding:14px 16px; margin:14px 0; }
  .callout.bad { border-color:#4A1E12; background:#160A06; }
  .callout.ok { border-color:#12321F; background:#08170E; }
  .btn { display:inline-block; margin-top:8px; padding:9px 16px; border-radius:10px; border:1px solid #3A2F14;
         background:#1B1710; color:var(--gold); font-weight:600; }
  .big { font-size:1.9rem; font-weight:800; letter-spacing:-.02em; }
  .lead { font-size:1.06rem; color:#CDD6DF; max-width:74ch; }
  footer { padding:34px 0; color:var(--muted); font-size:.8rem; }
  @media (max-width:900px) { .cols, .board { grid-template-columns:1fr; } }
</style>"""

NAV_ITEMS = [("changes", "Changes"), ("dashboard", "Dashboard"), ("clients", "Clients"), ("invoices", "Invoices"),
             ("finance", "Finance"), ("projects", "Projects"), ("comms", "Comms"), ("settings", "Settings"),
             ("live", "Go live"), ("proof", "Proof"), ("gaps", "Honest gaps")]

GAPS_HTML = """<table><thead><tr><th>Limitation</th><th>What that means for you</th></tr></thead><tbody>
<tr><td>Nothing sends email</td><td>MIM drafts; you copy and send from your own inbox. Deliverability and the relationship stay yours. Sending is a deliberate next step, not an oversight.</td></tr>
<tr><td>Sample data, not your clients</td><td>Five fictional accounts so every dashboard is live. Wipe them in Settings → Start a clean book, then load yours.</td></tr>
<tr><td>The demo link is session-bound</td><td>It works now, for you and for anyone you share it with — but it dies with this session. Permanent needs a deploy.</td></tr>
<tr><td>Single operator, no roles</td><td>One access code, one book. That is the shape of a one-person agency; multi-user would need real auth.</td></tr>
<tr><td>FX rates are manual</td><td>Update them in Settings when the market moves; nothing pretends to fetch live rates.</td></tr>
</tbody></table>"""


def nav_html() -> str:
    links = "".join('<a href="#' + sid + '">' + esc(label) + "</a>" for sid, label in NAV_ITEMS)
    return '<nav><div class="wrap" style="padding:0">' + links + "</div></nav>"


HEADER = """<header><div class="wrap">
  <div class="word">MIM</div>
  <div class="sub">MEM Digital · build preview · __DATE__</div>
  <h1>Everything that changed, and where to see it running</h1>
  <p class="lead">Your repo started as a blank Streamlit template. It is now an operating system for a
  one-person agency: CRM, invoicing and finance, project tracking and client communications — with a
  next-move engine that ranks every action by money at stake x urgency.</p>
  <div class="callout ok"><b>See it live right now</b><br>
    <a class="btn" href="__LIVE__">__LIVE__</a>
    <div class="note">Anyone with the link can open it — no account, no install. The book behind it is
    clearly labelled sample data (5 fictional clients), which is why this demo link carries no access code.
    It is tied to this session; a permanent address takes the 10-minute deploy in the "Go live" section.</div>
  </div>
</div></header>"""


def header_html(tests: dict, totals: dict, rows: list[dict]) -> str:
    return HEADER.replace("__DATE__", esc(TODAY.isoformat())).replace("__LIVE__", LIVE)


LIVE_BODY = """<p class="cap">The preview link dies with this session. Three ways to make it stick, all configured in the repo.</p>
<div class="cols">
  <div class="col"><h4>Free · Streamlit Community Cloud</h4>
    <p class="cap">Merge the open PR, then deploy with one click. Add <code>MIM_ACCESS_CODE</code> in secrets.
    Pair it with the private Git data repo so the book survives restarts.</p>
    <a href="__DEPLOY__">Open the deploy page →</a></div>
  <div class="col"><h4>Free · Hugging Face Space</h4>
    <p class="cap">Permanent https URL, private Space, same Git data backend. Walkthrough in
    <code>deploy/huggingface.md</code>.</p></div>
</div>
<div class="cols">
  <div class="col"><h4>~$7/mo · Render, Railway or Fly.io</h4>
    <p class="cap"><code>render.yaml</code> and <code>fly.toml</code> are in the repo: Docker build, a volume
    mounted at <code>/app/data</code>, secrets declared. Mount the volume — that one setting decides whether
    your data persists.</p></div>
  <div class="col"><h4>~€4/mo · your own server and domain</h4>
    <p class="cap">One command installs Docker, clones, generates the access code and serves HTTPS through Caddy:</p>
    <pre style="white-space:pre-wrap;font-size:.76rem;color:#DDE5EC">__INSTALL__</pre></div>
</div>"""

DEPLOY_URL = ("https://share.streamlit.io/deploy?repository=elmouhibmarouane9/Storytime"
              "&amp;branch=arena/01a10c7b-storytime&amp;mainModule=streamlit_app.py")
INSTALL_CMD = ("curl -fsSL https://raw.githubusercontent.com/elmouhibmarouane9/Storytime/"
               "arena/01a10c7b-storytime/deploy/install.sh | bash")


def live_body() -> str:
    return LIVE_BODY.replace("__DEPLOY__", DEPLOY_URL).replace("__INSTALL__", INSTALL_CMD)


def proof_body(tests: dict) -> str:
    moves = len(console.next_moves(BOOK, TODAY, limit=0))
    cards_html = (
        '<div class="grid">'
        '<div class="card accent"><div class="label">Test suite</div><div class="value">'
        + esc(tests["line"].split(" in ")[0])
        + '</div><div class="note">' + esc(tests["line"])
        + " · engine maths, all 7 pages rendered headlessly, the access gate, and the Git backend against a "
          "fake GitHub</div></div>"
        '<div class="card"><div class="label">Engine</div><div class="value">Pure Python</div>'
        '<div class="note">Streamlit only renders it — the maths is testable without a browser</div></div>'
        '<div class="card"><div class="label">Moves ranked</div><div class="value">' + str(moves) + "</div>"
        '<div class="note">Signals scored today, deduped to one relationship move per client</div></div>'
        '<div class="card"><div class="label">Data</div><div class="value">Plain JSON</div>'
        '<div class="note">Atomic writes, exportable, or committed to your own private repo</div></div>'
        "</div>"
    )
    callout = (
        '<div class="callout"><b>Run it yourself in one line</b>'
        '<pre style="white-space:pre-wrap;font-size:.8rem;color:#DDE5EC;margin:8px 0 0">pip install -r '
        "requirements.txt &amp;&amp; streamlit run streamlit_app.py</pre>"
        '<div class="note">First run seeds the labelled sample book. Tests: <code>pip install -r '
        "requirements-dev.txt &amp;&amp; python -m pytest tests/ -q</code></div></div>"
    )
    return cards_html + callout


def footer_html() -> str:
    return ('<footer><div class="wrap" style="padding:0">MIM · MEM Digital ops console · preview generated '
            + esc(TODAY.isoformat())
            + " · every figure on this page was produced by the same engine the live app calls.</div></footer>")


if __name__ == "__main__":
    store.bootstrap()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1024:.0f} KB)")
