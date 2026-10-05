"""Settings — the operating rules: agency details, targets, cadence, FX, invoice defaults."""

from __future__ import annotations

import json
from typing import Any

import streamlit as st

from .. import service, store
from ..models import STAGES
from ..ui import kpi_row, rule, table, toast


def render(ctx: dict[str, Any]) -> None:
    b = ctx["book"]
    settings = b["settings"]
    agency = settings.get("agency") or {}
    invoice_cfg = settings.get("invoice") or {}
    targets = settings.get("targets") or {}
    cadence = settings.get("cadence_days") or {}

    st.markdown("## Settings")
    gate = service.access_code()
    if gate:
        st.success(f"Access gate armed — {len(gate)}-character code required to open the console.", icon="🔐")
    else:
        st.warning("**No access code set.** Anyone with this URL sees your ledger. Set `MIM_ACCESS_CODE` "
                   "(or `MIM_ACCESS_CODE` in Streamlit secrets) before this runs anywhere public.", icon="🚨")
    if settings.get("sample_data"):
        st.warning("This book is sample data. Load in your real clients, then hit **Start a clean book** below.", icon="⚠️")

    kpi_row([
        {"label": "Clients", "value": len(b["clients"])},
        {"label": "Invoices", "value": len(b["invoices"])},
        {"label": "Projects", "value": len(b["projects"])},
        {"label": "Logged messages", "value": len(b["messages"])},
    ])
    rule()

    tab_agency, tab_rules, tab_book = st.tabs(["Agency", "Operating rules", "Book"])

    with tab_agency:
        with st.form("agency"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Agency name", agency.get("name", "MEM Digital"))
            owner = c2.text_input("Owner", agency.get("owner", ""))
            c1, c2 = st.columns(2)
            email = c1.text_input("Email", agency.get("email", ""))
            phone = c2.text_input("Phone", agency.get("phone", ""))
            c1, c2 = st.columns(2)
            website = c1.text_input("Website", agency.get("website", ""))
            tax_id = c2.text_input("Tax ID", agency.get("tax_id", ""))
            address = st.text_input("Address / service area", agency.get("address", ""))
            base_currency = st.selectbox("Base currency (all reporting)", ["USD", "EUR", "GBP", "AED", "MAD", "MXN"],
                                         index=["USD", "EUR", "GBP", "AED", "MAD", "MXN"].index(agency.get("base_currency", settings.get("currency", "USD"))))
            voice = st.text_area("Brand voice", settings.get("brand_voice", ""), height=70)
            if st.form_submit_button("Save agency", width="stretch"):
                service.update_settings({
                    "agency": {"name": name, "owner": owner, "email": email, "phone": phone, "website": website,
                               "tax_id": tax_id, "address": address, "base_currency": base_currency},
                    "brand_voice": voice,
                })
                toast("Agency saved")
                st.rerun()

    with tab_rules:
        st.markdown("### Targets")
        with st.form("targets"):
            c1, c2 = st.columns(2)
            monthly = c1.number_input("Monthly revenue target", value=float(targets.get("monthly_revenue", 0) or 0), step=500.0)
            quarterly = c2.number_input("Quarterly target", value=float(targets.get("quarterly_revenue", 0) or 0), step=1000.0)
            if st.form_submit_button("Save targets", width="stretch"):
                service.update_settings({"targets": {"monthly_revenue": monthly, "quarterly_revenue": quarterly}})
                toast("Targets saved")
                st.rerun()

        rule()
        st.markdown("### Contact cadence")
        st.caption("Days allowed between touches, per stage. Blow through it and the account shows up in the Silence radar.")
        with st.form("cadence"):
            cols = st.columns(len(STAGES))
            values = {}
            for col, stage in zip(cols, STAGES):
                values[stage] = col.number_input(stage, value=int(cadence.get(stage, 7) or 7), min_value=1, max_value=120)
            if st.form_submit_button("Save cadence", width="stretch"):
                service.update_settings({"cadence_days": values})
                toast("Cadence saved")
                st.rerun()

        rule()
        st.markdown("### Invoice defaults")
        with st.form("invoice_cfg"):
            c1, c2, c3 = st.columns(3)
            prefix = c1.text_input("Invoice prefix", invoice_cfg.get("prefix", "MEM"))
            terms = c2.text_input("Default terms", invoice_cfg.get("default_terms", "Net 14"))
            tax = c3.number_input("Default tax %", value=float(invoice_cfg.get("tax_rate", 0) or 0) * 100, step=0.5)
            if st.form_submit_button("Save invoice defaults", width="stretch"):
                service.update_settings({"invoice": {"prefix": prefix, "default_terms": terms, "tax_rate": tax / 100.0,
                                                     "next_number": invoice_cfg.get("next_number", 1)}})
                toast("Invoice settings saved")
                st.rerun()

        rule()
        st.markdown("### FX rates (to base currency)")
        st.caption("Used for every cross-currency total. Update when the market moves.")
        rates = settings.get("fx_rates") or {}
        with st.form("fx"):
            cols = st.columns(3)
            fields = {}
            for index, cur in enumerate(["USD", "EUR", "GBP", "AED", "MAD", "MXN"]):
                fields[cur] = cols[index % 3].number_input(f"{cur}", value=float(rates.get(cur, 1.0)), step=0.01, format="%.3f")
            if st.form_submit_button("Save rates", width="stretch"):
                service.update_settings({"fx_rates": fields})
                toast("Rates saved")
                st.rerun()

        rule()
        st.markdown("### Reminder policy")
        rows = [{"Tier": f'Tier {r["tier"]}', "Trigger": r["trigger"], "Tone": r["tone"], "Escalation": r["escalation"]}
                for r in settings.get("reminder_policy", [])]
        table(rows)
        st.caption("Tier is computed from days overdue. MIM drafts the copy; you decide when it lands.")

    with tab_book:
        st.markdown("### Where the book lives")
        health = service.storage_health()
        if health["backend"] == "github":
            if health["last_error"]:
                st.error(f'**Sync failing.** {health["last_error"]} Your changes are safe on this server '
                         f'({" · ".join(health["pending_push"]) or "no pending writes"}) and will push on the '
                         f'next successful sync.', icon="🔴")
            else:
                st.success(f'**Synced to your private repo** `{health["repo"]}` ({health["branch"]}/{health["path"]})'
                           + (f' · last push {health["last_sync"]}' if health["last_sync"] else "")
                           + ". Every save is a commit, and every commit is a restore point.", icon="✅")
            st.caption("The book survives restarts, redeploys and host migrations because it lives in Git, "
                       "not in a container disk.")
        else:
            st.caption(f'Stored as JSON in `{health["path"]}` — one file per pillar. Portable, auditable, yours.')
            if not health["writable"]:
                st.error("This filesystem is read-only. Changes will not survive a restart — export the book and "
                         "point MIM_DATA_DIR at a mounted volume.", icon="🔒")
            elif "app" in health["path"] or "tmp" in health["path"]:
                st.warning("Local disk only. On a host with an ephemeral filesystem this book resets on restart — "
                           "connect a private data repo (see `GITHUB_TOKEN` / `MIM_DATA_REPO` in the README) or "
                           "mount a volume at `/app/data`.", icon="📦")

        payload = json.dumps(store.dump(), indent=2)
        c1, c2, c3 = st.columns([1, 1, 1])
        c1.download_button("Export full book (JSON)", payload, file_name="mem_digital_book.json",
                           mime="application/json", width="stretch")
        if health["backend"] == "github" and c3.button("Sync now", width="stretch",
                                                       help="Retry pending pushes, then pull fresh state."):
            after = service.sync_book()
            if after["last_error"]:
                st.error(after["last_error"])
            else:
                toast("Book synced")
                st.rerun()
        upload = c2.file_uploader("Restore from JSON", type=["json"], label_visibility="collapsed")
        if upload is not None:
            c1, c2, c3 = st.columns([1, 1, 2])
            merge = c2.checkbox("Merge instead of replace", value=False,
                                help="Merge appends records with new ids; replace overwrites the whole book.")
            if c1.button("Restore book", type="primary", width="stretch"):
                try:
                    written = service.import_book(json.loads(upload.getvalue().decode("utf-8")), merge=merge)
                except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                    st.error(f"That file is not valid book JSON: {exc}")
                else:
                    summary = " · ".join(f"{count} {name}" for name, count in written.items() if count)
                    toast(f"Restored: {summary or 'nothing found in that file'}")
                    st.rerun()

        rule()
        st.markdown("### Danger zone")
        st.markdown('<div class="mim-note">Wiping is irreversible. Export first if there is anything you love.</div>',
                    unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        if c1.button("Reload sample book", width="stretch"):
            service.wipe_book(sample=True)
            toast("Sample book restored")
            st.rerun()
        confirm = c2.checkbox("I understand", key="wipe_confirm")
        if c2.button("Start a clean book", width="stretch", disabled=not confirm):
            service.wipe_book(sample=False)
            toast("Clean book. Go get clients.")
            st.rerun()

        if st.session_state.get("mim_unlocked"):
            st.success("Session unlocked with access code.")
