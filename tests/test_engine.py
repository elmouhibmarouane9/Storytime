"""Pillar logic: the numbers, the rankings, the flags. No Streamlit involved."""

from datetime import date, timedelta

import pytest

from mim import comms, console, crm, finance, models, projects, service, store

T = date(2026, 10, 5)


def inv(**kw):
    base = {
        "id": "X-1", "client_id": "C-1", "issue_date": "2026-09-01", "due_date": "2026-09-15",
        "currency": "USD", "status": "sent", "tax_rate": 0.0, "discount": 0,
        "items": [{"desc": "Work", "qty": 1, "rate": 1000, "unit": "fixed"}], "payments": [],
    }
    base.update(kw)
    return base


# ---------------------------------------------------------------- ids & money

def test_next_id_counts_up():
    assert models.next_id("C", ["C-001", "C-004", "junk"]) == "C-005"
    assert models.next_id("MEM", ["MEM-2026-001", "MEM-2026-002"], width=3, year=True) == "MEM-2026-003"


def test_money_formatting():
    assert models.money(1234.5, "USD") == "$1,234"
    assert models.money(1234.5, "EUR", 2) == "€1,234.50"
    assert models.money(-50, "USD") == "-$50"


def test_month_series():
    assert models.month_series(date(2026, 11, 15), 3) == ["2026-11", "2026-12", "2027-01"]


def test_add_months_handles_short_months():
    assert models.add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)


# ---------------------------------------------------------------- invoice math

def test_invoice_totals_with_tax_and_discount():
    invoice = inv(items=[{"desc": "A", "qty": 3, "rate": 100}], discount=50, tax_rate=0.10)
    assert finance.invoice_subtotal(invoice) == 300
    assert finance.invoice_total(invoice) == 275.0  # (300-50) * 1.1


def test_balance_and_partial_payment():
    invoice = inv(payments=[{"date": "2026-09-20", "amount": 400}])
    assert finance.invoice_paid(invoice) == 400
    assert finance.invoice_balance(invoice) == 600


def test_effective_status_truth_over_label():
    assert finance.effective_status(inv(), T) == "overdue"
    assert finance.effective_status(inv(status="paid"), T) == "overdue"  # label lies, money talks
    assert finance.effective_status(inv(payments=[{"date": "2026-09-20", "amount": 1000}], status="sent"), T) == "paid"
    # A partly-paid invoice that is also late reads as "overdue" — the lateness is the action.
    assert finance.effective_status(inv(payments=[{"date": "2026-09-20", "amount": 200}]), T) == "overdue"
    assert finance.effective_status(inv(due_date="2026-11-01", payments=[{"date": "2026-09-20", "amount": 200}]), T) == "partial"
    assert finance.effective_status(inv(status="draft", due_date="2026-08-01"), T) == "draft"
    assert finance.effective_status(inv(status="void"), T) == "void"


def test_days_overdue_and_buckets():
    assert finance.days_overdue(inv(due_date="2026-09-15"), T) == 20
    assert finance.days_overdue(inv(due_date="2026-11-01"), T) == 0
    assert finance.aging_bucket(inv(due_date="2026-11-01"), T) == "Current"
    assert finance.aging_bucket(inv(due_date="2026-09-15"), T) == "1-30"
    assert finance.aging_bucket(inv(due_date="2026-09-01"), T) == "31-60"
    assert finance.aging_bucket(inv(due_date="2026-07-15"), T) == "61-90"  # 82 days
    assert finance.aging_bucket(inv(due_date="2026-01-15"), T) == "90+"


def test_reminder_tier_ladder():
    assert finance.reminder_tier(inv(due_date="2026-10-10"), T) == 0
    assert finance.reminder_tier(inv(due_date="2026-10-01"), T) == 1
    assert finance.reminder_tier(inv(due_date="2026-09-20"), T) == 2
    assert finance.reminder_tier(inv(due_date="2026-08-01"), T) == 3


def test_revenue_summary_splits_billed_and_collected():
    invoices = [
        inv(id="A", issue_date="2026-10-01", due_date="2026-10-15", payments=[{"date": "2026-10-02", "amount": 600}]),
        inv(id="B", issue_date="2026-10-02", due_date="2026-10-16"),
        inv(id="C", issue_date="2026-08-01", due_date="2026-08-15"),
        inv(id="D", status="draft", issue_date="2026-10-03"),
    ]
    rev = finance.revenue_summary(invoices, T)
    assert rev["billed_mtd"] == 2000
    assert rev["collected_mtd"] == 600
    assert rev["outstanding"] == 2400
    assert rev["overdue"] == 1000   # invoice C only: A is partly paid but not yet due
    assert rev["draft_value"] == 1000


def test_aging_report_groups_by_client():
    invoices = [
        inv(id="A", client_id="C-1", due_date="2026-09-01"),
        inv(id="B", client_id="C-1", due_date="2026-10-01"),
        inv(id="C", client_id="C-2", due_date="2026-01-01"),
    ]
    clients = [{"id": "C-1", "company": "Acme"}, {"id": "C-2", "company": "Zenith"}]
    rows = {r["client"]: r for r in finance.aging_report(invoices, clients, T)}
    assert rows["Acme"]["31-60"] == 1000
    assert rows["Acme"]["Current"] + rows["Acme"]["1-30"] == 1000
    assert rows["Zenith"]["90+"] == 1000


# ---------------------------------------------------------------- FX

def test_fx_converts_to_base():
    settings = {"currency": "USD", "agency": {"base_currency": "USD"},
                "fx_rates": {"EUR": 1.08, "AED": 0.27}}
    eur = inv(currency="EUR")
    converted = finance.to_base_invoice(eur, settings)
    assert converted["currency"] == "USD"
    assert converted["items"][0]["rate"] == 1080.0
    assert eur["items"][0]["rate"] == 1000  # source untouched
    aed = finance.to_base_client({"currency": "AED", "deal_value": 10000}, settings)
    assert aed["deal_value"] == 2700.0


def test_clean_book_currency_mismatch_is_handled(book):
    base = console.base_book(book)
    assert {i["currency"] for i in base["invoices"]} == {"USD"}


# ---------------------------------------------------------------- CRM

def test_pipeline_summary_weights_by_probability():
    clients = [
        {"stage": "Lead", "deal_value": 1000},
        {"stage": "Proposal Sent", "deal_value": 2000},
        {"stage": "Active", "deal_value": 5000},
    ]
    summary = {s["stage"]: s for s in crm.pipeline_summary(clients)}
    assert summary["Lead"]["weighted"] == 100
    assert summary["Proposal Sent"]["weighted"] == 1000
    assert summary["Active"]["weighted"] == 5000
    assert crm.weighted_pipeline(clients) == 6100


def test_communication_gap_fires_past_cadence():
    settings = {"cadence_days": {"Active": 7}}
    stale = {"id": "C-1", "company": "Stale Co", "stage": "Active", "last_contact": (T - timedelta(days=20)).isoformat()}
    fresh = {"id": "C-2", "company": "Fresh Co", "stage": "Active", "last_contact": (T - timedelta(days=2)).isoformat()}
    gaps = crm.communication_gaps([stale, fresh], settings, T)
    assert [g["client"] for g in gaps] == ["Stale Co"]
    assert gaps[0]["severity"] == "Critical"
    assert gaps[0]["days_silent"] == 20


def test_never_contacted_is_critical():
    gaps = crm.communication_gaps([{"id": "C-9", "company": "Ghost", "stage": "Lead"}], {}, T)
    assert gaps[0]["days_silent"] == 9999
    assert "First touch" in gaps[0]["action"]


def test_health_penalises_overdue_money_and_silence(book):
    settings = book["settings"]
    client = next(c for c in book["clients"] if c["id"] == "C-001")
    healthy = dict(client, last_contact=T.isoformat())
    sick = dict(client, last_contact=(T - timedelta(days=60)).isoformat())
    good = crm.health(healthy, [], [], settings, T)
    bad = crm.health(sick, book["invoices"], book["projects"], settings, T)
    assert good["score"] == 100 and good["band"] == "Healthy"
    assert bad["score"] < 50 and bad["band"] in ("At Risk", "Critical")
    assert any("silent" in reason for reason in bad["reasons"])


def test_win_rate_counts_active_conversions():
    clients = [
        {"stage_history": [{"to": "Active"}, {"to": "Lost"}]},
        {"stage_history": [{"to": "Active"}]},
    ]
    assert crm.win_rate(clients) == 67.0


# ---------------------------------------------------------------- projects

def test_task_and_project_progress_weighted_by_hours():
    project = {"tasks": [
        {"name": "a", "status": "Done", "estimated_hours": 10},
        {"name": "b", "status": "Not Started", "estimated_hours": 10},
    ]}
    assert projects.project_progress(project) == 50.0
    project = {"tasks": [
        {"name": "a", "status": "Done", "estimated_hours": 1},
        {"name": "b", "status": "Not Started", "estimated_hours": 9},
    ]}
    assert projects.project_progress(project) == 10.0


def test_deadline_risk_flags_behind_schedule():
    behind = {"status": "Active", "start": (T - timedelta(days=20)).isoformat(), "due": (T + timedelta(days=10)).isoformat(),
              "tasks": [{"status": "Not Started", "estimated_hours": 10}]}
    assert projects.deadline_risk(behind, T)["status"] == "Critical"

    tracked = {"status": "Active", "start": (T - timedelta(days=30)).isoformat(), "due": (T + timedelta(days=30)).isoformat(),
               "tasks": [{"status": "In Review", "estimated_hours": 10}]}
    assert projects.deadline_risk(tracked, T)["status"] == "On Track"

    finished = {"status": "Active", "start": (T - timedelta(days=30)).isoformat(), "due": (T + timedelta(days=30)).isoformat(),
                "tasks": [{"status": "Done", "estimated_hours": 10}]}
    assert projects.deadline_risk(finished, T)["status"] == "Delivered"

    overdue = {"status": "Active", "start": (T - timedelta(days=60)).isoformat(), "due": (T - timedelta(days=2)).isoformat(),
               "tasks": [{"status": "In Progress", "estimated_hours": 10}]}
    assert projects.deadline_risk(overdue, T)["status"] == "Critical"


def test_scope_flags_catch_creep_and_unbilled_change_orders():
    project = {
        "hourly_rate": 100, "included_revisions": 2,
        "time_entries": [
            {"id": "T1", "hours": 20, "in_scope": True, "invoiced": False, "billable": True},
            {"id": "T2", "hours": 5, "in_scope": False, "invoiced": False, "billable": True},
        ],
        "deliverables": [{"name": "Film", "revisions": 4}],
        "change_orders": [{"id": "CO-1", "title": "Extra", "amount": 900, "status": "Approved"}],
        "tasks": [{"status": "In Progress", "estimated_hours": 10, "logged_hours": 20}],
    }
    kinds = {f["type"] for f in projects.scope_flags(project)}
    assert "Out-of-scope work" in kinds
    assert "Revision overage" in kinds
    assert "Hours over estimate" in kinds
    assert "Approved, unbilled change order" in kinds
    # 5h out of scope (500) + 2 extra revision passes (200) + 15h over the 10h estimate (1500) + approved CO (900)
    assert projects.scope_exposure(project) == 500 + 200 + 1500 + 900


def test_uninvoiced_time_splits_scope():
    project = {"hourly_rate": 100, "time_entries": [
        {"id": "T1", "hours": 3, "in_scope": True, "billable": True},
        {"id": "T2", "hours": 2, "in_scope": False, "billable": True},
        {"id": "T3", "hours": 5, "in_scope": True, "billable": True, "invoiced": True},
    ]}
    info = projects.uninvoiced_time(project)
    assert info["hours"] == 3
    assert info["value"] == 300
    assert info["out_of_scope_hours"] == 2


def test_bill_time_for_client_builds_line_items_and_skips_invoiced():
    project = {"id": "P-1", "client_id": "C-1", "name": "Sprint", "hourly_rate": 100,
               "tasks": [{"id": "T-1", "name": "Design"}],
               "time_entries": [
                   {"id": "E1", "hours": 2, "task_id": "T-1", "in_scope": True, "billable": True},
                   {"id": "E2", "hours": 3, "task_id": "T-1", "in_scope": True, "billable": True},
                   {"id": "E3", "hours": 4, "task_id": "T-1", "in_scope": True, "billable": True, "invoiced": True},
                   {"id": "E4", "hours": 9, "task_id": "T-1", "in_scope": False, "billable": True},
               ]}
    items, ids = projects.bill_time_for_client([project], "C-1")
    assert len(items) == 1
    assert items[0]["qty"] == 5
    assert items[0]["desc"] == "Sprint · Design"
    assert ids == ["E1", "E2"]
    assert projects.mark_time_invoiced([project], ids) == 2
    assert [e.get("invoiced", False) for e in project["time_entries"]] == [True, True, True, False]


def test_pending_approvals_ranks_by_waiting_time():
    project = {"id": "P-1", "name": "Launch", "client_id": "C-1", "deliverables": [
        {"name": "A", "approval": {"state": "pending", "requested": (T - timedelta(days=9)).isoformat()}},
        {"name": "B", "approval": {"state": "approved"}},
    ]}
    rows = projects.pending_approvals([project], [{"id": "C-1", "company": "Acme"}], T)
    assert len(rows) == 1
    assert rows[0]["waiting_days"] == 9
    assert rows[0]["chase"] == "Second chase"


# ---------------------------------------------------------------- forecast

def test_cash_flow_forecast_weights_and_covers_target():
    clients = [
        {"id": "R", "company": "Retainer Co", "stage": "Active", "tags": ["retainer"],
         "deal_value": 12000, "currency": "USD"},
        {"id": "P", "company": "Proposal Co", "stage": "Proposal Sent", "deal_value": 10000,
         "currency": "USD", "expected_close": "2026-11-10"},
    ]
    invoices = [inv(id="A", client_id="R", due_date="2026-10-20"),
                inv(id="B", client_id="R", due_date="2026-09-01")]
    settings = {"currency": "USD", "agency": {"base_currency": "USD"},
                "targets": {"monthly_revenue": 3000}, "fx_rates": {}}
    rows = finance.cash_flow_forecast(invoices, clients, settings, T, 3)
    assert rows[0]["recurring"] == 1000          # 12000 / 12
    assert rows[0]["invoices"] == pytest.approx(1850)   # 1000 overdue x 0.90 + 1000 due x 0.95
    assert rows[1]["pipeline"] == 5000           # 10000 x 50%
    assert rows[2]["expected"] == pytest.approx(1000)
    assert finance.pipeline_covered_ratio(rows) is not None


def test_forecast_note_when_short():
    settings = {"agency": {"base_currency": "USD"}, "targets": {"monthly_revenue": 10000}}
    rows = [{"month": "Oct 2026", "expected": 1000, "gap": 9000, "target": 10000}]
    assert "under target" in finance.forecast_notes(rows, settings)[0]


# ---------------------------------------------------------------- comms

@pytest.mark.parametrize("kind", [k for k, _ in comms.kinds()])
def test_every_template_renders_in_both_languages(kind):
    client = {"name": "Daniel Voss", "company": "Nordwind Media", "currency": "USD"}
    for lang in ("EN", "ES"):
        subject, body = comms.render(kind, client, {"days": 5, "invoice": "MEM-1", "amount": "$4,800"}, lang)
        assert subject and body
        assert "{" not in subject and "}" not in subject
        assert "{" not in body and "}" not in body


def test_spanish_template_actually_spanish():
    subject, body = comms.render("proposal_nudge", {"company": "Casa Ferrer", "name": "Lucía"}, {"days": 16}, "ES")
    assert "propuesta" in subject.lower()
    assert "días" in body


def test_reminder_tier_selects_escalating_copy():
    invoice = inv(due_date="2026-10-01")  # 4 days late
    subject, _ = comms.reminder_for(invoice, {"company": "Acme"}, T)
    assert "cleared?" in subject or "on the way?" in subject
    invoice = inv(due_date="2026-06-01")  # 126 days late
    subject, body = comms.reminder_for(invoice, {"company": "Acme"}, T)
    assert "final notice" in subject.lower() or "final" in body.lower()


def test_thread_summariser_extracts_signal():
    thread = """Daniel: Can you confirm the Q4 budget by Monday?
We will send the revised scope tomorrow.
Daniel: Approved — let's go.
Invoice MEM-2026-003 is still unpaid, $4,800 due 2026-08-03.
"""
    result = comms.summarise_thread(thread)
    assert any("Approved" in d for d in result["decisions"])
    assert any("confirm" in q for q in result["questions"])
    assert any("Monday" in d for d in result["dates"])
    assert any("4,800" in m for m in result["money"])
    assert "Confirm in writing" in result["next_step"]


# ---------------------------------------------------------------- console

def test_pulse_reports_the_books_truth(book):
    snap = console.pulse(book, T)
    assert snap["clients"] == 5
    assert snap["overdue"] > 0
    assert snap["projects_at_risk"] >= 1
    assert snap["base_currency"] == "USD"
    assert set(snap["outstanding_by_currency"]) >= {"USD", "EUR", "AED"}


def test_next_moves_are_ranked_and_deduped(book):
    moves = console.next_moves(book, T, limit=10)
    assert moves[0]["score"] >= moves[-1]["score"]
    refs = [m["ref"] for m in moves if m["kind"] in ("comm_gap", "proposal", "upsell", "next_action") and m["ref"]]
    assert len(refs) == len(set(refs)), "one relationship move per client"
    kinds = {m["kind"] for m in moves}
    assert "collection" in kinds


def test_next_move_block_is_two_moves(book):
    text = console.next_move_markdown(book, T)
    assert text.count("▶ **NEXT MOVE**") == 2
    assert "at stake" in text


def test_finance_dashboard_aging_totals_match_rows(book):
    dash = console.finance_dashboard(book, T)
    assert sum(dash["aging_totals"].values()) == pytest.approx(dash["revenue"]["outstanding"], abs=0.02)
    assert len(dash["forecast"]) == 3


def test_client_dashboard_sorts_worst_health_first(book):
    rows = console.client_dashboard(book, T)
    assert rows[0]["health"] <= rows[-1]["health"]
    assert {"company", "stage", "deal_value", "outstanding"} <= set(rows[0])


# ---------------------------------------------------------------- service (writes)

def test_service_crud_cycle(book):
    cid = service.new_client({"name": "Test Person", "company": "Test Co", "stage": "Lead",
                              "deal_value": 5000, "currency": "USD"})
    assert cid.startswith("C-")
    service.set_stage(cid, "Contacted")
    stored = next(c for c in store.load("clients") if c["id"] == cid)
    assert stored["stage"] == "Contacted"
    assert stored["stage_history"][-1]["to"] == "Contacted"

    inv_id = service.create_invoice({"client_id": cid, "items": [{"desc": "Test", "qty": 2, "rate": 500}],
                                     "currency": "USD", "status": "draft", "terms_days": 14})
    service.record_payment(inv_id, 1000)
    stored_inv = next(i for i in store.load("invoices") if i["id"] == inv_id)
    assert stored_inv["status"] == "paid"
    assert finance.invoice_balance(stored_inv) == 0

    mid = service.log_communication(cid, {"subject": "Hi", "summary": "Test", "direction": "out"})
    assert mid.startswith("M-")
    client = next(c for c in store.load("clients") if c["id"] == cid)
    assert client["last_contact"] == store.today().isoformat()


def test_export_then_import_round_trips(book):
    exported = store.dump()
    service.wipe_book(sample=False)
    assert store.load("clients") == []
    written = service.import_book(exported)
    assert written["clients"] == 5
    restored = store.load("clients")
    assert {c["id"] for c in restored} == {"C-001", "C-002", "C-003", "C-004", "C-005"}
    assert store.load("settings")["targets"]["monthly_revenue"] == 18000


def test_import_merge_skips_duplicate_ids(book):
    exported = store.dump()
    written = service.import_book(exported, merge=True)
    assert written["clients"] == 0            # same ids already present
    assert len(store.load("clients")) == 5


def test_import_ignores_unknown_collections(book):
    written = service.import_book({"clients": store.load("clients"), "junk": [1, 2, 3]})
    assert "junk" not in written


def test_storage_health_reports_path_and_writability(book):
    health = service.storage_health()
    assert health["writable"] is True
    assert health["path"].endswith("data") or "mim-test-book" in health["path"]


def test_service_can_reset_to_clean_book(book):
    service.wipe_book(sample=False)
    assert store.load("clients") == []
    assert store.load("invoices") == []
    assert store.load("settings").get("sample_data") is False
    store.bootstrap(force=True)  # restore for other tests
