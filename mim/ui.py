"""Shared UI kit for the MIM console: theme, cards, pills, tables, composers.

Visual language: deep charcoal, one gold accent, no decoration that isn't data.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Iterable

import pandas as pd
import streamlit as st

from .models import money, pct

GOLD = "#E9B949"
INK = "#0A0D11"
TONE = {
    "good": "#2FBF71",
    "warn": "#E9B949",
    "bad": "#E4572E",
    "info": "#5AA9E6",
    "muted": "#7C8794",
}


# ---------------------------------------------------------------- theme

def inject_theme() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background:
              radial-gradient(1100px 520px at 12% -12%, #14202b 0%, rgba(10,13,17,0) 62%),
              radial-gradient(900px 480px at 96% 4%, #1a160c 0%, rgba(10,13,17,0) 58%),
              #0A0D11;
        }}
        section[data-testid="stSidebar"] {{
            background: #0D1218;
            border-right: 1px solid #1B232C;
        }}
        h1, h2, h3 {{ letter-spacing: -0.02em; }}
        .mim-wordmark {{
            font-size: 1.45rem; font-weight: 800; letter-spacing: 0.28em;
            color: {GOLD}; margin: 0 0 .1rem 0;
        }}
        .mim-sub {{ font-size: .72rem; letter-spacing: .18em; color: #7C8794;
            text-transform: uppercase; margin-bottom: 1.1rem; }}
        .mim-card {{
            background: linear-gradient(180deg, #111823 0%, #0D131A 100%);
            border: 1px solid #1E2733; border-radius: 14px;
            padding: 14px 16px 12px 16px; height: 100%;
        }}
        .mim-card .kpi-label {{ font-size: .68rem; letter-spacing: .14em;
            text-transform: uppercase; color: #8A97A6; margin-bottom: 6px; }}
        .mim-card .kpi-value {{ font-size: 1.5rem; font-weight: 700; color: #F3F6F9;
            line-height: 1.1; }}
        .mim-card .kpi-note {{ font-size: .74rem; color: #8A97A6; margin-top: 6px; }}
        .mim-card.accent {{ border-color: #3A2F14;
            background: linear-gradient(180deg, #1B1710 0%, #12100B 100%); }}
        .mim-card.accent .kpi-value {{ color: {GOLD}; }}
        .mim-move {{
            background: linear-gradient(180deg, #1A1508 0%, #100E09 100%);
            border: 1px solid #4A3A12; border-left: 4px solid {GOLD};
            border-radius: 12px; padding: 13px 16px; margin-bottom: 10px;
        }}
        .mim-move .mv-head {{ font-weight: 700; color: #FAF3E0; font-size: 1.02rem; }}
        .mim-move .mv-meta {{ color: #B9A46B; font-size: .8rem; margin-top: 4px; }}
        .mim-move .mv-where {{ color: #8A97A6; font-size: .72rem;
            letter-spacing: .12em; text-transform: uppercase; margin-top: 7px; }}
        .mim-pill {{ display: inline-block; padding: 2px 9px; border-radius: 999px;
            font-size: .68rem; font-weight: 700; letter-spacing: .06em;
            text-transform: uppercase; border: 1px solid; }}
        .mim-rule {{ height: 1px; background: #1B232C; margin: 14px 0 18px 0; }}
        .mim-note {{ color: #8A97A6; font-size: .8rem; }}
        div[data-testid="stDataFrame"] {{ border: 1px solid #1B232C; border-radius: 12px; }}
        .stButton > button {{
            border-radius: 10px; border: 1px solid #2A3542; background: #131A23;
            color: #E8EDF3; font-weight: 600;
        }}
        .stButton > button:hover {{ border-color: {GOLD}; color: {GOLD}; }}
        .stDownloadButton > button {{ border-radius: 10px; }}
        code {{ color: #E9B949; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def wordmark(subtitle: str) -> None:
    st.markdown(f'<div class="mim-wordmark">MIM</div><div class="mim-sub">{subtitle}</div>', unsafe_allow_html=True)


def rule() -> None:
    st.markdown('<div class="mim-rule"></div>', unsafe_allow_html=True)


def pill(text: str, tone: str = "muted") -> str:
    color = TONE.get(tone, TONE["muted"])
    return f'<span class="mim-pill" style="color:{color};border-color:{color}44;background:{color}14">{text}</span>'


def pill_for(value: str, kind: str) -> str:
    """Colour a status string by what it means, not by what it says."""
    tone = {
        "stage": {"Active": "good", "Completed": "info", "Upsell": "warn", "Proposal Sent": "info",
                  "Contacted": "muted", "Lead": "muted"}.get(value, "muted"),
        "risk": {"Delivered": "good", "On Track": "good", "At Risk": "warn", "Critical": "bad",
                 "No Deadline": "muted"}.get(value, "muted"),
        "band": {"Healthy": "good", "Watch": "warn", "At Risk": "bad", "Critical": "bad"}.get(value, "muted"),
        "invoice": {"paid": "good", "sent": "info", "partial": "warn", "overdue": "bad",
                    "draft": "muted", "void": "muted"}.get(value, "muted"),
        "approval": {"approved": "good", "pending": "warn", "changes requested": "bad",
                     "none": "muted"}.get(value, "muted"),
        "task": {"Done": "good", "In Progress": "info", "In Review": "info", "Blocked": "bad",
                 "Not Started": "muted"}.get(value, "muted"),
        "severity": {"High": "bad", "Medium": "warn", "Low": "muted", "Critical": "bad", "Warning": "warn"}.get(value, "muted"),
        "co": {"Draft": "muted", "Sent": "info", "Approved": "warn", "Declined": "bad", "Billed": "good"}.get(value, "muted"),
    }.get(kind, "muted")
    return pill(value, tone)


# ---------------------------------------------------------------- KPIs

def kpi_row(cards: list[dict]) -> None:
    """cards: [{label, value, note, accent(bool), tone}]"""
    cols = st.columns(len(cards), gap="small")
    for col, card in zip(cols, cards):
        cls = "mim-card accent" if card.get("accent") else "mim-card"
        note = card.get("note", "")
        note_color = TONE.get(card.get("tone", "muted"), TONE["muted"])
        note_html = f'<div class="kpi-note" style="color:{note_color}">{note}</div>' if note else ""
        col.markdown(
            f'<div class="{cls}"><div class="kpi-label">{card.get("label","")}</div>'
            f'<div class="kpi-value">{card.get("value","—")}</div>{note_html}</div>',
            unsafe_allow_html=True,
        )


def next_move_block(moves: list[dict], title: str = "▶ NEXT MOVE") -> None:
    if not moves:
        st.markdown(
            '<div class="mim-move"><div class="mv-head">▶ NEXT MOVE — Book is clean.</div>'
            '<div class="mv-meta">No overdue money, no stalled threads, no at-risk projects.</div>'
            '<div class="mv-where">→ Use the time: book 3 discovery calls</div></div>',
            unsafe_allow_html=True,
        )
        return
    for index, move in enumerate(moves):
        value = f' · <b>{money(move["value"], move.get("currency", "USD"))}</b> at stake' if move.get("value") else ""
        label = title if index == 0 else "▶ NEXT MOVE (2nd)"
        st.markdown(
            f'<div class="mim-move"><div class="mv-head">{label} — {move["move"]}{value}</div>'
            f'<div class="mv-meta">{move["why"]}</div>'
            f'<div class="mv-where">→ {move["where"]}</div></div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------- tables

def frame(rows: Iterable[dict], columns: list[str] | None = None) -> pd.DataFrame:
    rows = list(rows)
    if not rows:
        return pd.DataFrame(columns=columns or [])
    df = pd.DataFrame(rows)
    if columns:
        for col in columns:
            if col not in df.columns:
                df[col] = None
        df = df[columns]
    return arrow_safe(df)


def arrow_safe(df: pd.DataFrame) -> pd.DataFrame:
    """Mixed int/str columns ("9d", "—") break Arrow serialisation. Stringify them."""
    for col in df.columns:
        if df[col].dtype != object:
            continue
        values = df[col].dropna().unique().tolist()
        if len({type(v) for v in values}) > 1:
            df[col] = df[col].astype(str).replace({"None": "", "nan": "", "<NA>": ""})
    return df


def table(rows: Iterable[dict], columns: list[str] | None = None, config: dict | None = None,
          height: int | None = None, key: str | None = None) -> None:
    df = frame(rows, columns)
    if df.empty:
        st.markdown('<div class="mim-note">Nothing on the board.</div>', unsafe_allow_html=True)
        return
    kwargs: dict = {"width": "stretch", "hide_index": True, "column_config": config or {}}
    if height:
        kwargs["height"] = height
    if key:
        kwargs["key"] = key
    st.dataframe(df, **kwargs)


MONEY_COL = lambda label="Amount", currency="USD": st.column_config.NumberColumn(label, format=f"{currency} %.0f")
PCT_COL = lambda label="%": st.column_config.ProgressColumn(label, min_value=0, max_value=100, format="%d%%")


# ---------------------------------------------------------------- draft surface

def draft_surface(subject: str, body: str, key: str, filename: str, language: str = "EN") -> None:
    """Editable draft + downloads. Nothing sends from here — you do."""
    st.markdown(f"**Subject** · `{subject}`")
    st.caption(f"Brand voice · {language} · edit before sending. MIM drafts, you sign.")
    st.text_area("Message body", value=body, height=340, key=f"{key}_body", label_visibility="collapsed")
    edited = st.session_state.get(f"{key}_body", body)
    col1, col2, col3 = st.columns([1, 1, 2])
    col1.download_button("Download .md", data=f"Subject: {subject}\n\n{edited}", file_name=f"{filename}.md",
                         mime="text/markdown", width="stretch", key=f"{key}_md")
    col2.download_button("Download .txt", data=f"Subject: {subject}\n\n{edited}", file_name=f"{filename}.txt",
                         mime="text/plain", width="stretch", key=f"{key}_txt")
    col3.markdown('<div class="mim-note">Copy from the box. Send from your own inbox — no ghost-sending.</div>',
                  unsafe_allow_html=True)


def save_button(label: str, key: str, kind: str = "primary") -> bool:
    return st.button(label, key=key, type=kind, width="stretch")


def toast(message: str, icon: str = "✔") -> None:
    st.toast(message, icon=icon)


def page_footer(book_: dict) -> None:
    """Every page ends the way every MIM response ends: two moves, ranked."""
    from .console import next_moves

    rule()
    st.markdown('<div class="mim-sub" style="margin-bottom:.4rem">Every page ends with the move. No filler.</div>',
                unsafe_allow_html=True)
    next_move_block(next_moves(book_, limit=2))


def pick(label: str, options: list[tuple[str, str]], key: str, index: int = 0,
         allow_empty: bool = False, empty_label: str = "— none —", help: str | None = None) -> str:
    """Selectbox that returns the id, not the label.

    Labels are the option text and must be unique — duplicates get the id appended.
    Avoids st.format_func, which breaks element-tree tooling and headless tests.
    """
    labels: list[str] = []
    mapping: dict[str, str] = {}
    if allow_empty:
        labels.append(empty_label)
        mapping[empty_label] = ""
    for oid, text in options:
        lab = str(text)
        if lab in mapping:
            lab = f"{lab} · {oid}"
        labels.append(lab)
        mapping[lab] = oid
    if not labels:
        return ""
    safe_index = index if 0 <= index < len(labels) else 0
    chosen = st.selectbox(label, labels, index=safe_index, key=key, help=help)
    return mapping.get(chosen, "")
