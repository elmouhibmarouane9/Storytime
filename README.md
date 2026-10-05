# MIM — MEM Digital Operations Console

MIM is the 24/7 COO, CFO and account manager for a one-person agency. It runs the whole
operation from a single screen: **CRM · Invoicing & Finance · Project Tracking · Client
Communications** — and it ends every page the way it ends every conversation:

> **▶ NEXT MOVE** — the two highest-value actions, ranked by money at stake × urgency.

No filler. No dashboards that only report. Every screen tells you what to do next and why.

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

First run seeds a clearly-labelled **sample book** (5 clients, 8 invoices, 4 projects) so every
dashboard is live immediately. Wipe it from **Settings → Book → Start a clean book**.

---

## The four pillars

| Pillar | What it does | Where |
|---|---|---|
| **CRM** | Pipeline board (Lead → Contacted → Proposal Sent → Active → Completed → Upsell), full client files (deal value, comms style, payment behaviour, preferences), 0-100 health scoring with reasons, stage history | `mim/crm.py` · Clients |
| **Invoicing & Finance** | Build invoices with dynamic line items, record payments, ledger with effective status, aging (Current → 90+), collection queue ranked by balance × lateness, tiered reminders, cash-flow forecast, multi-currency with FX to base | `mim/finance.py` · Invoices · Finance |
| **Projects** | Weighted progress, deadline risk vs schedule baseline, deliverables + approval states, time logging, scope-creep detection × 4 flavours, change orders, uninvoiced-time → invoice | `mim/projects.py` · Projects |
| **Comms** | 15 brand-voice templates in EN/ES, tiered payment reminders, approval chases, upsell and change-order drafts, thread summariser that pulls decisions/questions/dates/money, silence radar that flags communication gaps by cadence | `mim/comms.py` · Comms |

## The engine

`mim/console.py` is where everything is judged. `next_moves()` scores every signal in the book —
overdue invoices, parked drafts, approved-but-unbilled change orders, uninvoiced hours, blocked
approvals, at-risk deadlines, scope creep, cold threads, stalled proposals, upsell windows,
missed revenue targets — and returns them ranked, with one relationship move per client, never two.

```
score = money at stake × urgency multiplier
```

Collection urgency scales with lateness tier (soft → firm → final notice). Deadline risk scales with
severity. Every move carries the reason it exists and the screen that fixes it.

## Brand voice

Confident. Cinematic. Direct. Bilingual. Templates are hand-written, not generated: no "just
checking in", no hedging. Each one ends in a decision or a next step.

| Situation | Template | Tone |
|---|---|---|
| Cold lead | `lead_followup` | One idea worth replying to, no ask |
| Proposal sent, silence | `proposal_nudge` | Which is wrong — timing or number? |
| 1-7 days late | `reminder_1` | Admin slip, assume good faith |
| 8-21 days late | `reminder_2` | Firm: confirm a payment date today |
| 22+ days late | `reminder_3` | Formal notice, escalation stated |
| Approval sitting | `approval_chase` | "Reply go or hold. Drift isn't." |

Drafts are **never sent** by MIM. They arrive editable with `.md` / `.txt` / `.html` / `.json`
downloads; you send from your own inbox and hit "Log as sent".

## Data model

Plain JSON in `data/`, one file per collection, written atomically:

```
data/settings.json   agency details, targets, cadence, FX rates, invoice defaults, brand voice
data/clients.json    profiles, stage, stage_history, next_action, negotiation context
data/invoices.json   line items, payments, reminders, status
data/projects.json   tasks, deliverables + approvals, time_entries, change_orders
data/messages.json   every logged touch, with channel, direction and reminder tier
```

`data/` is git-ignored by default — your client data shouldn't live in a repo. Export the full book
as JSON from **Settings → Book** any time.

## Deployment

The console runs anywhere Streamlit runs (Streamlit Community Cloud, a VM, a container).

- **Gate it.** Set `MIM_ACCESS_CODE` and the app asks for a code before rendering anything:
  ```bash
  MIM_ACCESS_CODE=your-code streamlit run streamlit_app.py
  ```
- **Time-travel the forecast** for demos by pinning the clock: `MIM_TODAY=2026-12-01`.
- **Point it at another volume:** `MIM_DATA_DIR=/path/to/book`.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q     # 60 tests
```

- `tests/test_engine.py` — invoice maths, aging buckets, effective status, FX conversion, weighted
  forecasting, health scoring, deadline risk, scope-creep detection, time-to-invoice conversion,
  template rendering in both languages, move ranking and dedupe.
- `tests/test_app.py` — headless render of all seven pages plus the language switch, via Streamlit's
  own `AppTest`. A broken page fails the build.

## Layout

```
streamlit_app.py        router: sidebar, pulse snapshot, page dispatch, next-move footer
mim/
  console.py            aggregation + next-move engine (the brain)
  finance.py            invoice maths, aging, collections, forecast, FX
  crm.py                pipeline, health, cadence, upsell triggers
  projects.py           progress, risk, scope flags, billable time
  comms.py              brand-voice templates EN/ES, reminder tiers, thread summariser
  render.py             invoice → Markdown / print-ready HTML
  service.py            every write path (single audit trail)
  store.py              atomic JSON persistence
  models.py             schema constants, ids, dates, money formatting
  ui.py                 theme, KPI cards, tables, draft surface
  views/                one module per page
```
