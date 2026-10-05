"""Client communications — draft, summarise, and catch the silence before it costs you."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import streamlit as st

from .. import comms, console, crm, projects, service
from ..models import money
from ..ui import draft_surface, kpi_row, pick, pill, rule, table, toast


def render(ctx: dict[str, Any]) -> None:
    b, today = ctx["book"], ctx["today"]
    gaps = crm.communication_gaps(b["clients"], b["settings"], today)
    approvals = projects.pending_approvals(b["projects"], b["clients"], today)
    this_month = [m for m in b["messages"] if m.get("date", "").startswith(today.strftime("%Y-%m"))]

    st.markdown("## Comms desk")
    st.markdown(f'<div class="mim-note">Brand voice — {b["settings"].get("brand_voice", "Confident. Cinematic. Direct.")}</div>',
                unsafe_allow_html=True)
    st.write("")
    kpi_row([
        {"label": "Threads gone cold", "value": len(gaps),
         "note": f'{sum(1 for g in gaps if g["severity"] == "Critical")} critical',
         "tone": "bad" if gaps else "good"},
        {"label": "Approvals waiting", "value": len(approvals),
         "note": f'{max([a["waiting_days"] for a in approvals], default=0)}d longest', "tone": "warn" if approvals else "good"},
        {"label": "Logged this month", "value": len(this_month),
         "note": f'{sum(1 for m in this_month if m["direction"] == "out")} outbound'},
        {"label": "Clients on cadence", "value": f'{len(b["clients"]) - len(gaps)}/{len(b["clients"])}',
         "note": "Contact cadence enforced by stage", "accent": True},
    ])
    rule()

    tab_compose, tab_summary, tab_gap, tab_history = st.tabs(["Compose", "Thread summariser", "Silence radar", "History"])

    with tab_compose:
        _compose(b, today)

    with tab_summary:
        _summariser()

    with tab_gap:
        if not gaps:
            st.markdown('<div class="mim-note">Every thread is warm. Keep it that way.</div>', unsafe_allow_html=True)
        else:
            table([{"Client": g["client"], "Stage": g["stage"], "Last contact": g["last_contact"],
                    "Days silent": g["days_silent"], "Cadence": f'{g["threshold"]}d',
                    "Severity": g["severity"], "Play": g["action"]} for g in gaps])
            options = [(g["client_id"], g["client"]) for g in gaps]
            gap_client = pick("Draft the re-open", options, key="gap_pick")
            client = next(c for c in b["clients"] if c["id"] == gap_client)
            lang = st.radio("Language", ["EN", "ES"], horizontal=True,
                            index=0 if client.get("language", "EN") == "EN" else 1, key="gap_lang")
            subject, body = comms.gap_draft(client, today, lang)
            draft_surface(subject, body, key=f"gap_{gap_client}_{lang}", filename=f"gap_{gap_client}", language=lang)
            if st.button("Log as sent", key=f"gap_sent_{gap_client}", width="stretch"):
                service.log_communication(gap_client, {"date": today.isoformat(), "channel": "email", "direction": "out",
                                                 "subject": subject, "summary": body.split("\n")[0][:200]})
                toast("Logged")
                st.rerun()

    with tab_history:
        rows = []
        for m in sorted(b["messages"], key=lambda m: m.get("date", ""), reverse=True):
            client = next((c for c in b["clients"] if c["id"] == m.get("client_id")), {})
            rows.append({"Date": m.get("date"), "Client": client.get("company", "—"),
                         "Channel": m.get("channel"), "Dir": "→ out" if m.get("direction") == "out" else "← in",
                         "Subject": m.get("subject"), "Summary": m.get("summary"),
                         "Tier": str(m.get("reminder_tier") or "")})
        table(rows, height=420)
        with st.expander("Log an interaction by hand"):
            options = console.client_options(b)
            with st.form("manual_log"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    client_id = pick("Client", options, key="manual_log_client")
                when = c2.date_input("Date", today)
                channel = c3.selectbox("Channel", ["email", "call", "whatsapp", "slack", "loom", "meeting"])
                c1, c2 = st.columns(2)
                direction_label = c1.selectbox("Direction", ["Outbound", "Inbound"])
                subject = c2.text_input("Subject")
                summary = st.text_area("Summary", height=80)
                if st.form_submit_button("Log it", width="stretch"):
                    service.log_communication(client_id, {"date": when.isoformat(), "channel": channel,
                                                          "direction": "out" if direction_label == "Outbound" else "in",
                                                          "subject": subject, "summary": summary})
                    toast("Logged")
                    st.rerun()


def _compose(b: dict, today: date) -> None:
    if not b["clients"]:
        st.markdown('<div class="mim-note">Add a client before drafting.</div>', unsafe_allow_html=True)
        return
    options = console.client_options(b)
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        client_id = pick("Client", options, key="compose_client")
    client = next(c for c in b["clients"] if c["id"] == client_id)
    kinds = comms.kinds()
    with c2:
        kind_label = st.selectbox("Template", [k[1] for k in kinds], key="compose_kind")
    kind = dict((label, key) for key, label in kinds)[kind_label]
    lang = c3.radio("Language", ["EN", "ES"], index=0 if client.get("language", "EN") == "EN" else 1, key="compose_lang")

    extra: dict[str, Any] = {}
    if kind in ("proposal_send", "proposal_nudge", "onboarding", "project_update", "upsell", "change_order"):
        with st.expander("Fill the blanks", expanded=True):
            if kind == "proposal_send":
                c1, c2 = st.columns(2)
                extra["project"] = c1.text_input("Project name", "Rebrand + launch", key="f_proj")
                extra["outcome"] = c2.text_input("Outcome (the business result)", "A brand that closes bigger deals", key="f_out")
                extra["scope"] = st.text_area("Scope", "Strategy, identity, launch campaign, 2 revision rounds", height=70, key="f_scope")
                c1, c2, c3 = st.columns(3)
                extra["investment"] = c1.text_input("Investment", money(client.get("deal_value", 0), client.get("currency", "USD")), key="f_inv")
                extra["terms"] = c2.text_input("Terms", "50% deposit, 50% on delivery", key="f_terms")
                extra["timeline"] = c3.text_input("Timeline", "4 weeks, 3 milestones", key="f_time")
                extra["start_date"] = st.text_input("Start date", (today + timedelta(days=7)).isoformat(), key="f_start")
            elif kind == "proposal_nudge":
                extra["days"] = crm.days_since(client.get("last_contact"), today) or 0
            elif kind == "onboarding":
                c1, c2 = st.columns(2)
                extra["access"] = c1.text_input("Access needed", "ad account, domain, analytics", key="f_access")
                extra["start_date"] = c2.text_input("Start date", (today + timedelta(days=3)).isoformat(), key="f_start2")
                c1, c2 = st.columns(2)
                extra["cadence"] = c1.text_input("Cadence", "weekly written update, monthly strategy call", key="f_cad")
                extra["first_win"] = c2.text_input("First win date", (today + timedelta(days=14)).isoformat(), key="f_win")
            elif kind == "upsell":
                c1, c2 = st.columns(2)
                extra["trigger"] = c1.text_input("Why now", "Phase one delivered on time and under budget.", key="f_trig")
                extra["offer"] = c2.text_input("Phase two offer", "Retainer covering paid social + content", key="f_off")
                extra["why_now"] = st.text_input("Cost of waiting", "Every week without paid support is compounding CAC.", key="f_why")
                c1, c2, c3 = st.columns(3)
                extra["amount"] = c1.text_input("Investment", money(float(client.get("deal_value", 0) or 0) * 0.4, client.get("currency", "USD")), key="f_amt")
                extra["start_date"] = c2.text_input("Start date", (today + timedelta(days=10)).isoformat(), key="f_start3")
                extra["first_win"] = c3.text_input("First win", (today + timedelta(days=40)).isoformat(), key="f_win2")
            elif kind == "change_order":
                c1, c2 = st.columns(2)
                extra["title"] = c1.text_input("Change order title", "Property 3 creative adaptation", key="f_t")
                extra["scope"] = c2.text_input("Scope added", "6 assets + rollout plan", key="f_s")
                c1, c2, c3 = st.columns(3)
                extra["hours"] = c1.number_input("Hours", value=12.0, step=1.0, key="f_h")
                extra["amount"] = c2.text_input("Amount", money(1200, client.get("currency", "USD")), key="f_m")
                extra["schedule_impact"] = c3.text_input("Schedule impact", "adds 2 working days", key="f_si")
                extra["reason"] = st.text_input("Reason", "This sits outside the signed scope.", key="f_r")
            elif kind == "project_update":
                c1, c2 = st.columns(2)
                extra["project"] = c1.text_input("Project", "Q4 sprint", key="f_p")
                extra["progress"] = c2.number_input("Progress %", 0, 100, 60, key="f_pg")
                extra["shipped"] = "\n".join("· " + line for line in st.text_area("Shipped (one per line)", "Content calendar\nPaid audit", height=70, key="f_sh").splitlines() if line.strip())
                extra["next"] = "\n".join("· " + line for line in st.text_area("Next (one per line)", "Podcast pilot\nPerformance review", height=70, key="f_nx").splitlines() if line.strip())
                extra["asks"] = "\n".join("· " + line for line in st.text_area("Asks (one per line)", "Approve month-3 batch", height=70, key="f_ak").splitlines() if line.strip())
                extra["status_line"] = ""

    subject, body = comms.render(kind, client, extra, lang)
    draft_surface(subject, body, key=f"compose_{client_id}_{kind}_{lang}", filename=f"{client_id}_{kind}", language=lang)
    c1, c2 = st.columns(2)
    if c1.button("Log as sent", width="stretch", key=f"compose_log_{client_id}_{kind}"):
        service.log_communication(client_id, {"date": today.isoformat(), "channel": "email", "direction": "out",
                                              "subject": subject, "summary": body.split("\n")[0][:200]})
        toast("Logged as sent")
        st.rerun()
    if kind.startswith("proposal") and c2.button("Move client to Proposal Sent", width="stretch", key="compose_stage"):
        service.set_stage(client_id, "Proposal Sent", float(client.get("deal_value", 0) or 0))
        toast("Stage moved")
        st.rerun()


def _summariser() -> None:
    st.markdown("### Thread summariser")
    st.caption("Paste the thread — emails, WhatsApp, call notes. MIM pulls the decisions, the open questions and the next step.")
    text = st.text_area("Thread", height=260, key="thread_text",
                        placeholder="Paste raw messages here, one per line or broken up however you have them.")
    if st.button("Summarise", type="primary", key="summarise_btn"):
        if not text.strip():
            st.error("Nothing to read.")
            return
        result = comms.summarise_thread(text)
        st.session_state["thread_result"] = result
    result = st.session_state.get("thread_result")
    if not result:
        return
    st.markdown(f'**Headline** — {result["headline"]}')
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Decisions**")
        st.markdown("\n".join(f"· {d}" for d in result["decisions"]) or "· none")
        st.markdown("**Open questions**")
        st.markdown("\n".join(f"· {q}" for q in result["questions"]) or "· none")
    with c2:
        st.markdown("**Commitments**")
        st.markdown("\n".join(f"· {c}" for c in result["commitments"]) or "· none")
        st.markdown("**Dates & money detected**")
        st.markdown("\n".join(f"· {d}" for d in (result["dates"] + result["money"])) or "· none")
    st.markdown(f'<div class="mim-move"><div class="mv-head">▶ NEXT MOVE — {result["next_step"]}</div>'
                f'<div class="mv-meta">{result["stats"]["lines"]} lines read · '
                f'{result["stats"]["questions"]} questions · {result["stats"]["decisions"]} decisions</div></div>',
                unsafe_allow_html=True)
