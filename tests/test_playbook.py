"""The playbook engine: sourcing, cadence, portfolio, pricing and the approval gate.

The two rules that matter most are tested first — nothing sends, and nothing
runs before a human signs off. Everything else is detail underneath them.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from mim import playbook
from mim.playbook import (
    CAMPAIGN_DAYS,
    LANGUAGES,
    LEAD_COLUMNS,
    NICHES,
    ORGANIC_POSTS,
    PRICING,
    SAMPLE_WORKS,
    ApprovalRequired,
    OfferOutOfRange,
    SampleOverCap,
)

TODAY = date(2026, 10, 10)


@pytest.fixture(autouse=True)
def _clean_playbook_state():
    """Every test starts from an empty tracker and an unapproved checklist.

    `data/playbook.json` survives between tests, so lead ids would otherwise
    keep climbing and a later test would edit an earlier test's lead.
    """
    playbook.save_state({"leads": [], "approvals": playbook.empty_approvals()})
    yield
    playbook.save_state({"leads": [], "approvals": playbook.empty_approvals()})


def a_lead(**over):
    """A lead with enough signal to qualify, on a fixed date."""
    base = dict(
        name="Ane Etxeberria",
        business="Bar Nestor",
        channel="instagram",
        signal="the txuleta board is chalked by hand every morning and never photographed",
        niche="tapas_bars",
        city="San Sebastián",
        language="ES",
        signals_matched=["low_posting", "unanswered", "single_language"],
        lead_date=TODAY,
        existing=[],
    )
    base.update(over)
    return playbook.new_lead(**base)


# ---------------------------------------------------------------- rule 1: nothing sends


def test_the_module_exposes_no_way_to_send_anything():
    """No send, publish, post or schedule function may exist here."""
    forbidden = ("send", "publish", "post_", "schedule_", "deliver", "dispatch", "broadcast")
    offenders = [n for n in dir(playbook) if n.lower().startswith(forbidden)]
    assert offenders == [], f"the playbook must not be able to send: {offenders}"


def test_every_generated_draft_is_unsent_and_gated():
    lead = a_lead()
    for code in LANGUAGES:
        for draft in playbook.outreach_set(lead, code):
            assert draft["status"] == "draft"
            assert draft["requires_approval"] is True
            assert draft["sent"] is False
            assert draft["sent_by_human"] is False
            assert draft["language"] == code


# ---------------------------------------------------------------- rule 2: the approval gate


def test_a_fresh_checklist_has_all_five_points_open():
    rows = playbook.checklist()
    assert len(rows) == 5
    assert [r["step"] for r in rows] == [1, 2, 3, 4, 5]
    assert all(r["done"] is False for r in rows)
    assert playbook.is_ready() is False


def test_campaign_is_refused_while_any_approval_is_missing():
    lead = a_lead()
    with pytest.raises(ApprovalRequired) as blocked:
        playbook.plan_campaign(playbook.empty_approvals(), [lead], TODAY)
    assert len(blocked.value.missing) == 5
    assert "5 approval(s) still open" in str(blocked.value)


def test_campaign_is_refused_when_outreach_covers_only_two_languages():
    approvals = _fully_approved()
    approvals["outreach_drafts"]["languages"] = ["EN", "ES"]   # FR missing
    with pytest.raises(ApprovalRequired) as blocked:
        playbook.plan_campaign(approvals, [a_lead()], TODAY)
    assert [r["key"] for r in blocked.value.missing] == ["outreach_drafts"]


def test_campaign_is_refused_when_a_step_is_missing_from_the_drafts():
    approvals = _fully_approved()
    approvals["outreach_drafts"]["kinds"] = ["first_touch", "day3_reminder"]   # day 7 missing
    with pytest.raises(ApprovalRequired) as blocked:
        playbook.plan_campaign(approvals, [a_lead()], TODAY)
    assert [r["key"] for r in blocked.value.missing] == ["outreach_drafts"]


def test_campaign_plans_but_still_sends_nothing_once_approved():
    approvals = _fully_approved()
    plan = playbook.plan_campaign(approvals, [a_lead()], TODAY)
    assert plan["status"] == "pending_human_send"
    assert plan["sent"] is False
    assert plan["requires_approval"] is True
    assert len(plan["messages"]) == 1
    assert plan["messages"][0]["kind"] == "first_touch"
    assert len(plan["timeline"]) == CAMPAIGN_DAYS
    assert plan["window"] == "2026-10-10 → 2026-10-23"


def test_an_already_messaged_lead_gets_no_new_first_touch():
    approvals = _fully_approved()
    lead = dict(a_lead(), message_sent=True)
    plan = playbook.plan_campaign(approvals, [lead], TODAY)
    assert plan["messages"] == []


def _fully_approved() -> dict:
    approvals = playbook.empty_approvals()
    approvals.update(
        niche="tapas_bars",
        city="San Sebastián",
        outreach_drafts={"approved": True, "kinds": list(playbook.OUTREACH_ORDER),
                         "languages": list(LANGUAGES)},
        pricing={"approved": True, "tiers": ["content_starter", "social_growth"]},
        duration_days=CAMPAIGN_DAYS,
        duration_approved=True,
        start_date="2026-10-10",
        sample_files=["pintxo_reel"],
    )
    return playbook.record_approval(approvals, "niche_city", by="Marouane")


def test_an_approval_needs_the_name_of_the_human_who_gave_it():
    with pytest.raises(playbook.PlaybookError, match="needs the name"):
        playbook.record_approval(playbook.empty_approvals(), "niche_city", by="  ")


def test_an_unknown_checklist_item_is_refused():
    with pytest.raises(playbook.PlaybookError, match="Unknown checklist item"):
        playbook.record_approval(playbook.empty_approvals(), "vibes", by="Marouane")


def test_the_checklist_renders_as_a_reviewable_pr_body():
    body = playbook.checklist_markdown(_fully_approved())
    assert "0 of 5 open" in body
    assert body.count("- [x]") == 5
    assert "[x] **1. Niche and city chosen** — tapas_bars · San Sebastián" in body
    open_body = playbook.checklist_markdown(playbook.empty_approvals())
    assert "5 of 5 open" in open_body
    assert "[ ] **2. Outreach drafts approved**" in open_body


# ---------------------------------------------------------------- step 1: sourcing


def test_there_are_exactly_twenty_niches_and_all_three_languages():
    assert len(NICHES) == 20
    for key, niche in NICHES.items():
        for code in ("en", "es", "fr"):   # trilingual dicts use the lowercase comms.py keys
            assert niche[code].strip(), f"{key} is missing its {code} label"
        assert niche["service"] in playbook.CORE_SERVICES, f"{key} offers something off-catalogue"
    assert len(playbook.niche_options("FR")) == 20


def test_niches_stay_inside_the_core_catalogue():
    for niche in NICHES.values():
        assert niche["service"] not in playbook.EXTRA_OFFERS


def test_the_tracker_has_exactly_the_eight_defined_columns():
    assert LEAD_COLUMNS == ("name", "business", "channel", "signal spotted",
                            "message sent", "date", "reply", "next step")
    rows = playbook.tracker_rows([a_lead()])
    assert list(rows[0]) == list(LEAD_COLUMNS)


def test_the_tracker_csv_and_markdown_carry_the_same_columns():
    leads = [a_lead(), a_lead(name="Jon Ruiz", business="La Cuchara de San Telmo", existing=[a_lead()])]
    csv_text = playbook.tracker_csv(leads)
    assert csv_text.splitlines()[0] == ",".join(LEAD_COLUMNS)
    assert len(csv_text.strip().splitlines()) == 3
    assert playbook.tracker_markdown(leads).splitlines()[0] == "| " + " | ".join(LEAD_COLUMNS) + " |"


def test_a_lead_needs_a_business_name():
    with pytest.raises(playbook.PlaybookError, match="needs a business name"):
        playbook.new_lead(name="Nobody", business="  ", channel="instagram", signal="x")


def test_an_unknown_qualification_signal_is_refused():
    with pytest.raises(playbook.PlaybookError, match="Unknown qualification signal"):
        a_lead(signals_matched=["low_posting", "bad_logo"])


def test_two_matched_criteria_qualify_a_lead_and_three_makes_it_a_priority():
    assert playbook.qualify(a_lead(signals_matched=["low_posting", "unanswered"]))["verdict"] == "qualified"
    assert playbook.qualify(a_lead(signals_matched=["low_posting", "unanswered", "no_booking_link"]))["verdict"] == "priority"
    thin = playbook.qualify(a_lead(signals_matched=["low_posting"]))
    assert thin["verdict"] == "thin"
    assert thin["qualified"] is False


def test_there_are_five_qualification_criteria_in_three_languages():
    assert len(playbook.QUALIFICATION) == 5
    for row in playbook.QUALIFICATION:
        assert all(row[code].strip() for code in ("en", "es", "fr"))


def test_ranking_puts_the_most_gapped_lead_first():
    weak = a_lead(name="Uno", business="Weak", signals_matched=["low_posting"], existing=[])
    strong = a_lead(name="Dos", business="Strong",
                    signals_matched=["low_posting", "unanswered", "no_booking_link", "low_quality"],
                    existing=[weak])
    ranked = playbook.rank_leads([weak, strong])
    assert ranked[0]["business"] == "Strong"


# ---------------------------------------------------------------- step 2: outreach


def test_the_cadence_is_day_0_day_3_and_day_7():
    assert [(k, playbook.OUTREACH[k]["day"]) for k in playbook.OUTREACH_ORDER] == [
        ("first_touch", 0), ("day3_reminder", 3), ("day7_final", 7)
    ]


def test_every_outreach_step_exists_in_all_three_languages():
    for kind in playbook.OUTREACH_ORDER:
        for code in ("en", "es", "fr"):
            assert playbook.OUTREACH[kind][code].strip()


def test_the_first_message_names_a_detail_and_asks_a_question():
    draft = playbook.outreach_draft("first_touch", a_lead(), "ES", {"question": "¿Quién escribe la pizarra cada mañana?"})
    assert "the txuleta board" in draft["body"]          # the specific detail
    assert "¿Quién escribe la pizarra cada mañana?" in draft["body"]
    assert "?" in draft["body"]
    assert draft["language"] == "ES"


def test_the_first_message_does_not_mention_price_or_service():
    body = playbook.outreach_draft("first_touch", a_lead(), "EN", {"question": "Who chalks the board?"})["body"]
    for pitchy in ("€", "price", "package", "month", "proposal"):
        assert pitchy.lower() not in body.lower()


def test_the_day_3_reminder_offers_the_free_sample():
    es = playbook.outreach_draft("day3_reminder", a_lead(), "ES")["body"]
    assert "gratis" in es.lower()
    fr = playbook.outreach_draft("day3_reminder", a_lead(), "FR")["body"]
    assert "gratuite" in fr.lower()


def test_the_day_7_note_closes_the_thread_and_stops():
    en = playbook.outreach_draft("day7_final", a_lead(), "EN")["body"]
    assert "Last note from me" in en
    assert "no follow-up sequence" in en


def test_an_unfilled_slot_blocks_review_readiness():
    draft = playbook.outreach_draft("first_touch", a_lead(), "EN")
    assert draft["ready_for_review"] is False
    assert "question" in draft["unfilled"]


def test_filling_every_slot_makes_the_draft_review_ready():
    draft = playbook.outreach_draft(
        "first_touch", a_lead(), "EN", {"question": "Who chalks the board each morning?"}
    )
    assert draft["unfilled"] == []
    assert draft["ready_for_review"] is True


def test_the_bundle_covers_three_steps_in_three_languages():
    bundle = playbook.outreach_bundle(a_lead())
    assert set(bundle) == set(LANGUAGES)
    assert all(len(bundle[code]) == 3 for code in LANGUAGES)


def test_an_unknown_outreach_step_is_refused():
    with pytest.raises(playbook.PlaybookError, match="Unknown outreach step"):
        playbook.outreach_draft("day14_last_chance", a_lead(), "EN")


# ---------------------------------------------------------------- cadence


def test_followups_are_scheduled_three_and_seven_days_after_first_contact(monkeypatch):
    monkeypatch.setenv("MIM_TODAY", "2026-10-10")
    steps = playbook.followup_schedule(a_lead())
    assert [(s["kind"], s["due"]) for s in steps] == [
        ("first_touch", "2026-10-10"),
        ("day3_reminder", "2026-10-13"),
        ("day7_final", "2026-10-17"),
    ]


def test_a_due_followup_is_reported_on_the_right_day(monkeypatch):
    monkeypatch.setenv("MIM_TODAY", "2026-10-13")
    steps = playbook.followup_schedule(a_lead())
    assert steps[1]["status"] == "due today"
    assert steps[2]["status"] == "scheduled"


def test_a_late_followup_counts_its_days_late(monkeypatch):
    monkeypatch.setenv("MIM_TODAY", "2026-10-20")
    due = playbook.due_followups([a_lead()])
    final = next(row for row in due if row["kind"] == "day7_final")
    assert final["days_late"] == 3
    assert due[0]["days_late"] >= due[-1]["days_late"], "worst first"


def test_closing_a_thread_records_the_decision_without_sending():
    closed = playbook.close_thread(a_lead())
    assert closed["closed"] is True
    assert closed["next_step"].startswith("Closed.")


# ---------------------------------------------------------------- steps 3 and 4: portfolio and campaign


def test_there_are_exactly_five_sample_works():
    assert len(SAMPLE_WORKS) == 5
    assert [w["id"] for w in SAMPLE_WORKS] == [
        "pintxo_reel", "coach_carousel", "candle_copy", "n8n_automation", "multilingual_post",
    ]
    for work in SAMPLE_WORKS:
        assert all(work["title"][code].strip() for code in ("en", "es", "fr"))
        assert work["service"] in playbook.CORE_SERVICES


def test_selecting_samples_moves_them_into_polishing():
    chosen = playbook.select_samples(["pintxo_reel", "n8n_automation"])
    assert [w["id"] for w in chosen] == ["pintxo_reel", "n8n_automation"]
    assert all(w["status"] == "polishing" for w in chosen)


def test_an_unknown_sample_file_is_refused():
    with pytest.raises(playbook.PlaybookError, match="Unknown sample work"):
        playbook.select_samples(["pintxo_reel", "logo_redesign"])


def test_the_free_sample_is_capped_at_one_hour():
    assert playbook.check_sample_cap(0.75) == 0.75
    with pytest.raises(SampleOverCap):
        playbook.check_sample_cap(2.5)


def test_ten_organic_posts_land_inside_the_fourteen_day_window():
    assert len(ORGANIC_POSTS) == 10
    assert all(1 <= post["day"] <= CAMPAIGN_DAYS for post in ORGANIC_POSTS)
    timeline = playbook.campaign_timeline(TODAY)
    assert len(timeline) == CAMPAIGN_DAYS
    assert timeline[0]["date"] == "2026-10-10"
    assert timeline[-1]["date"] == "2026-10-23"
    assert sum(1 for day in timeline if day["organic_post"]) == 10


def test_the_first_two_campaign_days_are_human_gates():
    timeline = playbook.campaign_timeline(TODAY)
    assert timeline[0]["human_gate"] is True
    assert timeline[1]["human_gate"] is True
    assert timeline[2]["human_gate"] is False


def test_the_campaign_summary_counts_replies(monkeypatch):
    monkeypatch.setenv("MIM_TODAY", "2026-10-10")
    leads = [a_lead(), a_lead(name="Jon", business="B side", reply="Yes please", existing=[a_lead()])]
    summary = playbook.campaign_summary(leads, TODAY)
    assert summary["leads"] == 2
    assert summary["replied"] == 1
    assert summary["reply_rate"] == 50.0
    assert summary["name"] == "10 Businesses, 10 Free Posts"


# ---------------------------------------------------------------- step 5: pricing


def test_the_launch_prices_are_the_agreed_numbers():
    prices = {row["id"]: row for row in PRICING}
    assert prices["free_sample"]["setup"] == 0.0 and prices["free_sample"]["monthly"] == 0.0
    assert prices["content_starter"]["monthly"] == 149.0
    assert prices["social_growth"]["monthly"] == 349.0
    assert prices["automation_setup"]["setup"] == 250.0
    assert prices["automation_setup"]["monthly"] == 49.0
    assert playbook.EXTRA_LANGUAGE_MONTHLY == 60.0
    assert playbook.CURRENCY == "EUR"


def test_what_each_tier_includes_is_stated_in_three_languages():
    for row in PRICING:
        for code in ("en", "es", "fr"):
            assert row["includes"][code].strip(), f"{row['id']} is missing its {code} description"


def test_content_starter_quotes_flat_at_149_in_one_language():
    q = playbook.quote("content_starter", languages=1, months=1)
    assert q["setup"] == 0.0 and q["monthly"] == 149.0 and q["total"] == 149.0
    assert q["currency"] == "EUR"


def test_an_extra_language_adds_sixty_a_month():
    q = playbook.quote("social_growth", languages=2, months=1)
    assert q["extra_languages"] == 1
    assert q["monthly"] == 409.0
    assert q["total_display"] == "€409"


def test_three_languages_on_social_growth_over_three_months():
    q = playbook.quote("social_growth", languages=3, months=3)
    assert q["monthly"] == 469.0
    assert q["total"] == 1407.0


def test_automation_setup_charges_the_setup_once_then_monthly_upkeep():
    q = playbook.quote("automation_setup", languages=1, months=6)
    assert q["setup"] == 250.0
    assert q["monthly"] == 49.0
    assert q["first_month"] == 299.0
    assert q["total"] == 250.0 + 49.0 * 6


def test_the_free_sample_costs_nothing_and_refuses_a_second_language():
    assert playbook.quote("free_sample")["total"] == 0.0
    with pytest.raises(playbook.PlaybookError, match="capped at an hour"):
        playbook.quote("free_sample", languages=2)


def test_an_unknown_tier_is_refused():
    with pytest.raises(playbook.PlaybookError, match="Unknown tier"):
        playbook.quote("enterprise_unlimited")


def test_zero_languages_is_refused():
    with pytest.raises(playbook.PlaybookError, match="at least one language"):
        playbook.quote("content_starter", languages=0)


def test_the_reserved_extras_cannot_be_offered():
    assert playbook.assert_core_offer(["ai_content", "automation"]) == ["ai_content", "automation"]
    with pytest.raises(OfferOutOfRange, match="reserved extra"):
        playbook.assert_core_offer(["design"])


def test_an_unknown_service_is_refused():
    with pytest.raises(playbook.PlaybookError, match="Unknown service"):
        playbook.assert_core_offer(["astrology"])


# ---------------------------------------------------------------- closing


def test_the_closing_message_carries_the_goals_the_prospect_named():
    draft = playbook.closing_draft(
        a_lead(), "quiero llenar el local entre semana sin depender de la terraza",
        tier_id="social_growth", languages=2, lang="ES",
        extra={"reason": "Los martes es donde se pierden las mesas.", "first_step": "El primer carrusel sale el lunes."},
    )
    assert draft["language"] == "ES"
    assert "quiero llenar el local entre semana" in draft["body"]
    assert draft["quote"]["monthly"] == 409.0
    assert draft["ready_for_review"] is True


def test_the_closing_message_is_written_in_english_and_spanish_only():
    with pytest.raises(playbook.PlaybookError, match="EN and ES only"):
        playbook.closing_draft(a_lead(), "goals", lang="FR")
    assert playbook.closing_draft(a_lead(), "goals", lang="EN")["language"] == "EN"


def test_a_closing_message_needs_the_prospect_goals_first():
    with pytest.raises(playbook.PlaybookError, match="needs the prospect's own goals"):
        playbook.closing_draft(a_lead(), "   ", lang="ES")


def test_the_closing_draft_is_unsent_and_gated():
    draft = playbook.closing_draft(a_lead(), "goals", lang="ES")
    assert draft["status"] == "draft"
    assert draft["requires_approval"] is True
    assert draft["sent"] is False
    assert "reason" in draft["unfilled"], "a half-written close must not read as ready"


# ---------------------------------------------------------------- review artefacts


def test_the_review_bundle_shows_three_languages_and_the_gaps():
    body = playbook.review_bundle(a_lead())
    for code in LANGUAGES:
        assert f"### {code}" in body
    assert "UNFILLED: question" in body
    assert "MIM does not send" in body


# ---------------------------------------------------------------- persistence


def test_the_lead_tracker_round_trips_through_the_book():
    state = playbook.add_lead(a_lead())
    assert len(state["leads"]) == 1
    assert playbook.load_state()["leads"][0]["business"] == "Bar Nestor"


def test_logging_a_send_records_it_without_claiming_to_have_sent_it(monkeypatch):
    monkeypatch.setenv("MIM_TODAY", "2026-10-10")
    state = playbook.add_lead(a_lead())
    state = playbook.log_sent("L-001")
    lead = state["leads"][0]
    assert lead["message_sent"] is True
    assert lead["date"] == "2026-10-10"
    assert lead["next_step"].startswith("Day 3")


def test_logging_a_send_for_an_unknown_lead_is_refused():
    with pytest.raises(playbook.PlaybookError, match="No lead with id"):
        playbook.log_sent("L-999")


def test_a_saved_book_starts_with_an_empty_checklist():
    playbook.save_state({"leads": [], "approvals": playbook.empty_approvals()})
    assert playbook.is_ready(playbook.load_state()["approvals"]) is False


# ---------------------------------------------------------------- language fallback


def test_an_unknown_language_falls_back_to_english():
    assert playbook.normalize_lang("de") == "EN"
    assert playbook.normalize_lang("fr-FR") == "FR"
    assert playbook.normalize_lang("español") == "ES"
    assert playbook.niche_label("tapas_bars", "fr") == "Bars à tapas et pintxos"


def test_an_unknown_niche_is_refused():
    with pytest.raises(playbook.PlaybookError, match="Unknown niche"):
        playbook.niche_label("nightclubs", "EN")


def test_the_next_lead_id_does_not_collide():
    first = a_lead()
    second = a_lead(business="Ganbara", existing=[first])
    assert (first["id"], second["id"]) == ("L-001", "L-002")


# ---------------------------------------------------------------- status cli


def test_status_reports_the_block_and_exits_nonzero(capsys):
    assert playbook.main(["EN"]) == 1
    printed = capsys.readouterr().out
    assert "BLOCKED — the campaign cannot run" in printed
    assert "## Playbook approval — 5 of 5 open" in printed
    assert "TRACKER — 0 lead(s)" in printed


def test_status_shows_the_tracker_and_due_followups(monkeypatch, capsys):
    monkeypatch.setenv("MIM_TODAY", "2026-10-20")
    playbook.add_lead(dict(a_lead(), message_sent=True))
    printed = playbook.status("EN")
    assert "TRACKER — 1 lead(s)" in printed
    assert "Bar Nestor" in printed
    assert "DUE OR OVERDUE — 2 follow-up(s)" in printed, "day 3 and day 7 are both late by day 10"


def test_status_says_cleared_once_every_approval_is_in(monkeypatch):
    monkeypatch.setenv("MIM_TODAY", "2026-10-10")
    playbook.save_state({"leads": [], "approvals": _fully_approved()})
    assert playbook.main(["EN"]) == 0
    assert "CLEARED — every approval is in" in playbook.status("EN")


def test_the_status_cli_localises(monkeypatch):
    monkeypatch.setenv("MIM_TODAY", "2026-10-10")
    assert "Una des vingt niches" not in playbook.status("FR")
    assert "Nicho y ciudad elegidos" in playbook.status("ES")
    assert "Niche et ville choisis" in playbook.status("FR")


# ---------------------------------------------------------------- per-step send log


def test_a_sent_step_is_never_flagged_as_due_again(monkeypatch):
    monkeypatch.setenv("MIM_TODAY", "2026-10-10")
    playbook.add_lead(a_lead())
    playbook.log_step_sent("L-001", "first_touch")
    monkeypatch.setenv("MIM_TODAY", "2026-10-20")
    steps = {s["kind"]: s["status"] for s in playbook.followup_schedule(playbook.load_state()["leads"][0])}
    assert steps == {"first_touch": "sent", "day3_reminder": "overdue", "day7_final": "overdue"}


def test_logging_each_step_advances_the_next_step(monkeypatch):
    monkeypatch.setenv("MIM_TODAY", "2026-10-10")
    playbook.add_lead(a_lead())
    playbook.log_step_sent("L-001", "first_touch")
    assert playbook.load_state()["leads"][0]["next_step"].startswith("Day 3")
    playbook.log_step_sent("L-001", "day3_reminder")
    assert playbook.load_state()["leads"][0]["next_step"].startswith("Day 7")
    playbook.log_step_sent("L-001", "day7_final")
    assert playbook.load_state()["leads"][0]["next_step"].startswith("Closed.")


def test_message_sent_alone_is_enough_to_stop_the_first_touch_nagging(monkeypatch):
    monkeypatch.setenv("MIM_TODAY", "2026-10-20")
    legacy = dict(a_lead(), message_sent=True)      # imported from an older tracker
    legacy.pop("sent_steps")
    steps = {s["kind"]: s["status"] for s in playbook.followup_schedule(legacy)}
    assert steps["first_touch"] == "sent"


def test_an_unknown_step_cannot_be_logged():
    playbook.add_lead(a_lead())
    with pytest.raises(playbook.PlaybookError, match="Unknown outreach step"):
        playbook.log_step_sent("L-001", "day30_please")


# ---------------------------------------------------------------- per-language detail


def test_a_language_matched_detail_replaces_the_spanish_note():
    lead = a_lead(detail_i18n={
        "en": "the room photos are still from the 2019 refurb",
        "es": "las fotos son de la reforma de 2019",
        "fr": "les photos datent encore de la rénovation de 2019",
    })
    assert "still from the 2019 refurb" in playbook.outreach_draft("first_touch", lead, "EN")["body"]
    assert "reforma de 2019" in playbook.outreach_draft("first_touch", lead, "ES")["body"]
    assert "rénovation de 2019" in playbook.outreach_draft("first_touch", lead, "FR")["body"]


def test_a_spanish_note_never_leaks_into_the_french_message():
    lead = a_lead(detail_i18n={"fr": "les photos datent de la rénovation de 2019"})
    body = playbook.outreach_draft("first_touch", lead, "FR")["body"]
    assert "txuleta" not in body


def test_the_bundle_accepts_a_question_per_language():
    per_lang = {
        "EN": {"question": "How many bookings come straight through your own site?"},
        "ES": {"question": "¿Cuántas reservas os entran por la web?"},
        "FR": {"question": "Combien de réservations passent par votre propre site ?"},
    }
    bundle = playbook.outreach_bundle(a_lead(), per_lang)
    assert "straight through your own site" in bundle["EN"][0]["body"]
    assert "por la web" in bundle["ES"][0]["body"]
    assert "votre propre site" in bundle["FR"][0]["body"]
    assert all(bundle[c][0]["ready_for_review"] for c in LANGUAGES)


def test_a_flat_extra_still_applies_to_every_language():
    bundle = playbook.outreach_bundle(a_lead(), {"question": "Who chalks the board?"})
    assert all("Who chalks the board?" in bundle[c][0]["body"] for c in LANGUAGES)


def test_the_detail_slot_survives_being_a_full_clause():
    """A clause in {detail} must not produce broken grammar in any language."""
    lead = a_lead(detail_i18n={
        "en": "the room photos are still from the 2019 refurb",
        "es": "las fotos son de la reforma de 2019",
        "fr": "les photos datent de la rénovation de 2019",
    })
    assert "What stuck: the room photos are still from the 2019 refurb" in \
        playbook.outreach_draft("first_touch", lead, "EN")["body"]
    assert "Lo que se me quedó grabado: las fotos son de la reforma de 2019" in \
        playbook.outreach_draft("first_touch", lead, "ES")["body"]
    assert "Ce qui m'a marqué : les photos datent de la rénovation de 2019" in \
        playbook.outreach_draft("first_touch", lead, "FR")["body"]
    for code in LANGUAGES:
        assert "one post about" not in playbook.outreach_draft("day3_reminder", lead, code)["body"]
