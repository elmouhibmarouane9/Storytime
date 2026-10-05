"""CRM — pipeline board, full client profiles, health, comms history, stage moves."""

from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st

from .. import comms, console, crm, service
from ..models import STAGES, money, parse_date
from ..ui import draft_surface, kpi_row, pick, pill, pill_for, rule, table, toast


def pipeline_board(b: dict, today: date) -> None:
    columns = st.columns(len(STAGES), gap="small")
    for col, stage in zip(columns, STAGES):
        in_stage = [c for c in b["clients"] if c.get("stage") == stage]
        value = sum(float(c.get("deal_value", 0) or 0) for c in in_stage)
        col.markdown(
            f'<div class="mim-card" style="margin-bottom:8px">'
            f'<div class="kpi-label">{stage}</div>'
            f'<div class="kpi-value" style="font-size:1.15rem">{money(value)}</div>'
            f'<div class="kpi-note">{len(in_stage)} client(s)</div></div>',
            unsafe_allow_html=True,
        )
        for client in in_stage:
            col.markdown(
                f'<div class="mim-card" style="margin-bottom:6px;padding:10px 12px">'
                f'<div style="font-weight:600;font-size:.86rem">{client.get("company") or client.get("name")}</div>'
                f'<div class="kpi-note" style="margin-top:2px">{money(client.get("deal_value", 0), client.get("currency", "USD"))}'
                f' · {client.get("language", "EN")}</div></div>',
                unsafe_allow_html=True,
            )


def render(ctx: dict[str, Any]) -> None:
    b, today = ctx["book"], ctx["today"]
    st.markdown("## Clients & pipeline")

    base_book = console.base_book(b)
    currency = base_book["base_currency"]
    stages = crm.pipeline_summary(base_book["clients"])
    raw = sum(float(c.get("deal_value", 0) or 0) for c in base_book["clients"])
    kpi_row([
        {"label": "Clients", "value": len(b["clients"]), "note": f'{sum(1 for c in b["clients"] if c.get("stage") == "Active")} active'},
        {"label": f"Pipeline ({currency})", "value": money(crm.weighted_pipeline(base_book["clients"]), currency),
         "note": f'Raw {money(raw, currency)} · native: {console.currency_breakdown(console.native_pipeline_breakdown(b["clients"]))}',
         "accent": True},
        {"label": "Avg deal", "value": money(crm.avg_deal(base_book["clients"]), currency),
         "note": f'Win rate {crm.win_rate(b["clients"]) or 0:.0f}%'},
        {"label": "Proposals out", "value": sum(1 for c in b["clients"] if c.get("stage") == "Proposal Sent"),
         "note": "on the table now", "tone": "info"},
    ])
    rule()

    tab_board, tab_list, tab_add = st.tabs(["Pipeline board", "Client list", "Add client"])

    with tab_board:
        pipeline_board(b, today)
        rule()
        st.markdown("### Stage economics")
        rows = [{"Stage": s["stage"], "Clients": s["clients"], "Value": s["value"],
                 "Probability": f'{s["probability"] * 100:.0f}%', "Weighted": s["weighted"]} for s in stages]
        table(rows, config={
            "Value": st.column_config.NumberColumn("Value", format="%.0f"),
            "Weighted": st.column_config.NumberColumn("Weighted", format="%.0f"),
        })
        history = crm.stage_history_rows(b["clients"])[:8]
        if history:
            st.markdown("### Recent stage moves")
            table([{"Date": h["date"], "Client": h["client"], "From": h["from"], "To": h["to"]} for h in history])

    with tab_list:
        rows = console.client_rows(b, today)
        table(
            [{"ID": r["id"], "Client": r["company"], "Contact": r["name"], "Stage": r["stage"],
              "Health": r["health"], "Deal": r["deal_value"], "Owed": r["outstanding"],
              "Lifetime": r["lifetime_billed"], "Last touch": r.get("last_contact", "—"),
              "Next action": (r.get("next_action") or {}).get("note", "—")} for r in
             sorted(rows, key=lambda r: r["health"])],
            config={
                "Health": st.column_config.ProgressColumn("Health", min_value=0, max_value=100, format="%d"),
                "Deal": st.column_config.NumberColumn("Deal", format="%.0f"),
                "Owed": st.column_config.NumberColumn("Owed", format="%.0f"),
                "Lifetime": st.column_config.NumberColumn("Billed", format="%.0f"),
            },
            height=320,
        )
        rule()
        _client_detail(b, today)

    with tab_add:
        _add_client_form(b)


def _client_detail(b: dict, today: date) -> None:
    options = console.client_options(b)
    if not options:
        st.markdown('<div class="mim-note">No clients yet. Add one.</div>', unsafe_allow_html=True)
        return
    st.markdown("### Client file")
    choice = pick("Open a file", options, key="crm_detail")
    client = next(c for c in b["clients"] if c["id"] == choice)
    health = crm.health(client, b["invoices"], b["projects"], b["settings"], today)
    value = crm.client_value(client, b["invoices"], today)
    currency = client.get("currency", "USD")

    head_l, head_r = st.columns([2, 1])
    with head_l:
        st.markdown(
            f'### {client.get("company")} {pill_for(client.get("stage", "—"), "stage")} '
            f'{pill(health["band"], "good" if health["score"] >= 80 else "warn" if health["score"] >= 60 else "bad")}',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="mim-note">{client.get("name")} · {client.get("role", "—")} · {client.get("location", "—")} · '
            f'{client.get("email", "—")} · {client.get("language", "EN")} · {client.get("timezone", "—")}</div>',
            unsafe_allow_html=True,
        )
    with head_r:
        st.metric("Health", f'{health["score"]}/100', help=" · ".join(health["reasons"]))

    kpi_row([
        {"label": "Deal value", "value": money(client.get("deal_value", 0), currency), "note": f'Since {client.get("since", "—")}'},
        {"label": "Lifetime billed", "value": money(value["lifetime_billed"], currency), "note": f'{value["invoices"]} invoices'},
        {"label": "Outstanding", "value": money(value["outstanding"], currency),
         "note": "Overdue" if value["outstanding"] > 0 else "Clean", "tone": "bad" if value["outstanding"] else "good"},
        {"label": "Last contact", "value": f'{crm.days_since(client.get("last_contact"), today)}d',
         "note": f'Cadence {crm.cadence_for(client, b["settings"])}d', "tone": "warn"},
    ])
    rule()

    tab_profile, tab_comms, tab_money, tab_actions = st.tabs(["Profile", "Comms log", "Money", "Actions"])

    with tab_profile:
        st.markdown(f'**Communication style** — {client.get("communication_style") or "—"}')
        st.markdown(f'**Payment behaviour** — {client.get("payment_behaviour") or "—"}')
        st.markdown(f'**Preferences** — {", ".join(client.get("preferences") or []) or "—"}')
        st.markdown(f'**Notes** — {client.get("notes") or "—"}')
        st.markdown(f'**Tags** — {", ".join(client.get("tags") or []) or "—"}')
        with st.expander("Edit profile"):
            with st.form(f"profile_{client['id']}"):
                c1, c2 = st.columns(2)
                name = c1.text_input("Contact name", client.get("name", ""))
                company = c2.text_input("Company", client.get("company", ""))
                c1, c2, c3 = st.columns(3)
                email = c1.text_input("Email", client.get("email", ""))
                role = c2.text_input("Role", client.get("role", ""))
                location = c3.text_input("Location", client.get("location", ""))
                c1, c2, c3 = st.columns(3)
                deal = c1.number_input("Deal value", value=float(client.get("deal_value", 0) or 0), step=500.0)
                cur = c2.selectbox("Currency", ["USD", "EUR", "GBP", "AED", "MAD", "MXN"],
                                   index=["USD", "EUR", "GBP", "AED", "MAD", "MXN"].index(client.get("currency", "USD")))
                lang = c3.selectbox("Language", ["EN", "ES"], index=["EN", "ES"].index(client.get("language", "EN")))
                style = st.text_area("Communication style", client.get("communication_style", ""), height=70)
                payment = st.text_input("Payment behaviour", client.get("payment_behaviour", ""))
                prefs = st.text_input("Preferences (comma separated)", ", ".join(client.get("preferences") or []))
                tags = st.text_input("Tags (comma separated)", ", ".join(client.get("tags") or []))
                notes = st.text_area("Notes", client.get("notes", ""), height=70)
                if st.form_submit_button("Save file", width="stretch"):
                    service.update_client(client["id"], {
                        "name": name, "company": company, "email": email, "role": role, "location": location,
                        "deal_value": deal, "currency": cur, "language": lang, "communication_style": style,
                        "payment_behaviour": payment,
                        "preferences": [p.strip() for p in prefs.split(",") if p.strip()],
                        "tags": [t.strip() for t in tags.split(",") if t.strip()],
                        "notes": notes,
                    })
                    toast("Client file updated")
                    st.rerun()

    with tab_comms:
        messages = sorted([m for m in b["messages"] if m["client_id"] == client["id"]],
                          key=lambda m: m["date"], reverse=True)
        rows = [{"Date": m["date"], "Channel": m["channel"], "Dir": "→" if m["direction"] == "out" else "←",
                 "Subject": m["subject"], "Summary": m["summary"],
                 "Tier": str(m.get("reminder_tier") or "")} for m in messages]
        table(rows, height=280)
        gap = crm.communication_gaps([client], b["settings"], today)
        if gap:
            st.warning(f'{gap[0]["days_silent"]} days silent — cadence is {gap[0]["threshold"]}d. {gap[0]["action"]}')
        with st.expander("Log a communication"):
            with st.form(f"log_{client['id']}"):
                c1, c2, c3 = st.columns(3)
                when = c1.date_input("Date", today)
                channel = c2.selectbox("Channel", ["email", "call", "whatsapp", "slack", "loom", "meeting"])
                direction_label = c3.selectbox("Direction", ["Outbound", "Inbound"])
                subject = st.text_input("Subject")
                summary = st.text_area("Summary", height=80)
                if st.form_submit_button("Log it", width="stretch"):
                    service.log_communication(client["id"], {
                        "date": when.isoformat(), "channel": channel,
                        "direction": "out" if direction_label == "Outbound" else "in",
                        "subject": subject, "summary": summary,
                    })
                    toast("Logged")
                    st.rerun()

    with tab_money:
        rows = [{"Invoice": i["id"], "Issued": i["issue_date"], "Due": i["due_date"],
                 "Total": finance_total(i), "Paid": sum(float(p.get("amount", 0) or 0) for p in i.get("payments", [])),
                 "Status": i.get("status", "—")} for i in b["invoices"] if i.get("client_id") == client["id"]]
        table(rows, config={"Total": st.column_config.NumberColumn("Total", format="%.0f"),
                            "Paid": st.column_config.NumberColumn("Paid", format="%.0f")})
        if not rows:
            st.markdown('<div class="mim-note">No invoices on file.</div>', unsafe_allow_html=True)

    with tab_actions:
        left, right = st.columns(2, gap="large")
        with left:
            st.markdown("**Move the stage**")
            current = STAGES.index(client.get("stage", "Lead"))
            new_stage = st.selectbox("New stage", STAGES, index=current, key=f"stage_{client['id']}")
            new_value = st.number_input("Updated deal value", value=float(client.get("deal_value", 0) or 0),
                                        step=500.0, key=f"val_{client['id']}")
            if st.button("Apply stage move", key=f"movestage_{client['id']}", width="stretch"):
                service.set_stage(client["id"], new_stage, new_value)
                toast(f'Moved to {new_stage}')
                st.rerun()
            rule()
            st.markdown("**Set the next action**")
            with st.form(f"next_{client['id']}"):
                note = st.text_input("Action", (client.get("next_action") or {}).get("note", ""))
                due_default = parse_date((client.get("next_action") or {}).get("due")) or today
                due = st.date_input("Due", due_default)
                if st.form_submit_button("Set it", width="stretch"):
                    service.set_next_action(client["id"], note, due.isoformat())
                    toast("Next action set")
                    st.rerun()
        with right:
            st.markdown("**Draft a message**")
            kinds = comms.kinds()
            kind_label = st.selectbox("Template", [k[1] for k in kinds], key=f"kind_{client['id']}")
            kind = dict((label, key) for key, label in kinds)[kind_label]
            lang = st.radio("Language", ["EN", "ES"], index=0 if client.get("language", "EN") == "EN" else 1,
                            horizontal=True, key=f"lang_{client['id']}")
            extra: dict[str, Any] = {}
            if kind == "proposal_send":
                extra = {"project": st.text_input("Project", "Rebrand + launch", key=f"p_{client['id']}")}
            if kind in ("proposal_nudge", "gap_nudge"):
                extra = {"days": crm.days_since(client.get("last_contact"), today) or 0}
            subject, body = comms.render(kind, client, extra, lang)
            draft_surface(subject, body, key=f"{client['id']}_{kind}_{lang}",
                          filename=f"{client['id']}_{kind}", language=lang)
            if st.button("Log this as sent", key=f"sent_{client['id']}_{kind}", width="stretch"):
                service.log_communication(client["id"], {
                    "date": today.isoformat(), "channel": "email", "direction": "out",
                    "subject": subject, "summary": body.split("\n")[0][:200],
                })
                toast("Logged as sent")
                st.rerun()


def finance_total(invoice: dict) -> float:
    from ..finance import invoice_total

    return invoice_total(invoice)


def _add_client_form(b: dict) -> None:
    st.markdown("### New client")
    with st.form("new_client"):
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("Contact name*")
        company = c2.text_input("Company")
        role = c3.text_input("Role")
        c1, c2, c3 = st.columns(3)
        email = c1.text_input("Email")
        phone = c2.text_input("Phone")
        location = c3.text_input("Location")
        c1, c2, c3 = st.columns(3)
        stage = c1.selectbox("Stage", STAGES)
        deal = c2.number_input("Deal value", value=0.0, step=500.0)
        cur = c3.selectbox("Currency", ["USD", "EUR", "GBP", "AED", "MAD", "MXN"])
        c1, c2 = st.columns(2)
        lang = c1.selectbox("Language", ["EN", "ES"])
        source = c2.text_input("Source", "Referral")
        style = st.text_area("Communication style", height=70,
                             placeholder="Executive brevity. Reads the headline. Hates being CC'd.")
        payment = st.text_input("Payment behaviour", placeholder="Slow but reliable — pays 3 weeks late.")
        tags = st.text_input("Tags (comma separated)", placeholder="retainer, DTC")
        notes = st.text_area("Notes", height=70)
        if st.form_submit_button("Create client file", width="stretch"):
            if not name.strip():
                st.error("Name required.")
            else:
                cid = service.new_client({
                    "name": name, "company": company, "role": role, "email": email, "phone": phone,
                    "location": location, "stage": stage, "deal_value": deal, "currency": cur,
                    "language": lang, "source": source, "communication_style": style,
                    "payment_behaviour": payment, "notes": notes,
                    "tags": [t.strip() for t in tags.split(",") if t.strip()],
                })
                toast(f"{cid} created")
                st.rerun()
