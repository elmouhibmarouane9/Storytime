"""MIM — MEM Digital's operations console.

Run it:  streamlit run streamlit_app.py
Gated deploy:  set MIM_ACCESS_CODE=<your code> before launching.

Four pillars, one screen: CRM · Invoicing & Finance · Projects · Communications.
"""

from __future__ import annotations

import streamlit as st

from mim import console, finance, i18n, service, store
from mim.ui import inject_theme, page_footer, wordmark
from mim.views import clients_view, comms_view, dashboard, finance_view, invoices_view, projects_view, settings_view

st.set_page_config(page_title="MIM · MEM Digital", page_icon="◆", layout="wide",
                   initial_sidebar_state="expanded")

PAGES = {
    "dashboard": dashboard.render,
    "clients": clients_view.render,
    "invoices": invoices_view.render,
    "finance": finance_view.render,
    "projects": projects_view.render,
    "comms": comms_view.render,
    "settings": settings_view.render,
}


def _is_public_host() -> bool:
    """True when the request did not arrive on localhost — i.e. this is reachable."""
    try:
        host = (st.context.headers.get("Host") or "").split(":")[0].lower()
    except Exception:
        return False
    return bool(host) and host not in ("localhost", "127.0.0.1", "0.0.0.0")


def _warn_if_public_and_unguarded() -> None:
    if service.access_code() or not _is_public_host():
        return
    st.error("**This console is on a public URL with no access code.** Anyone with the link can read "
             "your ledger. Add `MIM_ACCESS_CODE` to the host's environment or secrets and reload.", icon="🚨")


def main() -> None:
    store.bootstrap()
    inject_theme()

    if not service.require_password():
        return

    _warn_if_public_and_unguarded()

    lang = st.session_state.get("console_lang", "EN")
    b = console.book()
    today = store.today()

    with st.sidebar:
        wordmark(i18n.t("tagline", lang))
        keys = i18n.PAGE_KEYS
        labels = i18n.nav_labels(lang)
        chosen = st.radio(i18n.t("nav", lang), labels, key="nav_page", label_visibility="collapsed")
        page = keys[labels.index(chosen)]
        st.markdown("---")
        snap = console.pulse(b, today)
        base = snap["base_currency"]
        st.markdown(
            f'<div class="mim-sub" style="margin-bottom:.5rem">{i18n.t("snapshot", lang)} · {today.isoformat()}</div>'
            f'<div style="font-size:.82rem;line-height:1.9">'
            f'<b style="color:#E9B949">{finance.money(snap["collected_mtd"], base)}</b> {i18n.t("collected", lang)}<br>'
            f'<b style="color:#E4572E">{finance.money(snap["overdue"], base)}</b> {i18n.t("overdue", lang)}<br>'
            f'<b style="color:#E9B949">{snap["projects_at_risk"]}</b> {i18n.t("at_risk", lang)}'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")
        lang = st.selectbox(i18n.t("language", lang), ["EN", "ES", "FR", "AR"],
                            index=["EN", "ES", "FR", "AR"].index(lang), key="console_lang")
        if snap["sample"]:
            st.caption(f'⚠️ {i18n.t("sample", lang)}')
        st.caption("Data: JSON in `data/` · nothing sends itself.")

    PAGES[page]({"book": b, "today": today, "lang": lang})
    page_footer(b)


main()
