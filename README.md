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

Two backends, chosen by configuration, same JSON either way:

* **local disk** (default) — `MIM_DATA_DIR`, atomic writes.
* **your private Git repo** — set `GITHUB_TOKEN` + `MIM_DATA_REPO`. Every save is a commit;
  the console pulls on load with a short cache and retries failed pushes. This is what makes
  a free, permanently-linked host safe: the book outlives the container.

The `data/` folder itself is git-ignored default so real client data stays out of this repo.
Export the full book as JSON from **Settings → Book** any time, or push it to your own
private data repo with the backend above.

## Get a permanent link

Three routes to a URL that outlives this session. The links below are pre-filled for this repo.

### A. Streamlit Community Cloud — free, 2 minutes, permanent URL

**[→ Deploy now](https://share.streamlit.io/deploy?repository=elmouhibmaroune9/Storytime&branch=arena/01a10c7b-storytime&mainModule=streamlit_app.py)**

Sign in with GitHub, confirm the repo + branch + `streamlit_app.py`, then paste this into
**Advanced settings → Secrets**:

```toml
MIM_ACCESS_CODE = "paste-a-long-random-code"
```

You get `https://<your-app>.streamlit.app`. **The container disk is ephemeral** — without
step B your book resets when the app sleeps. With step B it never does.

### B. Your book in Git — the part that makes any free host safe

Create a **private** repo (e.g. `mim-book`, empty — no README), then create a
[fine-grained token](https://github.com/settings/personal-access-tokens/new) scoped to
**that repo only** with **Contents: Read and write**. Add both as secrets/env vars on
whatever host you use:

| Variable | Value |
|---|---|
| `GITHUB_TOKEN` | the fine-grained token (never paste it into chat or a repo) |
| `MIM_DATA_REPO` | `your-user/mim-book` |

Optional: `MIM_DATA_BRANCH` (default `main`), `MIM_DATA_PATH` (default `data`).

From then on every save is a commit, every commit is a restore point, and the console —
Settings shows a green **Synced** panel with the repo name and last push. If GitHub is
briefly unreachable, writes mirror to local disk, the sidebar flags it, and **Sync now**
retries. Nothing is lost.

### C. Render / Railway / Fly.io — permanent URL with a real disk

Configs are in the repo: **`render.yaml`** (Blueprint — New → Blueprint → pick the repo),
**`fly.toml`** (`fly launch --copy-config && fly volumes create mim_data --size 1 && fly deploy`).
Mount the volume at `/app/data` — that single setting is the difference between a
permanent book and a recurring data loss. The Render disk requires the Starter plan
(~$7/mo); on the free plan, use the Git backend from step B instead.

### D. Your own domain, €4/month

Full control, no platform in the middle:

```bash
curl -fsSL https://raw.githubusercontent.com/elmouhibmarouane9/Storytime/arena/01a10c7b-storytime/deploy/install.sh | bash
```

One command: installs Docker, clones to `/opt/mim`, generates your access code, asks for a
domain, and serves HTTPS through Caddy. Details in **Path 2** below.

### Hugging Face Spaces — free, permanent, private

`deploy/huggingface.md` walks it end to end: Space + secrets + `git push`. Pair it with
step B so the book lives in Git, not on an ephemeral Space disk.

---

## Run it live

Five real paths. Pick by where the data lives, not by what's fashionable.

| Path | Cost | Where the book lives | Effort | Use it for |
|---|---|---|---|---|
| **This sandbox preview** | free | sandbox container, dies with the session | none | showing it off today |
| **Your machine + a tunnel** | €0 | your own disk, never leaves the room | 5 min | solo operator, always-on laptop or mini-PC |
| **Your own server** | ~€4/mo | Docker volume on the VPS, your domain, HTTPS | 10 min | production — always on, no laptop tax |
| **Render / Railway / Fly.io** | $5-7/mo | managed volume | 10 min | git-push deploys without touching a server |
| **Streamlit Community Cloud** | €0 | **container disk, wiped on restart** | 5 min | demos only — see the warning below |

---

### 1. Your machine + a tunnel — €0, data stays home

The console runs on your laptop, the tunnel makes it reachable from your phone. Nothing is uploaded anywhere.

```bash
# terminal 1 — the console
pip install -r requirements.txt
MIM_ACCESS_CODE=your-code streamlit run streamlit_app.py

# terminal 2 — the public URL (prints an https://...trycloudflare.com address)
brew install cloudflared          # macOS
winget install Cloudflare.cloudflared   # Windows
cloudflared tunnel --url http://localhost:8501
```

An account-free quick tunnel gives you a **random URL that changes on every restart**. For a fixed address, run a named tunnel against a domain you own (`cloudflared tunnel login && cloudflared tunnel create mim`). Your machine has to stay on; the book stays in `data/` next to the code.

Prefer private over public? `tailscale up` and open the machine's tailnet IP instead — no public URL, no access code needed, only your devices can see it.

---

### 2. Your own server — ~€4/month, the production answer

Hetzner CX22 (~€4), Contabo (~€4.50), DigitalOcean ($6). Debian or Ubuntu, any size — the app is idle-friendly.

**One command on a fresh server:**

```bash
curl -fsSL https://raw.githubusercontent.com/elmouhibmarouane9/Storytime/arena/01a10c7b-storytime/deploy/install.sh | bash
```

It installs Docker, clones the console into `/opt/mim`, generates an access code, asks for a domain (blank = localhost only), and starts everything. Point an A record at the server first if you want HTTPS — Caddy fetches the certificate automatically, websockets included.

**Or by hand, if you'd rather see every step:**

```bash
git clone --branch arena/01a10c7b-storytime https://github.com/elmouhibmarouane9/Storytime.git /opt/mim
cd /opt/mim
cp .env.example .env && nano .env        # set MIM_ACCESS_CODE (openssl rand -hex 12) and MIM_DOMAIN
docker compose --profile https up -d --build
docker compose logs -f mim               # watch it boot
```

No domain yet? Drop the profile and use an SSH tunnel from your laptop:

```bash
docker compose up -d                     # app bound to 127.0.0.1:8501 only
ssh -L 8501:127.0.0.1:8501 root@YOUR_SERVER   # then open http://localhost:8501
```

| Operation | Command |
|---|---|
| Update to latest code | `git pull && docker compose up -d --build` |
| Stop / start | `docker compose down` · `docker compose up -d` |
| Logs | `docker compose logs -f mim` |
| Back up the book | `docker compose exec mim cat /app/data/clients.json > backups/clients.json` |
| Restore | Settings → Book → Restore from JSON |

The book lives in the **`mim-data` Docker volume**, not the image — rebuilding never touches it. `backups/` on the host is mounted into the container for off-server copies.

---

### 3. Streamlit Community Cloud — €0, with one honest caveat

Fastest public URL, and the caveat matters: **the container filesystem is ephemeral.** Add a client, the platform sleeps the app, your data is gone. Use it to demo, not to run the agency.

1. Push this repo to GitHub, then [share.streamlit.io](https://share.streamlit.io) → **New app** → repo + branch → main file `streamlit_app.py`.
2. **Advanced settings → Secrets**, paste:
   ```toml
   MIM_ACCESS_CODE = "your-code"
   ```
   The console reads it from `st.secrets` when the environment variable is absent.
3. To move real data in: Settings → Book → **Restore from JSON** (upload an export). Before you leave the session, Settings → Book → **Export** and keep the JSON.

---

### 4. Render / Railway / Fly.io — git-push with a real disk

All three build the included `Dockerfile` as-is. The only requirement: **mount a volume at `/app/data`**, otherwise you inherit the ephemeral-disk problem.

| Platform | Setup |
|---|---|
| **Render** | New → Web Service → Docker → add a Disk, mount path `/app/data`; set `MIM_ACCESS_CODE` in Environment. Free tier has no disks — that's a paid-plan feature, and it's the whole point. |
| **Railway** | New Project → Deploy from repo → Variables: `MIM_ACCESS_CODE`; add a Volume mounted at `/app/data`. |
| **Fly.io** | `fly launch --no-deploy` → `fly volumes create mim_data --size 1` → mount at `/app/data` → `fly secrets set MIM_ACCESS_CODE=...` → `fly deploy`. |

---

### The gate, everywhere

Set `MIM_ACCESS_CODE` (env var, or `st.secrets` on Streamlit Cloud) and the console refuses to render until the code is entered. **Settings shows the gate status in red when it is not armed** — do not leave it that way on a public URL: your Finance page is your cash position.

Move a book between hosts with Settings → Book → Export / Restore. Same JSON, any host.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q     # 64 tests
```

- `tests/test_engine.py` — invoice maths, aging buckets, effective status, FX conversion, weighted
  forecasting, health scoring, deadline risk, scope-creep detection, time-to-invoice conversion,
  template rendering in both languages, move ranking and dedupe, export/import round-trips.
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
Dockerfile              production image (non-root, healthcheck, /app/data volume)
docker-compose.yml      app + optional Caddy HTTPS, persistent book volume
render.yaml             Render Blueprint (one-click, disk + secrets declared)
fly.toml                Fly.io app with a volume mounted at /app/data
deploy/install.sh       one-command install for a fresh Debian/Ubuntu server
deploy/Caddyfile        automatic TLS + websocket-safe reverse proxy
deploy/huggingface.md   Hugging Face Spaces walkthrough
tools/make_preview.py   regenerates docs/preview/index.html — a shareable static
                        walkthrough built from the same engine the app calls
.env.example            access code, domain, timezone
```
