"""Finance — revenue, aging, forecast, and the cash you've delivered but never invoiced."""

from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st

from .. import console, finance, projects, service
from ..models import money, pct
from ..ui import frame, kpi_row, pick, rule, table, toast


def render(ctx: dict[str, Any]) -> None:
    b, today = ctx["book"], ctx["today"]
    base = console.base_book(b)
    settings = b["settings"]
    currency = finance.base_currency(settings)
    rev = finance.revenue_summary(base["invoices"], today)
    target = float((settings.get("targets") or {}).get("monthly_revenue", 0) or 0)

    st.markdown("## Finance")
    st.markdown(f'<div class="mim-note">All totals converted to {currency}. Per-invoice amounts stay in the client currency.</div>',
                unsafe_allow_html=True)
    st.write("")
    kpi_row([
        {"label": "Collected MTD", "value": money(rev["collected_mtd"], currency),
         "note": (f'{pct(rev["collected_mtd"] / target * 100) if target else "—"} of {money(target, currency)} target'),
         "accent": True, "tone": "good" if target and rev["collected_mtd"] >= target else "warn"},
        {"label": "Billed YTD", "value": money(rev["billed_ytd"], currency),
         "note": f'Collected YTD {money(rev["collected_ytd"], currency)}'},
        {"label": "Outstanding", "value": money(rev["outstanding"], currency),
         "note": f'Overdue {money(rev["overdue"], currency)} on {rev["overdue_count"]} invoice(s)',
         "tone": "bad" if rev["overdue"] else "good"},
        {"label": "Avg days to pay", "value": f'{rev["avg_days_to_pay"] or "—"}',
         "note": "Across paid invoices", "tone": "warn" if (rev["avg_days_to_pay"] or 0) > 14 else "good"},
    ])
    rule()

    tab_aging, tab_trend, tab_forecast, tab_unbilled = st.tabs(["Aging & risk", "Trend", "Cash forecast", "Unbilled time"])

    with tab_aging:
        aging = finance.aging_report(base["invoices"], base["clients"], today)
        rows = []
        for row in aging:
            rows.append({
                "Client": row["client"], "Invoices": row["invoices"], "Current": row["Current"],
                "1-30": row["1-30"], "31-60": row["31-60"], "61-90": row["61-90"], "90+": row["90+"],
                "Balance": row["balance"], "Worst": f'{row["worst"]}d' if row["worst"] else "—",
            })
        money_cfg = {k: st.column_config.NumberColumn(k, format="%.0f")
                     for k in ("Current", "1-30", "31-60", "61-90", "90+", "Balance")}
        table(rows, config=money_cfg)
        totals = {bucket: round(sum(r[bucket] for r in aging), 2)
                  for bucket in ("Current", "1-30", "31-60", "61-90", "90+")}
        kpi_row([{"label": bucket, "value": money(value, currency),
                  "tone": "bad" if bucket in ("61-90", "90+") and value else "warn" if bucket in ("1-30", "31-60") and value else "good"}
                 for bucket, value in totals.items()])
        if not rows:
            st.markdown('<div class="mim-note">Nothing open. Clean ledger.</div>', unsafe_allow_html=True)

    with tab_trend:
        months = st.slider("Months shown", 3, 12, 6, key="trend_months")
        trend = finance.month_revenue(base["invoices"], months, today)
        chart = frame(trend)[["month", "billed", "collected"]]
        chart["month"] = chart["month"].str.slice(0, 3)
        st.bar_chart(chart.set_index("month"), height=320, color=["#3C4A5A", "#E9B949"])
        rows = [{"Month": t["month"], "Billed": t["billed"], "Collected": t["collected"],
                 "Gap": round(t["billed"] - t["collected"], 2)} for t in trend]
        table(rows, config={
            "Billed": st.column_config.NumberColumn("Billed", format="%.0f"),
            "Collected": st.column_config.NumberColumn("Collected", format="%.0f"),
            "Gap": st.column_config.NumberColumn("Gap", format="%.0f"),
        })
        totals = {"billed": sum(t["billed"] for t in trend), "collected": sum(t["collected"] for t in trend)}
        if totals["billed"]:
            st.markdown(f'<div class="mim-note">Collection efficiency over the window: '
                        f'<b>{pct(totals["collected"] / totals["billed"] * 100)}</b> of billed revenue landed.</div>',
                        unsafe_allow_html=True)

    with tab_forecast:
        horizon = st.slider("Forecast horizon (months)", 1, 6, 3, key="horizon")
        rows = finance.cash_flow_forecast(base["invoices"], base["clients"], settings, today, horizon)
        chart = frame(rows)[["month", "expected", "committed"]]
        chart["month"] = chart["month"].str.slice(0, 3)
        st.bar_chart(chart.set_index("month"), height=280, color=["#E9B949", "#3C4A5A"])
        table([{"Month": r["month"], "Recurring": r["recurring"], "Invoices": r["invoices"],
                "Pipeline (weighted)": r["pipeline"], "Expected": r["expected"],
                "Committed": r["committed"], "Target": r["target"], "Gap": r["gap"]} for r in rows],
              config={k: st.column_config.NumberColumn(k, format="%.0f")
                      for k in ("Recurring", "Invoices", "Pipeline (weighted)", "Expected", "Committed", "Target", "Gap")})
        coverage = finance.pipeline_covered_ratio(rows)
        notes = finance.forecast_notes(rows, settings)
        st.markdown(
            f'<div class="mim-note">Model: retainers monthly · open invoices at 95% in their due month · overdue at 90% this month · '
            f'pipeline weighted by stage probability. '
            f'{f"Coverage of target: <b>{pct(coverage)}</b>. " if coverage else ""}{" ".join(notes)}</div>',
            unsafe_allow_html=True,
        )

    with tab_unbilled:
        rows = projects.unbilled_by_client(b["projects"], b["clients"])
        rows = [r for r in rows if r["value"] > 0 or r["out_of_scope_value"] > 0]
        if not rows:
            st.markdown('<div class="mim-note">Every logged hour is billed. That is the standard.</div>', unsafe_allow_html=True)
            return
        table([{"Client": r["client"], "Hours": r["hours"],
                "Billable value": r["value"], "Currency": r["currency"],
                "Out of scope hours": r["out_of_scope_hours"], "Out of scope value": r["out_of_scope_value"],
                "Projects": ", ".join(r["projects"])} for r in rows],
              config={"Hours": st.column_config.NumberColumn("Hours", format="%.1f"),
                      "Billable value": st.column_config.NumberColumn("Billable value", format="%.0f"),
                      "Out of scope value": st.column_config.NumberColumn("Out of scope value", format="%.0f")})
        st.caption("Out-of-scope hours need a change order, not an invoice. Billable hours go straight to a draft invoice.")

        options = [(r["client_id"], r["client"]) for r in rows if r["value"] > 0]
        if options:
            client_choice = pick("Convert time to invoice", options, key="bill_client")
            targets = [p for p in b["projects"]
                       if p.get("client_id") == client_choice and projects.uninvoiced_time(p)["value"] > 0]
            if targets:
                project_id = pick("Project", [(p["id"], p["name"]) for p in targets], key="bill_project")
                chosen = next(p for p in targets if p["id"] == project_id)
                total = projects.uninvoiced_time(chosen)["value"]
                st.markdown(f'<div class="mim-note">Will create a draft invoice for '
                            f'<b>{money(total, chosen.get("currency", "USD"))}</b> of logged time.</div>',
                            unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                if c1.button("Create draft invoice", type="primary", width="stretch"):
                    inv_id = service.bill_time_to_invoice(project_id, status="draft")
                    if inv_id:
                        toast(f"{inv_id} drafted from logged time")
                        st.session_state["last_invoice"] = inv_id
                        st.rerun()
                    st.error("Nothing billable on that project.")
                if c2.button("Flag time as billed", width="stretch"):
                    touched = service.mark_project_time_invoiced(project_id)
                    toast(f"{touched} time entries marked invoiced")
                    st.rerun()
            else:
                st.markdown('<div class="mim-note">No billable time left on that client.</div>',
                            unsafe_allow_html=True)
