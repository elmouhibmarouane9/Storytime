"""Dashboard — the one screen that tells you what the business is doing today."""

from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st

from .. import console, crm, finance, projects
from ..models import money, pct
from ..ui import frame, kpi_row, next_move_block, rule, table


def render(ctx: dict[str, Any]) -> None:
    b, today = ctx["book"], ctx["today"]
    snap = console.pulse(b, today)
    base = snap["base_currency"]

    st.markdown("## Ops pulse")
    st.markdown(
        f'<div class="mim-note">{today.strftime("%A, %d %B %Y")} · '
        f'{snap["clients"]} clients · {snap["projects_active"]} live projects · '
        f'totals in {base} equivalent</div>',
        unsafe_allow_html=True,
    )
    st.write("")
    next_move_block(console.next_moves(b, today, limit=2))
    rule()

    target_note = (
        f'{pct(snap["target_pct"])} of {money(snap["target"], base)} target · {money(snap["gap_to_target"], base)} to close'
        if snap["target"] else "No monthly target set"
    )
    kpi_row([
        {"label": "Collected this month", "value": money(snap["collected_mtd"], base),
         "note": target_note, "accent": True,
         "tone": "good" if snap["target"] and snap["collected_mtd"] >= snap["target"] else "warn"},
        {"label": "Outstanding", "value": money(snap["outstanding"], base),
         "note": f'{snap["overdue_count"]} overdue · {money(snap["overdue"], base)} late', "tone": "bad" if snap["overdue"] else "good"},
        {"label": "Weighted pipeline", "value": money(snap["pipeline"], base),
         "note": f'Raw {money(snap["pipeline_raw"], base)} · win rate {pct(snap["win_rate"]) if snap["win_rate"] is not None else "—"}', "tone": "info"},
        {"label": "Forecast this month", "value": money(snap["expected_month"], base),
         "note": "Weighted: retainers + invoices + pipeline", "tone": "info"},
    ])
    st.write("")
    kpi_row([
        {"label": "Projects at risk", "value": f'{snap["projects_at_risk"]}',
         "note": f'{snap["projects_critical"]} critical · {snap["projects_active"]} active',
         "tone": "bad" if snap["projects_critical"] else "warn" if snap["projects_at_risk"] else "good"},
        {"label": "Scope exposure", "value": money(snap["scope_exposure"], base),
         "note": "Unbilled work + approved change orders", "tone": "warn" if snap["scope_exposure"] else "good"},
        {"label": "Unbilled time", "value": money(snap["unbilled"], base),
         "note": f'{snap["unbilled_hours"]}h delivered, not invoiced', "tone": "warn" if snap["unbilled"] else "good"},
        {"label": "Comms gaps", "value": f'{snap["comm_gaps"]}',
         "note": f'{snap["pending_approvals"]} approvals pending', "tone": "bad" if snap["comm_gaps"] else "good"},
    ])

    rule()
    left, right = st.columns(2, gap="large")

    with left:
        st.markdown("### Cash priority")
        st.caption("Chase in this order. Weighted by balance and lateness.")
        queue = finance.collection_queue(b["invoices"], b["clients"], today)[:6]
        rows = [{
            "Invoice": r["invoice"],
            "Client": r["client"],
            "Balance": r["balance"],
            "Late": f'{r["days_overdue"]}d' if r["days_overdue"] else "—",
            "Tier": {0: "Pre-due", 1: "Soft", 2: "Firm", 3: "Final"}[r["tier"]],
        } for r in queue]
        table(rows, config={"Balance": st.column_config.NumberColumn("Balance", format="%.0f")})
        if not queue:
            st.markdown('<div class="mim-note">Nothing owed. Rare air.</div>', unsafe_allow_html=True)

    with right:
        st.markdown("### Delivery priority")
        st.caption("Projects in the danger zone, worst first.")
        rows = []
        for row in projects.portfolio(b["projects"], b["clients"], today):
            if row["risk"] in ("Delivered",):
                continue
            rows.append({
                "Project": row["project"], "Client": row["client"], "Risk": row["risk"],
                "Done": f'{row["progress"]:.0f}%', "Due": row["due"], "Open": row["open_tasks"],
            })
        table(rows, config={"Done": st.column_config.TextColumn("Done")})
        if not rows:
            st.markdown('<div class="mim-note">Nothing in motion.</div>', unsafe_allow_html=True)

    rule()
    left, right = st.columns([3, 2], gap="large")

    with left:
        st.markdown("### Revenue trend")
        trend = finance.month_revenue(b["invoices"], 6, today)
        if trend:
            chart = frame(trend)[["month", "billed", "collected"]]
            chart["month"] = chart["month"].str.slice(0, 3)
            st.bar_chart(chart.set_index("month"), height=250, color=["#3C4A5A", "#E9B949"])
            st.caption("Billed (grey) vs collected (gold) — the gap is your accounts receivable.")

    with right:
        st.markdown("### Aging")
        aging = finance.aging_report(b["invoices"], b["clients"], today)
        totals = {bucket: round(sum(r[bucket] for r in aging), 2) for bucket in ("Current", "1-30", "31-60", "61-90", "90+")}
        rows = [{"Bucket": k, "Value": v} for k, v in totals.items()]
        table(rows, config={"Value": st.column_config.NumberColumn("Value", format="%.0f")})
        worst = max(aging, key=lambda r: r["worst"], default=None)
        if worst and worst["worst"] > 0:
            st.markdown(f'<div class="mim-note">Oldest exposure: <b>{worst["client"]}</b> at {worst["worst"]} days.</div>',
                        unsafe_allow_html=True)

    rule()
    left, right = st.columns([1, 1], gap="large")

    with left:
        st.markdown("### Needs a decision")
        approvals = projects.pending_approvals(b["projects"], b["clients"], today)
        actions = [a for a in crm.next_actions_due(b["clients"], today) if a["state"] in ("Overdue", "Today")]
        rows = []
        for row in approvals:
            rows.append({"Type": "Approval", "Item": f'{row["deliverable"]} · {row["client"]}',
                         "Waiting": f'{row["waiting_days"]}d', "Play": row["chase"]})
        for row in actions:
            rows.append({"Type": "Your action", "Item": f'{row["action"]} · {row["client"]}',
                         "Waiting": row["state"], "Play": row["due"]})
        table(rows)
        if not rows:
            st.markdown('<div class="mim-note">Nothing blocked on a decision.</div>', unsafe_allow_html=True)

    with right:
        st.markdown("### Relationship watchlist")
        watch = crm.at_risk_accounts(b["clients"], b["invoices"], b["projects"], b["settings"], today)
        rows = [{"Client": r["client"], "Stage": r["stage"], "Health": r["health"], "Why": r["why"]} for r in watch[:5]]
        table(rows)
        if not rows:
            st.markdown('<div class="mim-note">Every account is on cadence.</div>', unsafe_allow_html=True)
