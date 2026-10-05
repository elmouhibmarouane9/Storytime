"""Invoicing — build, send, chase, and close. The cash engine."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from .. import comms, console, finance, render as docs, service
from ..models import money
from ..ui import draft_surface, kpi_row, pick, pill_for, rule, table, toast


def render(ctx: dict[str, Any]) -> None:
    b, today = ctx["book"], ctx["today"]
    st.markdown("## Invoices")
    base = console.base_book(b)
    currency = base["base_currency"]
    rev = finance.revenue_summary(base["invoices"], today)
    native_outstanding = console.pulse(b, today)["outstanding_by_currency"]

    kpi_row([
        {"label": f"Outstanding ({currency})", "value": money(rev["outstanding"], currency),
         "note": f'{rev["open_count"]} open · native: {console.currency_breakdown(native_outstanding)}'},
        {"label": "Overdue", "value": money(rev["overdue"], currency),
         "note": f'{rev["overdue_count"]} invoices late', "tone": "bad" if rev["overdue"] else "good"},
        {"label": "Collected this month", "value": money(rev["collected_mtd"], currency),
         "note": f'Billed {money(rev["billed_mtd"], currency)}', "accent": True},
        {"label": "Drafts on the shelf", "value": money(rev["draft_value"], currency),
         "note": f'Avg days to pay {rev["avg_days_to_pay"] or "—"}', "tone": "warn" if rev["draft_value"] else "good"},
    ])
    rule()

    tab_ledger, tab_new, tab_chase, tab_open = st.tabs(["Ledger", "New invoice", "Collections", "Invoice view"])

    with tab_ledger:
        _ledger(b, today)

    with tab_new:
        _new_invoice(b, today)

    with tab_chase:
        _collections(b, today)

    with tab_open:
        _invoice_view(b, today)


def _ledger(b: dict, today: date) -> None:
    statuses = ["all", "draft", "sent", "partial", "paid", "overdue", "void"]
    choice = st.radio("Filter", statuses, horizontal=True, label_visibility="collapsed", key="inv_filter")
    rows = []
    for inv in b["invoices"]:
        status = finance.effective_status(inv, today)
        if choice != "all" and status != choice:
            continue
        client = next((c for c in b["clients"] if c["id"] == inv.get("client_id")), {})
        rows.append({
            "Invoice": inv["id"],
            "Client": client.get("company") or client.get("name", "—"),
            "Issued": inv.get("issue_date", "—"),
            "Due": inv.get("due_date", "—"),
            "Currency": inv.get("currency", "USD"),
            "Total": finance.invoice_total(inv),
            "Paid": finance.invoice_paid(inv),
            "Balance": finance.invoice_balance(inv),
            "Late": f'{finance.days_overdue(inv, today)}d' if finance.days_overdue(inv, today) else "—",
            "Status": status,
        })
    table(rows, config={
        "Total": st.column_config.NumberColumn("Total", format="%.2f"),
        "Paid": st.column_config.NumberColumn("Paid", format="%.2f"),
        "Balance": st.column_config.NumberColumn("Balance", format="%.2f"),
    }, height=380)
    st.caption(f'{len(rows)} invoice(s) shown · balances in the invoice currency. Totals on the Finance page convert to base.')

    rule()
    st.markdown("### Record a payment")
    with st.form("payment"):
        c1, c2, c3, c4 = st.columns(4)
        open_ids = [i["id"] for i in b["invoices"] if finance.effective_status(i, today) in ("sent", "partial", "overdue", "draft")]
        if not open_ids:
            st.markdown('<div class="mim-note">No open invoices.</div>', unsafe_allow_html=True)
            return
        inv_id = c1.selectbox("Invoice", open_ids)
        inv = next(i for i in b["invoices"] if i["id"] == inv_id)
        c2.markdown(f'**Balance** {money(finance.invoice_balance(inv), inv.get("currency", "USD"), 2)}')
        amount = c3.number_input("Amount", value=float(finance.invoice_balance(inv)), step=100.0, min_value=0.0,
                                 key=f"pay_amt_{inv_id}")
        when = c4.date_input("Date", today)
        c1, c2 = st.columns(2)
        method = c1.selectbox("Method", ["wire", "transfer", "card", "cash", "other"])
        note = c2.text_input("Note", "")
        if st.form_submit_button("Record payment", width="stretch"):
            service.record_payment(inv_id, amount, when.isoformat(), method, note)
            toast(f'{money(amount, inv.get("currency", "USD"), 2)} recorded on {inv_id}')
            st.rerun()


def _new_invoice(b: dict, today: date) -> None:
    st.markdown("### Build an invoice")
    if not b["clients"]:
        st.markdown('<div class="mim-note">Add a client first.</div>', unsafe_allow_html=True)
        return
    options = console.client_options(b)
    c1, c2, c3 = st.columns([2, 2, 1])
    client_id = None
    with c1:
        client_id = pick("Client", options, key="inv_client")
    client = next(c for c in b["clients"] if c["id"] == client_id)
    project_options = [(p["id"], p["name"]) for p in b["projects"] if p.get("client_id") == client_id]
    with c2:
        project_id = pick("Project (optional)", project_options, key="inv_project",
                          allow_empty=True, empty_label="— none —")
    currency = c3.selectbox("Currency", ["USD", "EUR", "GBP", "AED", "MAD", "MXN"],
                            index=["USD", "EUR", "GBP", "AED", "MAD", "MXN"].index(client.get("currency", "USD")),
                            key="inv_cur")

    st.caption("Line items — add rows as needed. Qty × Rate, no maths required.")
    default_items = [{"desc": "", "qty": 1, "rate": 0.0, "unit": "fixed"}]
    items_df = st.data_editor(
        pd.DataFrame(default_items), num_rows="dynamic", width="stretch", key="inv_items_editor",
        column_config={
            "desc": st.column_config.TextColumn("Description", width="large", required=True),
            "qty": st.column_config.NumberColumn("Qty", min_value=0.0, step=1.0, format="%g"),
            "rate": st.column_config.NumberColumn("Rate", min_value=0.0, step=50.0, format="%.2f"),
            "unit": st.column_config.SelectboxColumn("Unit", options=["fixed", "hr", "day", "mo", "unit"]),
        },
    )
    c1, c2, c3, c4 = st.columns(4)
    issue = c1.date_input("Issue date", today, key="inv_issue")
    terms_days = c2.number_input("Terms (days)", value=14, min_value=0, max_value=120, key="inv_terms")
    tax = c3.number_input("Tax rate %", value=float((b["settings"].get("invoice") or {}).get("tax_rate", 0)) * 100,
                          min_value=0.0, max_value=40.0, step=0.5, key="inv_tax")
    status = c4.selectbox("Issue as", ["draft", "sent"], key="inv_status")
    notes = st.text_input("Notes on the invoice", project_next(b, project_id), key="inv_notes")

    draft = {
        "items": [r for r in items_df.to_dict("records") if str(r.get("desc", "")).strip()],
        "currency": currency, "tax_rate": tax / 100.0,
    }
    preview_total = finance.invoice_subtotal(draft) * (1 + tax / 100.0)
    st.markdown(f'<div class="mim-note">Invoice total will read <b>{money(preview_total, currency, 2)}</b> · '
                f'{len(draft["items"])} line item(s).</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([1, 3])
    if c1.button("Create invoice", type="primary", width="stretch"):
        if not draft["items"]:
            st.error("At least one line item with a description.")
        else:
            inv_id = service.create_invoice({
                "client_id": client_id, "project_id": project_id or None,
                "items": draft["items"], "currency": currency, "tax_rate": tax / 100.0,
                "issue_date": issue.isoformat(), "terms_days": int(terms_days),
                "notes": notes, "status": status,
            })
            if status == "sent" and project_id:
                service.log_communication(client_id, {
                    "date": issue.isoformat(), "channel": "email", "direction": "out",
                    "subject": f"Invoice {inv_id}", "summary": f'Invoice {inv_id} issued for {money(preview_total, currency, 2)}.',
                })
            toast(f"{inv_id} created as {status}")
            st.session_state["last_invoice"] = inv_id
            st.rerun()
    c2.markdown('<div class="mim-note">Drafts don\'t count toward revenue until sent. Create it, review it, then send.</div>',
                unsafe_allow_html=True)


def project_next(b: dict, project_id: str) -> str:
    for project in b["projects"]:
        if project["id"] == project_id:
            return project.get("scope_summary", "")
    return ""


def _collections(b: dict, today: date) -> None:
    queue = [row for row in finance.collection_queue(b["invoices"], b["clients"], today)]
    if not queue:
        st.markdown('<div class="mim-note">Nothing outstanding. Enjoy it.</div>', unsafe_allow_html=True)
        return
    st.markdown("### Collection queue")
    st.caption("Ranked by balance × lateness. Work top down.")
    table([{ "Invoice": r["invoice"], "Client": r["client"], "Balance": r["balance"], "Currency": r["currency"],
             "Due": r["due"], "Late": f'{r["days_overdue"]}d' if r["days_overdue"] else "—",
             "Tone": {0: "Pre-due", 1: "Soft", 2: "Firm", 3: "Final"}[r["tier"]],
             "Priority": r["priority"]} for r in queue],
          config={"Balance": st.column_config.NumberColumn("Balance", format="%.2f"),
                  "Priority": st.column_config.NumberColumn("Priority", format="%.0f")})

    rule()
    st.markdown("### Next reminder")
    options = [r["invoice"] for r in queue]
    inv_id = st.selectbox("Invoice", options, key="chase_inv")
    inv = next(i for i in b["invoices"] if i["id"] == inv_id)
    row = next(r for r in queue if r["invoice"] == inv_id)
    client = next((c for c in b["clients"] if c["id"] == inv.get("client_id")), {})
    tier = row["tier"]
    lang = st.radio("Language", ["EN", "ES"], horizontal=True,
                    index=0 if client.get("language", "EN") == "EN" else 1, key="chase_lang")
    subject, body = comms.reminder_for(inv, client, today, lang)
    tier_label = {0: "Pre-due heads-up", 1: "Soft nudge", 2: "Firm, decision-forcing", 3: "Final notice"}[tier]
    reminders_sent = len(inv.get("reminders") or [])
    st.markdown(
        f'{pill_for("overdue" if row["days_overdue"] else "sent", "invoice")} '
        f'<span class="mim-note">Tone: <b>{tier_label}</b> · {reminders_sent} reminder(s) already sent · '
        f'{row["days_overdue"]} days late · balance {money(row["balance"], row["currency"], 2)}</span>',
        unsafe_allow_html=True,
    )
    draft_surface(subject, body, key=f"chase_{inv_id}_{tier}_{lang}", filename=f"{inv_id}_reminder_{tier}", language=lang)
    c1, c2 = st.columns([1, 1])
    if c1.button("Mark reminder sent", width="stretch"):
        service.log_reminder(inv_id, tier, "email", today.isoformat())
        toast(f"Reminder logged on {inv_id}")
        st.rerun()
    if c2.button("Mark as paid in full", width="stretch"):
        service.record_payment(inv_id, finance.invoice_balance(inv), today.isoformat(), "wire", "Marked paid")
        toast(f"{inv_id} closed")
        st.rerun()


def _invoice_view(b: dict, today: date) -> None:
    if not b["invoices"]:
        st.markdown('<div class="mim-note">No invoices yet.</div>', unsafe_allow_html=True)
        return
    ids = [i["id"] for i in b["invoices"]]
    default = st.session_state.get("last_invoice", ids[0])
    inv_id = st.selectbox("Invoice", ids, index=ids.index(default) if default in ids else 0, key="view_inv")
    inv = next(i for i in b["invoices"] if i["id"] == inv_id)
    client = next((c for c in b["clients"] if c["id"] == inv.get("client_id")), {})
    settings = b["settings"]
    markdown_doc = docs.invoice_markdown(inv, client, settings)
    html_doc = docs.invoice_html(inv, client, settings)

    c1, c2, c3, c4 = st.columns(4)
    c1.download_button("Download .md", markdown_doc, file_name=f"{inv_id}.md", mime="text/markdown",
                       width="stretch")
    c2.download_button("Download .html", html_doc, file_name=f"{inv_id}.html", mime="text/html",
                       width="stretch")
    c3.download_button("Download .json", json.dumps(inv, indent=2),
                       file_name=f"{inv_id}.json", mime="application/json", width="stretch")
    status = finance.effective_status(inv, today)
    if status == "draft" and c4.button("Mark as sent", width="stretch"):
        service.set_invoice_status(inv_id, "sent")
        toast(f"{inv_id} marked sent")
        st.rerun()
    st.caption("HTML opens in the browser — Ctrl+P for a clean PDF. Nothing sends itself.")

    with st.expander("Preview", expanded=True):
        st.markdown(markdown_doc)
