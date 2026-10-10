# Leads-to-Sales playbook

The five-step playbook MIM runs for MEM Digital, and the gate that stops it
running without you.

```bash
python -m mim.playbook          # status in English
python -m mim.playbook ES       # estado en español
python -m mim.playbook FR       # état en français
```

It prints the approval checklist, the lead tracker and what is due — and exits
`1` while anything is unapproved, so a script can fail on an unapproved campaign
instead of quietly running it.

---

## The two rules

**1. Nothing sends.** There is no send, publish, post, schedule or dispatch
function in `mim/playbook.py`, and a test asserts none can be added by
accident. Every generator returns a draft carrying `requires_approval: True`
and `status: "draft"`. You send from your own accounts; then you log it with
`log_sent` / `log_step_sent`, which records the fact rather than performing it.

**2. Nothing runs until you approve it.** Five points, all of them, or the
campaign refuses to plan:

| # | Approval | What "done" means |
|---|---|---|
| 1 | Niche and city chosen | One of the twenty categories, and one city |
| 2 | Outreach drafts approved | All three steps, in all three languages |
| 3 | Pricing and offers confirmed | The launch tiers, as they will be quoted |
| 4 | Campaign duration approved | The 14-day window and its start date |
| 5 | Sample files selected | Which of the five sample works get polished |

`assert_ready()` raises `ApprovalRequired` naming exactly what is still open.
Approval is meant to happen in the open — `checklist_markdown()` renders the
five points as a pull-request body, and `review_bundle()` renders one lead's
whole three-language sequence for review.

---

## Step 1 — Source and qualify

Pick **one** niche and **one** city. A list that targets everyone converts
nobody.

The twenty categories: tapas & pintxo bars · specialty cafés · bakeries ·
independent restaurants · boutique hotels · rural tourism · real estate ·
gyms · yoga & Pilates · physiotherapy · dental clinics · aesthetic clinics ·
hair & barber · nail & beauty · language schools · driving schools · coaches ·
pet services · florists · home services.

Each carries a trilingual label, the core service it maps to, and a bank of
five concrete signals to look for.

A lead qualifies on **two** of the five gaps, and becomes a priority at three:

* posts less than once a week
* bio has no booking link
* unanswered DMs or comments
* single-language content
* active but low-quality business account

The tracker is eight columns, no more:

```
name | business | channel | signal spotted | message sent | date | reply | next step
```

`tracker_csv()` and `tracker_markdown()` both emit exactly those, in that order.

---

## Step 2 — Outreach and follow-up

Three steps. Then the thread closes. There is no day 10.

| Day | Step | What it does |
|---|---|---|
| 0 | `first_touch` | Names a specific detail about *that* business and asks a question. No pitch, no price. |
| 3 | `day3_reminder` | Offers one free sample post, under an hour of work. |
| 7 | `day7_final` | Final polite note, states there is no follow-up sequence, closes. |

All three are written in EN, ES and FR. A draft with an unfilled slot —
`{first_name}`, `{detail}`, `{question}` — reports `ready_for_review: False`
and lists what is missing, so a generic message cannot slip through as ready.

Write the `signal spotted` note in the language of the message you will send:
the detail is dropped into the draft verbatim.

`followup_schedule()` says what is due for one lead; `due_followups()` lists
everything due or overdue today, worst first. A step you have logged as sent
is never flagged again.

---

## Steps 3 and 4 — Portfolio and campaign

Five sample works, written once and polished rather than regenerated per lead:
the pintxo bar reel script, the coach carousel, the candle shop copy rewrite,
the n8n automation outline, and the multilingual post.

The campaign is **"10 Businesses, 10 Free Posts"** across 14 days. Days 1 and 2
are approval days — nothing goes out before them. `campaign_timeline()` returns
the calendar with each human gate marked and the organic post assigned to its day.

The free sample is capped at **one hour**. `check_sample_cap()` raises
`SampleOverCap` past it; cut the scope or quote a paid tier.

---

## Step 5 — Pricing and closing

Launch pricing, in euro:

| Tier | Price | Includes |
|---|---|---|
| Free Sample | €0 | One post or reel, capped at 1 hour of work |
| Content Starter | €149/month | 8 posts, captions, one language |
| Social Growth | €349/month | 12 posts, 4 reels, DM replies, monthly report |
| Automation Setup | €250 setup + €49/month | Upkeep |
| Extra Language | +€60/month | Per package |

`quote("social_growth", languages=2)` → €409/month. The free sample covers one
language and refuses a second, because an hour does not stretch further.

Closing messages are written in **EN and ES** only — the two languages the
launch market buys in — and refuse to be built before the prospect has named
their own goals.

Offers must come from the core catalogue: AI content, social media management,
automation, digital products. Design, editing, coding and tutoring are reserved
extras; `assert_core_offer()` raises `OfferOutOfRange` if you lead with one.

---

## State

`data/playbook.json` holds the leads and the approvals, written atomically by
the same layer as the rest of the book. It is deliberately **not** one of the
five core collections, so book exports and the Netlify console keep the shape
documented in the README. The trade-off: `store.sync_now()` does not re-pull
it — `save_state()` pushes it on every write instead.
