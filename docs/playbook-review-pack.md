# Playbook review pack

Everything the Leads-to-Sales playbook currently holds, rendered from the live
`data/playbook.json` and the module itself — nothing here is hand-copied.

- **Campaign:** 10 Businesses, 10 Free Posts
- **Target:** Boutique hotels & hostels · San Sebastián
- **Window:** 2026-10-10 → 2026-10-23 (2026-10-10 → 2026-10-23)
- **Plan status:** `pending_human_send` · sent: `False` · requires_approval: `True`

> Nothing has been sent. Every message below is a draft. Sending is yours.

---

## 1. Approval state — all five gates

## Playbook approval — 0 of 5 open

- [x] **1. Niche and city chosen** — boutique_hotels · San Sebastián
      One niche from the twenty categories, and one city.
- [x] **2. Outreach drafts approved** — 3/3 steps · 3/3 languages
      First touch, day 3 and day 7, in EN, ES and FR.
- [x] **3. Pricing and offers confirmed** — free_sample, content_starter, social_growth, automation_setup
      The launch tiers, in euro, as they will be quoted.
- [x] **4. Campaign duration approved** — 14 days from 2026-10-10
      The 14-day window and its start date.
- [x] **5. Sample files selected to polish** — pintxo_reel, coach_carousel, candle_copy, n8n_automation, multilingual_post
      Which of the five sample works get polished first.

> Nothing sends until all five are ticked. MIM drafts; a human approves and sends.

---

## 2. The nine approved outreach drafts

Three steps × three languages. The day-0 question is the sharpened
direct-bookings-vs-OTA version you asked for.

## Outreach review — [nombre del hotel]

- Lead: `L-001` · channel: instagram
- Signal spotted: las fotos de las habitaciones siguen siendo de la reforma de 2019 y la tarifa solo aparece en la OTA
- Qualification: 3/5 matched (priority)

### EN
**First message** — ready

```
Hi [Nombre],

I came across [nombre del hotel] while looking at Boutique hotels & hostels in San Sebastián. What stuck: the room photos are still from the 2019 refurb, and the only rate anywhere is the OTA one — exactly the sort of thing most places around here never put online.

One question, and there's nothing being sold in it: of August's room nights, how many came through your own site and how many through Booking?

— MEM Digital
```

**Day 3 — free sample offer** — ready

```
Hi [Nombre],

No reply needed if the timing is wrong.

If it isn't: I'll make [nombre del hotel] one post. The angle: the room photos are still from the 2019 refurb, and the only rate anywhere is the OTA one. Free, under an hour of my time, yours to keep whether we ever work together or not. If you like it, we talk. If you don't, you've lost nothing.

Want me to send it?

— MEM Digital
```

**Day 7 — final note** — ready

```
Hi [Nombre],

Last note from me — I'll close this thread so I'm not sitting in your inbox.

If [nombre del hotel] ever wants a hand with automation, the offer stands: one free post, no obligation, no follow-up sequence. Reply any time and I'll pick it up the same day.

Good luck with the season.

— MEM Digital
```

### ES
**Primer mensaje** — ready

```
Hola [Nombre],

Encontré [nombre del hotel] buscando Hoteles boutique y hostales en San Sebastián. Lo que se me quedó grabado: las fotos de las habitaciones siguen siendo de la reforma de 2019 y la tarifa solo aparece en la OTA — justo el tipo de cosa que casi nadie por aquí muestra en internet.

Una pregunta, y no hay nada en venta dentro: de las noches de agosto, ¿cuántas os llegaron por la web y cuántas por Booking?

— MEM Digital
```

**Día 3 — muestra gratis** — ready

```
Hola [Nombre],

No hace falta que respondas si no es el momento.

Si lo es: le hago a [nombre del hotel] una publicación. El ángulo: las fotos de las habitaciones siguen siendo de la reforma de 2019 y la tarifa solo aparece en la OTA. Gratis, menos de una hora de mi tiempo, y se queda contigo trabajemos juntos o no. Si te gusta, hablamos. Si no, no has perdido nada.

¿Te la envío?

— MEM Digital
```

**Día 7 — nota final** — ready

```
Hola [Nombre],

Último mensaje por mi parte — cierro el hilo para no ocupar tu bandeja.

Si [nombre del hotel] necesita una mano con automatización, la oferta sigue en pie: una publicación gratis, sin compromiso y sin secuencia de seguimiento. Escribe cuando quieras y lo retomo el mismo día.

Mucha suerte con la temporada.

— MEM Digital
```

### FR
**Premier message** — ready

```
Bonjour [Nombre],

Je suis tombé sur [nombre del hotel] en cherchant Hôtels boutiques et auberges à San Sebastián. Ce qui m'a marqué : les photos des chambres datent encore de la rénovation de 2019, et le seul tarif visible est celui de l'OTA — exactement le genre de chose que presque personne ici ne met en ligne.

Une question, et il n'y a rien à vendre dedans : sur les nuits d'août, combien sont passées par votre propre site et combien par Booking ?

— MEM Digital
```

**Jour 3 — échantillon offert** — ready

```
Bonjour [Nombre],

Pas besoin de répondre si ce n'est pas le moment.

Si ça l'est : je fais pour [nombre del hotel] une publication. L'angle : les photos des chambres datent encore de la rénovation de 2019, et le seul tarif visible est celui de l'OTA. Gratuite, moins d'une heure de mon temps, et elle reste à vous que l'on travaille ensemble ou non. Si elle vous plaît, on en parle. Sinon, vous n'avez rien perdu.

Je vous l'envoie ?

— MEM Digital
```

**Jour 7 — dernier message** — ready

```
Bonjour [Nombre],

Dernier message de ma part — je clôture le fil pour ne pas encombrer votre boîte.

Si un jour [nombre del hotel] a besoin d'un coup de main sur automatisation, l'offre tient toujours : une publication gratuite, sans engagement et sans relance. Écrivez quand vous voulez, je m'y mets le jour même.

Bonne saison.

— MEM Digital
```

> Human approval required before any of this is sent. MIM does not send.

---

## 3. Launch pricing

| Tier | Price | Includes |
|---|---|---|
| Free Sample | €0 | One post or reel, capped at 1 hour of work |
| Content Starter | €149/mo | 8 posts, captions, one language |
| Social Growth | €349/mo | 12 posts, 4 reels, DM replies, monthly report |
| Automation Setup | €250 setup + €49/mo | 250 setup + 49/month upkeep |
| Extra language | +€60/mo | Per package |

Worked examples, from `quote()`:

- `content_starter` · 1 language(s) · 1 month(s) → **€149** total (€0 setup + €149/mo)
- `content_starter` · 2 language(s) · 1 month(s) → **€209** total (€0 setup + €209/mo)
- `social_growth` · 1 language(s) · 1 month(s) → **€349** total (€0 setup + €349/mo)
- `social_growth` · 2 language(s) · 1 month(s) → **€409** total (€0 setup + €409/mo)
- `social_growth` · 3 language(s) · 3 month(s) → **€1407** total (€0 setup + €469/mo)
- `automation_setup` · 1 language(s) · 6 month(s) → **€544** total (€250 setup + €49/mo)

Refusals that are built in: the Free Sample rejects a second language, and
leading with design, editing, coding or tutoring raises `OfferOutOfRange`.

---

## 4. The 14-day campaign calendar

| Day | Date | Focus | Organic post | Gate |
|---|---|---|---|---|
| 1 | 2026-10-10 | Pick one niche and one city. Build the list of 20-30. | — | **HUMAN** |
| 2 | 2026-10-11 | Approve the outreach drafts in EN, ES and FR. | — | **HUMAN** |
| 3 | 2026-10-12 | Send the first touches. Organic post 1 goes out. | What 20 local businesses are getting wrong online (carousel) |  |
| 4 | 2026-10-13 | Log every reply. Book the calls that came back. | One free post, delivered: the pintxo bar (reel) |  |
| 5 | 2026-10-14 | Deliver the free samples that were accepted. | The reply that closed a client, in screenshots (carousel) |  |
| 6 | 2026-10-15 | Day 3 reminders due. Organic post 4. | Before / after: one bio, rewritten (single image) |  |
| 7 | 2026-10-16 | Day 3 reminders due. Post the pricing. | What I charge and why — the launch pricing (carousel) |  |
| 8 | 2026-10-17 | Deliver accepted samples. Start the closing conversations. | One free post, delivered: the coach (carousel) |  |
| 9 | 2026-10-18 | Send closing messages to anyone who named a goal. | An automation that answers in three languages (screen recording) |  |
| 10 | 2026-10-19 | Day 7 final notes due. Close the silent threads. | — |  |
| 11 | 2026-10-20 | Follow up the proposals that are still open. | The question that gets a local business to reply (single image) |  |
| 12 | 2026-10-21 | Deliver the last free samples. | One free post, delivered: the candle shop (single image) |  |
| 13 | 2026-10-22 | Count: replies, samples, proposals, signed. | — |  |
| 14 | 2026-10-23 | Campaign review. Decide: repeat, widen, or stop. | Ten businesses, ten free posts — what I learned (carousel) | **HUMAN** |

---

## 5. The five sample works — all selected for polishing

### Pintxo bar reel script

`pintxo_reel` · reel script · 30s · Social media management · EN, ES · status: **polishing**

- 0-3s: hands pulling a pintxo off the bar, no face, no logo
- 3-10s: voiceover names the one thing tourists never order
- 10-20s: the regular's order, cut to the count
- 20-27s: the bill, and what it really costs
- 27-30s: text card — the address, nothing else

### Coach carousel

`coach_carousel` · carousel · 7 slides · Digital products · EN, ES, FR · status: **polishing**

- 1: the belief the audience already holds
- 2: the cost of that belief, in numbers
- 3: the reframe, in one sentence
- 4-5: the two steps that follow from it
- 6: the objection, answered flatly
- 7: the offer and the one action

### Candle shop copy rewrite

`candle_copy` · product copy · before/after · AI content · EN, ES · status: **polishing**

- before: the original scent description, unedited
- after: the same scent told as a specific evening
- the three lines that changed and why
- the price justified in one sentence

### n8n automation outline

`n8n_automation` · workflow outline · one page · Automation · EN, ES, FR · status: **polishing**

- trigger: new review, message or booking request
- step 1: classify intent and language
- step 2: draft the reply in the customer's language
- step 3: route to the owner for approval — never auto-send
- step 4: log the exchange and the response time
- fallback: anything low-confidence goes to a human untouched

### Multilingual post

`multilingual_post` · single post · 3 languages · AI content · EN, ES, FR · status: **polishing**

- one hook that survives translation
- the same post rendered in ES, EN and FR
- the words that had to change per language and why
- the caption-length trade-off

---

## 6. The twenty niches

One was picked; the other nineteen stay closed for this campaign.

- `tapas_bars` — Tapas & pintxo bars / Bares de tapas y pintxos / Bars à tapas et pintxos · Social media management
- `coffee_shops` — Specialty cafés / Cafeterías de especialidad / Cafés de spécialité · AI content
- `bakeries` — Bakeries & pastelerías / Panaderías y pastelerías / Boulangeries et pâtisseries · AI content
- `restaurants` — Independent restaurants / Restaurantes independientes / Restaurants indépendants · Social media management
- `boutique_hotels` — Boutique hotels & hostels / Hoteles boutique y hostales / Hôtels boutiques et auberges · Automation ← **SELECTED**
- `rural_tourism` — Rural tourism & casas rurales / Turismo rural y casas rurales / Tourisme rural et gîtes · Automation
- `real_estate` — Real estate agents / Agentes inmobiliarios / Agents immobiliers · Automation
- `gyms` — Gyms & fitness studios / Gimnasios y estudios de fitness / Salles de sport et studios fitness · Social media management
- `yoga_pilates` — Yoga & Pilates studios / Estudios de yoga y pilates / Studios de yoga et pilates · Social media management
- `physio_clinics` — Physiotherapy & massage clinics / Clínicas de fisioterapia y masaje / Cabinets de kinésithérapie et massage · Automation
- `dental_clinics` — Dental clinics / Clínicas dentales / Cabinets dentaires · Automation
- `aesthetic_clinics` — Aesthetic clinics & med spas / Clínicas estéticas y med spas / Cliniques esthétiques et med spas · Social media management
- `hair_barber` — Hair salons & barbershops / Peluquerías y barberías / Salons de coiffure et barbiers · Automation
- `nail_beauty` — Nail & beauty studios / Estudios de uñas y belleza / Studios d'onglerie et beauté · Automation
- `language_schools` — Language schools & academies / Academias de idiomas / Écoles de langues · AI content
- `driving_schools` — Driving schools / Autoescuelas / Auto-écoles · Automation
- `coaches` — Business, life & nutrition coaches / Coaches de negocio, vida y nutrición / Coachs business, vie et nutrition · Digital products
- `pet_services` — Pet shops, vets & groomers / Tiendas de mascotas, veterinarios y peluquería canina / Animaleries, vétérinaires et toiletteurs · Social media management
- `florists` — Florists & garden centres / Floristerías y garden centers / Fleuristes et jardineries · AI content
- `home_services` — Home services & reforms / Servicios del hogar y reformas / Services à domicile et rénovations · Automation

---

## 7. Lead tracker

**0 leads.** Sourcing has not started — no San Sebastián
businesses have been added, and none were invented.

Columns, in the order the CSV and markdown emitters write them:

```
name | business | channel | signal spotted | message sent | date | reply | next step
```

---

## 8. Run it yourself

```bash
python -m mim.playbook        # status in English; exits 1 while any gate is open
python -m mim.playbook ES     # en español
python -m mim.playbook FR     # en français
python -m pytest tests/ -q    # 159 tests
```
