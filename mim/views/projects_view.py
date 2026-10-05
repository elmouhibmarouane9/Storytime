"""Projects — progress, deadlines, approvals, time and scope creep."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import streamlit as st

from .. import comms, console, finance, projects, service
from ..models import TASK_STATUS, money
from ..ui import draft_surface, kpi_row, pick, pill_for, rule, table, toast


def render(ctx: dict[str, Any]) -> None:
    b, today = ctx["book"], ctx["today"]
    port = projects.portfolio_summary(b["projects"], today)
    st.markdown("## Projects")
    kpi_row([
        {"label": "Active", "value": port["active"], "note": f'{port["avg_progress"]}% average progress'},
        {"label": "At risk", "value": port["at_risk"], "note": f'{port["critical"]} critical',
         "tone": "bad" if port["critical"] else "warn" if port["at_risk"] else "good"},
        {"label": "Scope exposure", "value": money(port["scope_exposure"]),
         "note": "Unbilled scope + approved change orders", "tone": "warn" if port["scope_exposure"] else "good"},
        {"label": "Unbilled time", "value": money(port["unbilled"]),
         "note": f'{port["unbilled_hours"]}h billable, not invoiced', "tone": "warn" if port["unbilled"] else "good"},
    ])
    rule()

    tab_board, tab_detail, tab_new = st.tabs(["Portfolio", "Project control", "New project"])

    with tab_board:
        rows = projects.portfolio(b["projects"], b["clients"], today)
        table([{"ID": r["id"], "Project": r["project"], "Client": r["client"], "Status": r["status"],
                "Done": f'{r["progress"]:.0f}%', "Due": r["due"],
                "Days": _days_label(r["days_left"]),
                "Risk": r["risk"], "Open tasks": r["open_tasks"], "Hours": r["hours"],
                "Unbilled": r["unbilled"], "Exposure": r["scope_exposure"]} for r in rows],
              config={"Unbilled": st.column_config.NumberColumn("Unbilled", format="%.0f"),
                      "Exposure": st.column_config.NumberColumn("Exposure", format="%.0f")},
              height=300)
        rule()
        st.markdown("### Approvals waiting on the client")
        approvals = projects.pending_approvals(b["projects"], b["clients"], today)
        table([{"Client": r["client"], "Project": r["project"], "Deliverable": r["deliverable"],
                "Requested": r["requested"], "Waiting": f'{r["waiting_days"]}d', "Play": r["chase"]} for r in approvals])
        if not approvals:
            st.markdown('<div class="mim-note">No approvals outstanding.</div>', unsafe_allow_html=True)

    with tab_detail:
        if not b["projects"]:
            st.markdown('<div class="mim-note">No projects yet.</div>', unsafe_allow_html=True)
            return
        options = [(p["id"], f'{p["name"]} · {p.get("status", "")}') for p in b["projects"]]
        pid = pick("Project", options, key="proj_pick")
        project = next(p for p in b["projects"] if p["id"] == pid)
        client = next((c for c in b["clients"] if c["id"] == project.get("client_id")), {})
        risk = projects.deadline_risk(project, today)
        hours = projects.project_hours(project)
        unbilled = projects.uninvoiced_time(project)

        st.markdown(
            f'### {project["name"]} {pill_for(project.get("status", "—"), "task")} {pill_for(risk["status"], "risk")}',
            unsafe_allow_html=True,
        )
        st.markdown(f'<div class="mim-note">{client.get("company", "—")} · due {project.get("due", "—")} · '
                    f'{risk["message"]}</div>', unsafe_allow_html=True)
        kpi_row([
            {"label": "Progress", "value": f'{projects.project_progress(project):.0f}%',
             "note": f'Expected {risk["expected"]}%' if risk.get("expected") is not None else "No schedule baseline"},
            {"label": "Hours", "value": f'{hours["logged"]}/{hours["estimated"]}',
             "note": f'Burn {hours["burn_pct"]:.0f}% · value {money(hours["logged_value"], project.get("currency", "USD"))}',
             "tone": "warn" if hours["burn_pct"] > 100 else "good"},
            {"label": "Unbilled", "value": money(unbilled["value"], project.get("currency", "USD")),
             "note": f'{unbilled["hours"]}h billable', "tone": "warn" if unbilled["value"] else "good"},
            {"label": "Scope exposure", "value": money(projects.scope_exposure(project), project.get("currency", "USD")),
             "note": f'{len(projects.scope_flags(project))} flag(s)', "tone": "bad" if projects.scope_exposure(project) else "good"},
        ])
        rule()

        tab_tasks, tab_deliv, tab_time, tab_scope = st.tabs(["Tasks", "Deliverables & approvals", "Time", "Scope & change orders"])

        with tab_tasks:
            _task_editor(project)

        with tab_deliv:
            rows = projects.deliverable_rows(project, today)
            table([{"Deliverable": r["deliverable"], "Status": r["status"], "Due": r["due"],
                    "Approval": r["approval"], "Waiting": f'{r["waiting"]}d' if r["waiting"] is not None else "—"} for r in rows])
            st.markdown("**Approval controls**")
            deliverable_names = [d["name"] for d in project.get("deliverables", [])]
            if deliverable_names:
                c1, c2, c3 = st.columns([2, 1, 1])
                target = c1.selectbox("Deliverable", deliverable_names, key=f"appr_{pid}")
                state = c2.selectbox("Set state", ["pending", "approved", "changes requested", "none"], key=f"appr_state_{pid}")
                if c3.button("Apply", width="stretch", key=f"appr_apply_{pid}"):
                    service.set_approval(pid, target, state, today.isoformat())
                    toast(f"{target} → {state}")
                    st.rerun()
                if state == "pending":
                    subject, body = comms.render("approval_request", client, {
                        "deliverable": target, "link": "[link]", "deadline": (today + timedelta(days=2)).isoformat(),
                    }, client.get("language", "EN"))
                    draft_surface(subject, body, key=f"appr_draft_{pid}_{target}", filename=f"approval_{pid}", language=client.get("language", "EN"))

        with tab_time:
            entries = sorted(project.get("time_entries", []), key=lambda e: e.get("date", ""), reverse=True)
            table([{"Date": e.get("date"), "Task": e.get("task_id", "—"), "Hours": e.get("hours", 0),
                    "Note": e.get("note", ""), "In scope": e.get("in_scope", True),
                    "Billable": e.get("billable", True), "Invoiced": e.get("invoiced", False)} for e in entries],
                  config={"Hours": st.column_config.NumberColumn("Hours", format="%.1f")})
            with st.expander("Log time"):
                with st.form(f"time_{pid}"):
                    c1, c2, c3 = st.columns(3)
                    when = c1.date_input("Date", today, key=f"tdate_{pid}")
                    task_ids = [t["id"] for t in project.get("tasks", [])] or [""]
                    task_pick = c2.selectbox("Task", task_ids, key=f"ttask_{pid}")
                    hrs = c3.number_input("Hours", value=1.0, step=0.5, min_value=0.0, key=f"thrs_{pid}")
                    c1, c2 = st.columns(2)
                    in_scope = c1.checkbox("In signed scope", value=True, key=f"tscope_{pid}")
                    billable = c2.checkbox("Billable", value=True, key=f"tbill_{pid}")
                    note = st.text_input("Note", key=f"tnote_{pid}")
                    if st.form_submit_button("Log it", width="stretch"):
                        service.log_time(pid, {"date": when.isoformat(), "task_id": task_pick, "hours": hrs,
                                               "note": note, "in_scope": in_scope, "billable": billable})
                        toast(f"{hrs}h logged")
                        st.rerun()

        with tab_scope:
            flags = projects.scope_flags(project)
            if flags:
                table([{"Flag": f["type"], "Detail": f["detail"], "Exposure": f["exposure"],
                        "Severity": f["severity"], "Play": f["action"]} for f in flags],
                      config={"Exposure": st.column_config.NumberColumn("Exposure", format="%.0f")})
                top = flags[0]
                subject, body = comms.change_order_from_flag(project, top, client, b["settings"], client.get("language", "EN"))
                st.markdown("#### Change order draft")
                draft_surface(subject, body, key=f"co_{pid}_{top['type']}", filename=f"change_order_{pid}", language=client.get("language", "EN"))
                c1, c2 = st.columns(2)
                if c1.button("Create change order from this flag", width="stretch", key=f"co_create_{pid}"):
                    coid = service.create_change_order(pid, {
                        "title": top["type"], "amount": top["exposure"],
                        "hours": round(top["exposure"] / (project.get("hourly_rate") or 1), 1),
                        "status": "Draft",
                    })
                    toast(f"{coid} drafted")
                    st.rerun()
            else:
                st.markdown('<div class="mim-note">Scope is clean. Hours inside estimate, no extra revisions.</div>',
                            unsafe_allow_html=True)

            st.markdown("#### Change orders")
            orders = project.get("change_orders", [])
            table([{"ID": co.get("id"), "Title": co.get("title"), "Amount": co.get("amount"),
                    "Hours": co.get("hours"), "Status": co.get("status"), "Date": co.get("date")} for co in orders],
                  config={"Amount": st.column_config.NumberColumn("Amount", format="%.0f"),
                          "Hours": st.column_config.NumberColumn("Hours", format="%.1f")})
            if orders:
                c1, c2, c3 = st.columns([2, 1, 1])
                co_id = c1.selectbox("Change order", [c["id"] for c in orders], key=f"co_pick_{pid}")
                status = c2.selectbox("Status", ["Draft", "Sent", "Approved", "Declined", "Billed"], key=f"co_status_{pid}")
                if c3.button("Update", width="stretch", key=f"co_upd_{pid}"):
                    service.set_change_order_status(pid, co_id, status)
                    toast(f"{co_id} → {status}")
                    st.rerun()
                if status == "Approved":
                    co = next(c for c in orders if c["id"] == co_id)
                    if st.button(f'Invoice {co_id} ({money(co.get("amount", 0), project.get("currency", "USD"))})',
                                 key=f"co_inv_{pid}", width="stretch"):
                        inv_id = service.create_invoice({
                            "client_id": project.get("client_id"), "project_id": pid,
                            "items": [{"desc": f'{co.get("title")} ({co_id})', "qty": 1,
                                       "rate": co.get("amount", 0), "unit": "fixed"}],
                            "currency": project.get("currency"), "notes": f"Change order {co_id}",
                            "status": "draft",
                        })
                        service.set_change_order_status(pid, co_id, "Billed")
                        toast(f"{inv_id} drafted for {co_id}")
                        st.session_state["last_invoice"] = inv_id
                        st.rerun()

            st.markdown("#### Project terms")
            with st.form(f"terms_{pid}"):
                c1, c2, c3 = st.columns(3)
                due = c1.date_input("Deadline", finance.parse_date(project.get("due")) or today, key=f"pd_{pid}")
                budget = c2.number_input("Budget", value=float(project.get("budget", 0) or 0), step=500.0, key=f"pb_{pid}")
                rate = c3.number_input("Hourly rate", value=float(project.get("hourly_rate", 0) or 0), step=5.0, key=f"pr_{pid}")
                c1, c2 = st.columns(2)
                status = c1.selectbox("Status", ["Active", "In Review", "Completed", "On Hold", "Delivered"],
                                      index=["Active", "In Review", "Completed", "On Hold", "Delivered"].index(project.get("status", "Active"))
                                      if project.get("status") in ("Active", "In Review", "Completed", "On Hold", "Delivered") else 0,
                                      key=f"ps_{pid}")
                revisions = c2.number_input("Included revisions", value=int(project.get("included_revisions", 2) or 2),
                                            min_value=0, step=1, key=f"prev_{pid}")
                scope = st.text_area("Signed scope (used to judge creep)", project.get("scope_summary", ""), height=80, key=f"psc_{pid}")
                if st.form_submit_button("Save project terms", width="stretch"):
                    service.update_project(pid, {"due": due.isoformat(), "budget": budget, "hourly_rate": rate,
                                                 "status": status, "included_revisions": revisions, "scope_summary": scope})
                    toast("Project updated")
                    st.rerun()

    with tab_new:
        _new_project(b, today)


def _days_label(days: int | None) -> str:
    if days is None:
        return "—"
    return f"{days}d left" if days >= 0 else f"{abs(days)}d late"


def _task_editor(project: dict) -> None:
    pid = project["id"]
    tasks = project.get("tasks", [])
    if tasks:
        table([{"ID": t["id"], "Task": t["name"], "Status": t["status"],
                "Done": f'{projects.task_progress(t):.0f}%', "Due": t.get("due", "—"),
                "Est": t.get("estimated_hours", 0), "Logged": t.get("logged_hours", 0)} for t in tasks],
              config={"Est": st.column_config.NumberColumn("Est h", format="%.1f"),
                      "Logged": st.column_config.NumberColumn("Logged h", format="%.1f")})
        with st.expander("Update a task"):
            with st.form(f"task_{pid}"):
                task_ids = [t["id"] for t in tasks]
                c1, c2 = st.columns(2)
                with c1:
                    task_pick = pick("Task", [(t["id"], t["name"]) for t in tasks], key=f"task_pick_{pid}")
                status = c2.selectbox("Status", TASK_STATUS)
                progress = st.slider("Progress %", 0, 100, 0, step=5)
                c1, c2 = st.columns(2)
                est = c1.number_input("Estimated hours", value=0.0, step=0.5)
                logged = c2.number_input("Logged hours", value=0.0, step=0.5)
                if st.form_submit_button("Save task", width="stretch"):
                    service.update_task(pid, task_pick, {"status": status, "progress": progress,
                                                         "estimated_hours": est, "logged_hours": logged})
                    toast("Task updated")
                    st.rerun()
    else:
        st.markdown('<div class="mim-note">No tasks on this project yet.</div>', unsafe_allow_html=True)


def _new_project(b: dict, today: date) -> None:
    st.markdown("### New project")
    if not b["clients"]:
        st.markdown('<div class="mim-note">Add a client first.</div>', unsafe_allow_html=True)
        return
    options = console.client_options(b)
    with st.form("new_project"):
        c1, c2, c3 = st.columns([2, 1, 1])
        name = c1.text_input("Project name*")
        with c2:
            client_id = pick("Client", options, key="new_proj_client")
        currency = c3.selectbox("Currency", ["USD", "EUR", "GBP", "AED", "MAD", "MXN"])
        c1, c2, c3 = st.columns(3)
        start = c1.date_input("Start", today)
        due = c2.date_input("Deadline", today + timedelta(days=30))
        budget = c3.number_input("Budget", value=0.0, step=500.0)
        c1, c2 = st.columns(2)
        rate = c1.number_input("Hourly rate", value=0.0, step=5.0)
        revisions = c2.number_input("Included revisions", value=2, min_value=0, step=1)
        scope = st.text_area("Signed scope", height=80, placeholder="What is explicitly included. Vague scope is how you get robbed.")
        if st.form_submit_button("Create project", width="stretch"):
            if not name.strip():
                st.error("Project name required.")
            else:
                pid = service.create_project({
                    "client_id": client_id, "name": name, "start": start.isoformat(), "due": due.isoformat(),
                    "budget": budget, "currency": currency, "hourly_rate": rate,
                    "included_revisions": revisions, "scope_summary": scope,
                })
                toast(f"{pid} created")
                st.rerun()
