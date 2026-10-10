"""Pillar 5 — Leads-to-Sales playbook.

The five steps: source leads, work the outreach cadence, build the portfolio,
run the organic campaign, close on launch pricing.

Two rules override everything else in this module.

1. **Nothing here sends.** Every generator returns a draft carrying
   ``requires_approval: True`` and ``status: "draft"``. There is no send,
   post, schedule, publish or network function anywhere in this file. The
   operator sends from their own accounts and logs it afterwards.
2. **No campaign step runs until the operator has approved it.**
   :func:`assert_ready` raises :class:`ApprovalRequired` naming every
   checklist item still open, and :func:`plan_campaign` calls it first.

State lives in ``data/playbook.json`` through the same atomic writer as the
rest of the book. It is deliberately *not* one of the five core collections
in :data:`mim.store.COLLECTIONS`, so exports and the Netlify book keep the
shape documented in the README; the trade-off is that ``store.sync_now()``
does not re-pull it — :func:`save_state` pushes it on every write instead.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date, timedelta
from typing import Any

from .models import as_str, days_since, money as _money, next_id, parse_date
from .store import load as _load, save as _save, today as _today

# ---------------------------------------------------------------- rules

LANGUAGES: tuple[str, ...] = ("EN", "ES", "FR")

#: The catalogue. Offers must come from here.
CORE_SERVICES: dict[str, dict[str, str]] = {
    "ai_content": {
        "en": "AI content", "es": "Contenido con IA", "fr": "Contenu IA",
    },
    "social_media": {
        "en": "Social media management", "es": "Gestión de redes sociales", "fr": "Gestion des réseaux sociaux",
    },
    "automation": {
        "en": "Automation", "es": "Automatización", "fr": "Automatisation",
    },
    "digital_products": {
        "en": "Digital products", "es": "Productos digitales", "fr": "Produits numériques",
    },
}

#: Reserved. These are add-ons, never the headline offer in a cold message.
EXTRA_OFFERS: dict[str, dict[str, str]] = {
    "design": {"en": "Design", "es": "Diseño", "fr": "Design"},
    "editing": {"en": "Editing", "es": "Edición", "fr": "Montage"},
    "coding": {"en": "Coding", "es": "Programación", "fr": "Développement"},
    "tutoring": {"en": "Tutoring", "es": "Clases particulares", "fr": "Tutorat"},
}

#: The eight columns the Lead Tracker is defined by. Order matters — the CSV,
#: the markdown table and the UI all read this one list.
LEAD_COLUMNS: tuple[str, ...] = (
    "name", "business", "channel", "signal spotted",
    "message sent", "date", "reply", "next step",
)

CHANNELS: tuple[str, ...] = ("instagram", "tiktok", "google_maps", "linkedin", "whatsapp", "walk_in")


class PlaybookError(RuntimeError):
    """Base class for every refusal in this module."""


class ApprovalRequired(PlaybookError):
    """A campaign step was requested before the operator signed off."""

    def __init__(self, missing: list[dict[str, Any]]):
        self.missing = missing
        items = "; ".join(f"{row['step']}. {row['label']}" for row in missing)
        super().__init__(f"Blocked — {len(missing)} approval(s) still open: {items}")


class OfferOutOfRange(PlaybookError):
    """An offer outside the core catalogue was put in front of a lead."""


class SampleOverCap(PlaybookError):
    """A free sample was scoped past the one-hour cap."""


# ---------------------------------------------------------------- niches

#: Twenty target categories. Pick exactly one per campaign — a list that
#: targets everyone converts nobody.
NICHES: dict[str, dict[str, Any]] = {
    "tapas_bars": {
        "en": "Tapas & pintxo bars", "es": "Bares de tapas y pintxos", "fr": "Bars à tapas et pintxos",
        "service": "social_media",
        "signals": [
            "board photos older than three weeks",
            "no booking or table link in the bio",
            "weekend comments sitting unanswered",
            "menu only in Spanish",
            "dishes shot in low light with no caption",
        ],
    },
    "coffee_shops": {
        "en": "Specialty cafés", "es": "Cafeterías de especialidad", "fr": "Cafés de spécialité",
        "service": "ai_content",
        "signals": [
            "posts under once a week",
            "no link to the beans or the menu",
            "questions in the comments ignored",
            "origin stories never told in a second language",
            "stories only, no feed presence",
        ],
    },
    "bakeries": {
        "en": "Bakeries & pastelerías", "es": "Panaderías y pastelerías", "fr": "Boulangeries et pâtisseries",
        "service": "ai_content",
        "signals": [
            "opening hours never posted",
            "no pre-order link",
            "DMs about custom cakes unanswered",
            "single-language captions",
            "product shots with no story behind them",
        ],
    },
    "restaurants": {
        "en": "Independent restaurants", "es": "Restaurantes independientes", "fr": "Restaurants indépendants",
        "service": "social_media",
        "signals": [
            "menu changes not reflected online",
            "reservation link missing from the bio",
            "reviews from the last month unanswered",
            "no English or French version of the menu",
            "empty tables midweek while the feed sleeps",
        ],
    },
    "boutique_hotels": {
        "en": "Boutique hotels & hostels", "es": "Hoteles boutique y hostales", "fr": "Hôtels boutiques et auberges",
        "service": "automation",
        "signals": [
            "seasonal offers never announced",
            "no direct-booking link, only an OTA",
            "guest questions unanswered for days",
            "property description in one language only",
            "photos from a single shoot, years old",
        ],
    },
    "rural_tourism": {
        "en": "Rural tourism & casas rurales", "es": "Turismo rural y casas rurales", "fr": "Tourisme rural et gîtes",
        "service": "automation",
        "signals": [
            "availability answered by hand, slowly",
            "no booking engine on the site",
            "enquiries in the inbox going cold",
            "listing in Spanish only",
            "surrounding area never shown",
        ],
    },
    "real_estate": {
        "en": "Real estate agents", "es": "Agentes inmobiliarios", "fr": "Agents immobiliers",
        "service": "automation",
        "signals": [
            "listings posted once and never again",
            "no valuation request form",
            "property questions unanswered",
            "no listing copy for foreign buyers",
            "raw phone footage of the flat",
        ],
    },
    "gyms": {
        "en": "Gyms & fitness studios", "es": "Gimnasios y estudios de fitness", "fr": "Salles de sport et studios fitness",
        "service": "social_media",
        "signals": [
            "class schedule only in the door window",
            "no trial booking link",
            "member questions left hanging",
            "timetable in one language",
            "before/afters with no context",
        ],
    },
    "yoga_pilates": {
        "en": "Yoga & Pilates studios", "es": "Estudios de yoga y pilates", "fr": "Studios de yoga et pilates",
        "service": "social_media",
        "signals": [
            "timetable changed without a post",
            "no drop-in booking link",
            "comment questions from weeks ago",
            "classes unexplained to newcomers",
            "same three poses on repeat",
        ],
    },
    "physio_clinics": {
        "en": "Physiotherapy & massage clinics", "es": "Clínicas de fisioterapia y masaje", "fr": "Cabinets de kinésithérapie et massage",
        "service": "automation",
        "signals": [
            "appointments taken only by phone",
            "no online booking in the bio",
            "patient messages unanswered",
            "treatment info in one language",
            "stock photos instead of the real clinic",
        ],
    },
    "dental_clinics": {
        "en": "Dental clinics", "es": "Clínicas dentales", "fr": "Cabinets dentaires",
        "service": "automation",
        "signals": [
            "first-visit offers never promoted",
            "no appointment link",
            "anxious-patient questions ignored",
            "no English guidance for expats",
            "clinical photos with no explanation",
        ],
    },
    "aesthetic_clinics": {
        "en": "Aesthetic clinics & med spas", "es": "Clínicas estéticas y med spas", "fr": "Cliniques esthétiques et med spas",
        "service": "social_media",
        "signals": [
            "price questions answered only in DMs",
            "no consultation booking link",
            "results comments unanswered",
            "treatments never explained in a second language",
            "over-filtered before/afters",
        ],
    },
    "hair_barber": {
        "en": "Hair salons & barbershops", "es": "Peluquerías y barberías", "fr": "Salons de coiffure et barbiers",
        "service": "automation",
        "signals": [
            "chairs visibly empty on Tuesdays",
            "no booking link, phone only",
            "cut requests unanswered in DMs",
            "stylists never introduced",
            "one mirror selfie a month",
        ],
    },
    "nail_beauty": {
        "en": "Nail & beauty studios", "es": "Estudios de uñas y belleza", "fr": "Studios d'onglerie et beauté",
        "service": "automation",
        "signals": [
            "price list only in stories",
            "no booking link in the bio",
            "availability questions ignored",
            "single-language service menu",
            "sets posted without prices or duration",
        ],
    },
    "language_schools": {
        "en": "Language schools & academies", "es": "Academias de idiomas", "fr": "Écoles de langues",
        "service": "ai_content",
        "signals": [
            "term dates announced late",
            "no enrolment form",
            "parent questions unanswered",
            "ironically, the content is not multilingual",
            "flyer scans instead of real classroom photos",
        ],
    },
    "driving_schools": {
        "en": "Driving schools", "es": "Autoescuelas", "fr": "Auto-écoles",
        "service": "automation",
        "signals": [
            "lesson slots managed on paper",
            "no enquiry form",
            "student messages unanswered",
            "no info for non-Spanish speakers",
            "pass rates never shared",
        ],
    },
    "coaches": {
        "en": "Business, life & nutrition coaches", "es": "Coaches de negocio, vida y nutrición", "fr": "Coachs business, vie et nutrition",
        "service": "digital_products",
        "signals": [
            "posts but no way to buy anything",
            "no calendar link in the bio",
            "DMs from interested people going stale",
            "one language, one audience",
            "long captions with no structure",
        ],
    },
    "pet_services": {
        "en": "Pet shops, vets & groomers", "es": "Tiendas de mascotas, veterinarios y peluquería canina", "fr": "Animaleries, vétérinaires et toiletteurs",
        "service": "social_media",
        "signals": [
            "cute photos, no service information",
            "no appointment link",
            "grooming questions unanswered",
            "care advice in one language",
            "nothing posted between product shots",
        ],
    },
    "florists": {
        "en": "Florists & garden centres", "es": "Floristerías y garden centers", "fr": "Fleuristes et jardineries",
        "service": "ai_content",
        "signals": [
            "seasonal peaks posted after the fact",
            "no order link",
            "delivery questions ignored",
            "no English option for expat orders",
            "bouquets photographed on a cluttered counter",
        ],
    },
    "home_services": {
        "en": "Home services & reforms", "es": "Servicios del hogar y reformas", "fr": "Services à domicile et rénovations",
        "service": "automation",
        "signals": [
            "quotes given only by phone call",
            "no request-a-quote form",
            "job enquiries unanswered for days",
            "no content for foreign homeowners",
            "before/after shots with no scope or price",
        ],
    },
}


def niche_options(lang: str = "EN") -> list[tuple[str, str]]:
    """(id, label) pairs for the twenty categories, in the operator's language."""
    key = lang_key(lang)
    return [(nid, value[key]) for nid, value in NICHES.items()]


def niche_label(niche: str, lang: str = "EN") -> str:
    entry = NICHES.get(niche)
    if not entry:
        raise PlaybookError(f"Unknown niche '{niche}'. Pick one of: {', '.join(sorted(NICHES))}")
    return entry[lang_key(lang)]


# ---------------------------------------------------------------- qualification

#: The five disqualifiers that make a business worth a message. Any one of
#: them is a real gap; two or more is a lead worth your hour.
QUALIFICATION: list[dict[str, Any]] = [
    {
        "key": "low_posting",
        "en": "Posts less than once a week",
        "es": "Publica menos de una vez por semana",
        "fr": "Publie moins d'une fois par semaine",
    },
    {
        "key": "no_booking_link",
        "en": "Bio has no booking link",
        "es": "No hay enlace de reservas en la bio",
        "fr": "Aucun lien de réservation dans la bio",
    },
    {
        "key": "unanswered",
        "en": "Unanswered DMs or comments",
        "es": "Mensajes o comentarios sin responder",
        "fr": "Messages ou commentaires sans réponse",
    },
    {
        "key": "single_language",
        "en": "Single-language content",
        "es": "Contenido en un solo idioma",
        "fr": "Contenu dans une seule langue",
    },
    {
        "key": "low_quality",
        "en": "Active but low-quality business account",
        "es": "Cuenta activa pero de baja calidad",
        "fr": "Compte actif mais de faible qualité",
    },
]

QUALIFYING_THRESHOLD = 2   # matched criteria before a lead earns a message
PRIORITY_THRESHOLD = 3     # matched criteria before a lead jumps the queue


def normalize_lang(lang: Any) -> str:
    """'es', 'ES-ES', 'Français' → 'EN' | 'ES' | 'FR'. Unknown falls back to EN."""
    raw = str(lang or "en").strip().lower()[:2]
    return {"en": "EN", "es": "ES", "fr": "FR"}.get(raw, "EN")


def lang_key(lang: Any) -> str:
    """Lowercase lookup key for the trilingual dicts: 'fr-FR' -> 'fr'."""
    return normalize_lang(lang).lower()


def qualification_labels(lang: str = "EN") -> list[dict[str, str]]:
    key = lang_key(lang)
    return [{"key": row["key"], "label": row[key]} for row in QUALIFICATION]


def new_lead(
    name: str,
    business: str,
    channel: str,
    signal: str,
    *,
    niche: str = "",
    city: str = "",
    language: str = "ES",
    signals_matched: list[str] | None = None,
    lead_date: date | str | None = None,
    reply: str = "",
    next_step: str = "",
    existing: list[dict] | None = None,
    detail_i18n: dict[str, str] | None = None,
) -> dict[str, Any]:
    """A lead tracker row. The eight public columns plus the internals."""
    if not business.strip():
        raise PlaybookError("A lead needs a business name.")
    known = {row["key"] for row in QUALIFICATION}
    unknown = [key for key in (signals_matched or []) if key not in known]
    if unknown:
        raise PlaybookError(f"Unknown qualification signal(s): {', '.join(unknown)}")
    return {
        "id": next_id("L", [row.get("id", "") for row in (existing or [])]),
        "name": name.strip(),
        "business": business.strip(),
        "channel": channel.strip().lower(),
        "signal": signal.strip(),
        "message_sent": False,
        "date": as_str(parse_date(lead_date) or _today()),
        "reply": reply,
        "next_step": next_step,
        "niche": niche,
        "city": city,
        "language": normalize_lang(language),
        "signals_matched": list(signals_matched or []),
        "sent_steps": [],
        # The same observation written per language, so a Spanish note does not
        # end up pasted into the French message.
        "detail_i18n": detail_i18n or {},
    }


def qualify(lead: dict[str, Any]) -> dict[str, Any]:
    """Score a lead against the five criteria. Two matched = worth messaging."""
    matched = [key for key in lead.get("signals_matched", []) if key in {row["key"] for row in QUALIFICATION}]
    missed = [row["key"] for row in QUALIFICATION if row["key"] not in matched]
    count = len(matched)
    if count >= PRIORITY_THRESHOLD:
        verdict, step = "priority", "Message today — this one has three visible gaps."
    elif count >= QUALIFYING_THRESHOLD:
        verdict, step = "qualified", "Message this week."
    else:
        verdict, step = "thin", "Not yet. Find one more visible gap before spending the message."
    return {
        "lead_id": lead.get("id"),
        "business": lead.get("business"),
        "matched": matched,
        "missed": missed,
        "score": count,
        "verdict": verdict,
        "qualified": count >= QUALIFYING_THRESHOLD,
        "next_step": step,
    }


def rank_leads(leads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Best leads first: qualification score, then silence, then id."""
    def key(lead: dict[str, Any]):
        q = qualify(lead)
        quiet = days_since(lead.get("date"), _today()) or 0
        return (-q["score"], -quiet, lead.get("id", ""))

    return sorted(leads, key=key)


# ---------------------------------------------------------------- tracker

def tracker_rows(leads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The tracker in its eight defined columns, nothing else."""
    rows = []
    for lead in leads:
        rows.append({
            "name": lead.get("name", ""),
            "business": lead.get("business", ""),
            "channel": lead.get("channel", ""),
            "signal spotted": lead.get("signal", ""),
            "message sent": "yes" if lead.get("message_sent") else "no",
            "date": lead.get("date", ""),
            "reply": lead.get("reply", ""),
            "next step": lead.get("next_step", ""),
        })
    return rows


def tracker_csv(leads: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(LEAD_COLUMNS), lineterminator="\n")
    writer.writeheader()
    writer.writerows(tracker_rows(leads))
    return buffer.getvalue()


def tracker_markdown(leads: list[dict[str, Any]]) -> str:
    rows = tracker_rows(leads)
    out = ["| " + " | ".join(LEAD_COLUMNS) + " |",
           "|" + "|".join(["---"] * len(LEAD_COLUMNS)) + "|"]
    for row in rows:
        cells = [str(row[col]).replace("|", "\\|").replace("\n", " ") for col in LEAD_COLUMNS]
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


# ---------------------------------------------------------------- outreach

SIGNOFF = "— MEM Digital"

#: The cadence. Day 0 names a specific detail and asks a question, with no
#: pitch attached. Day 3 offers the free sample. Day 7 closes the thread
#: politely and stops. There is no day 10.
OUTREACH: dict[str, dict[str, Any]] = {
    "first_touch": {
        "day": 0,
        "label": {"en": "First message", "es": "Primer mensaje", "fr": "Premier message"},
        "en": """Hi {first_name},

I came across {business} while looking at {niche} in {city}. What stuck: {detail} — exactly the sort of thing most places around here never put online.

One question, and there's nothing being sold in it: {question}

{sender}""",
        "es": """Hola {first_name},

Encontré {business} buscando {niche} en {city}. Lo que se me quedó grabado: {detail} — justo el tipo de cosa que casi nadie por aquí muestra en internet.

Una pregunta, y no hay nada en venta dentro: {question}

{sender}""",
        "fr": """Bonjour {first_name},

Je suis tombé sur {business} en cherchant {niche} à {city}. Ce qui m'a marqué : {detail} — exactement le genre de chose que presque personne ici ne met en ligne.

Une question, et il n'y a rien à vendre dedans : {question}

{sender}""",
    },
    "day3_reminder": {
        "day": 3,
        "label": {"en": "Day 3 — free sample offer", "es": "Día 3 — muestra gratis", "fr": "Jour 3 — échantillon offert"},
        "en": """Hi {first_name},

No reply needed if the timing is wrong.

If it isn't: I'll make {business} one post. The angle: {detail}. Free, under an hour of my time, yours to keep whether we ever work together or not. If you like it, we talk. If you don't, you've lost nothing.

Want me to send it?

{sender}""",
        "es": """Hola {first_name},

No hace falta que respondas si no es el momento.

Si lo es: le hago a {business} una publicación. El ángulo: {detail}. Gratis, menos de una hora de mi tiempo, y se queda contigo trabajemos juntos o no. Si te gusta, hablamos. Si no, no has perdido nada.

¿Te la envío?

{sender}""",
        "fr": """Bonjour {first_name},

Pas besoin de répondre si ce n'est pas le moment.

Si ça l'est : je fais pour {business} une publication. L'angle : {detail}. Gratuite, moins d'une heure de mon temps, et elle reste à vous que l'on travaille ensemble ou non. Si elle vous plaît, on en parle. Sinon, vous n'avez rien perdu.

Je vous l'envoie ?

{sender}""",
    },
    "day7_final": {
        "day": 7,
        "label": {"en": "Day 7 — final note", "es": "Día 7 — nota final", "fr": "Jour 7 — dernier message"},
        "en": """Hi {first_name},

Last note from me — I'll close this thread so I'm not sitting in your inbox.

If {business} ever wants a hand with {service}, the offer stands: one free post, no obligation, no follow-up sequence. Reply any time and I'll pick it up the same day.

Good luck with the season.

{sender}""",
        "es": """Hola {first_name},

Último mensaje por mi parte — cierro el hilo para no ocupar tu bandeja.

Si {business} necesita una mano con {service}, la oferta sigue en pie: una publicación gratis, sin compromiso y sin secuencia de seguimiento. Escribe cuando quieras y lo retomo el mismo día.

Mucha suerte con la temporada.

{sender}""",
        "fr": """Bonjour {first_name},

Dernier message de ma part — je clôture le fil pour ne pas encombrer votre boîte.

Si un jour {business} a besoin d'un coup de main sur {service}, l'offre tient toujours : une publication gratuite, sans engagement et sans relance. Écrivez quand vous voulez, je m'y mets le jour même.

Bonne saison.

{sender}""",
    },
}

OUTREACH_ORDER: tuple[str, ...] = ("first_touch", "day3_reminder", "day7_final")

#: Slots the operator must fill by hand. A draft with one of these still in
#: it is not finished, and `draft_gaps` says so.
PERSONALISATION_SLOTS: tuple[str, ...] = ("first_name", "detail", "question")


def _fill(template: str, ctx: dict[str, Any]) -> str:
    class _Missing(dict):
        def __missing__(self, key):  # leave the slot visible instead of crashing
            return f"{{{key}}}"

    return template.format_map(_Missing(**ctx))


def outreach_context(lead: dict[str, Any], extra: dict[str, Any] | None = None, lang: str = "ES") -> dict[str, Any]:
    """Merge a lead's fields with whatever the operator typed in by hand."""
    key = lang_key(lang)
    first_name = (lead.get("name") or "").strip().split(" ")[0]
    niche = lead.get("niche", "")
    # Unfilled slots are re-emitted as {braces} on purpose: `draft_gaps` then
    # finds them and the draft reports itself as not ready. A generic message
    # cannot be marked review-ready by accident.
    ctx: dict[str, Any] = {
        "first_name": first_name or "{first_name}",
        "business": lead.get("business") or "{business}",
        "niche": niche_label(niche, key) if niche in NICHES else "{niche}",
        "city": lead.get("city") or "{city}",
        "detail": (lead.get("detail_i18n") or {}).get(key) or lead.get("signal") or "{detail}",
        "question": "{question}",
        "service": "{service}",
        "sender": SIGNOFF,
    }
    service = NICHES.get(niche, {}).get("service")
    if service:
        ctx["service"] = CORE_SERVICES[service][key].lower()
    if extra:
        ctx.update({k: v for k, v in extra.items() if v not in (None, "")})
    return ctx


def draft_gaps(text: str) -> list[str]:
    """Slot names still unfilled in a draft. An empty list means it is ready to review."""
    return sorted(set(re.findall(r"\{([a-z_]+)\}", text)))


def outreach_draft(
    kind: str,
    lead: dict[str, Any],
    lang: str = "ES",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One draft message. Never sent — read `requires_approval` before you act.

    The draft is returned with its unfilled slots listed, so a generic
    message cannot leave by accident.
    """
    code = normalize_lang(lang)
    key = code.lower()
    template = OUTREACH.get(kind, {}).get(key)
    if template is None:
        raise PlaybookError(f"Unknown outreach step '{kind}'. Use one of: {', '.join(OUTREACH_ORDER)}")
    body = _fill(template, outreach_context(lead, extra, code))
    return {
        "kind": kind,
        "step": OUTREACH[kind]["label"][key],
        "lead_id": lead.get("id"),
        "business": lead.get("business"),
        "channel": lead.get("channel"),
        "language": code,
        "body": body,
        "unfilled": draft_gaps(body),
        "ready_for_review": not draft_gaps(body),
        "status": "draft",
        "requires_approval": True,
        "sent": False,
        "sent_by_human": False,
    }


def outreach_set(lead: dict[str, Any], lang: str = "ES", extra: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """The whole three-step sequence for one lead, in one language."""
    return [outreach_draft(kind, lead, lang, extra) for kind in OUTREACH_ORDER]


def outreach_bundle(lead: dict[str, Any], extra: dict[str, Any] | None = None) -> dict[str, list[dict[str, Any]]]:
    """All three steps in all three languages — what goes in the review PR.

    `extra` is either one flat dict applied to every language, or a dict keyed
    by language code ({"EN": {...}, "ES": {...}, "FR": {...}}) when the detail
    and the question differ per language — which in a Spanish city they do.
    """
    per_lang = isinstance(extra, dict) and set(LANGUAGES).issubset(extra)
    return {
        code: outreach_set(lead, code, extra.get(code) if per_lang else extra)
        for code in LANGUAGES
    }


# ---------------------------------------------------------------- cadence

def followup_schedule(lead: dict[str, Any], on: date | None = None) -> list[dict[str, Any]]:
    """What is due for one lead, and whether it is late.

    Day 3 offers the free sample. Day 7 is the final polite note, and the
    thread closes after it. Nothing here sends the follow-up.
    """
    ref = on or _today()
    touched = parse_date(lead.get("date"))
    sent_steps = set(lead.get("sent_steps") or [])
    if lead.get("message_sent"):
        # `message_sent` is the older flag and wins for the first touch, so a
        # lead imported from an older tracker is never nagged to re-send it.
        sent_steps.add("first_touch")
    out: list[dict[str, Any]] = []
    for kind in OUTREACH_ORDER:
        offset = OUTREACH[kind]["day"]
        due = (touched + timedelta(days=offset)) if touched else None
        if kind in sent_steps:
            # Already sent by the operator. Never nag them to send it twice.
            status = "sent"
        elif due is None:
            status = "unscheduled"
        elif kind == "first_touch" and not lead.get("message_sent"):
            status = "not started"
        elif due > ref:
            status = "scheduled"
        elif due == ref:
            status = "due today"
        else:
            status = "overdue"
        out.append({
            "kind": kind,
            "day": offset,
            "due": as_str(due),
            "days_late": max(0, (ref - due).days) if due and due <= ref and status != "sent" else 0,
            "status": status,
        })
    return out


def due_followups(leads: list[dict[str, Any]], on: date | None = None) -> list[dict[str, Any]]:
    """Every follow-up that is due or overdue today, worst first."""
    ref = on or _today()
    rows: list[dict[str, Any]] = []
    for lead in leads:
        for step in followup_schedule(lead, ref):
            if step["status"] in ("due today", "overdue"):
                rows.append({
                    "lead_id": lead.get("id"),
                    "business": lead.get("business"),
                    "channel": lead.get("channel"),
                    "kind": step["kind"],
                    "day": step["day"],
                    "due": step["due"],
                    "days_late": step["days_late"],
                    "next_step": "Draft the note, get it approved, then send it yourself.",
                })
    return sorted(rows, key=lambda row: (-row["days_late"], row["lead_id"] or ""))


def close_thread(lead: dict[str, Any], reason: str = "closed after day 7") -> dict[str, Any]:
    """Mark a lead closed. Records the decision; sends nothing."""
    updated = dict(lead)
    updated["closed"] = True
    updated["closed_on"] = as_str(_today())
    updated["closed_reason"] = reason
    updated["next_step"] = "Closed. Revisit only if they reply."
    return updated


# ---------------------------------------------------------------- portfolio

#: The five sample works. These are the proof, so they are written once and
#: polished — never regenerated per lead.
SAMPLE_WORKS: list[dict[str, Any]] = [
    {
        "id": "pintxo_reel",
        "title": {"en": "Pintxo bar reel script", "es": "Guion de reel para bar de pintxos", "fr": "Script de reel pour bar à pintxos"},
        "niche": "tapas_bars",
        "format": "reel script · 30s",
        "service": "social_media",
        "languages": ["EN", "ES"],
        "beats": [
            "0-3s: hands pulling a pintxo off the bar, no face, no logo",
            "3-10s: voiceover names the one thing tourists never order",
            "10-20s: the regular's order, cut to the count",
            "20-27s: the bill, and what it really costs",
            "27-30s: text card — the address, nothing else",
        ],
        "status": "draft",
    },
    {
        "id": "coach_carousel",
        "title": {"en": "Coach carousel", "es": "Carrusel para coach", "fr": "Carrousel pour coach"},
        "niche": "coaches",
        "format": "carousel · 7 slides",
        "service": "digital_products",
        "languages": ["EN", "ES", "FR"],
        "beats": [
            "1: the belief the audience already holds",
            "2: the cost of that belief, in numbers",
            "3: the reframe, in one sentence",
            "4-5: the two steps that follow from it",
            "6: the objection, answered flatly",
            "7: the offer and the one action",
        ],
        "status": "draft",
    },
    {
        "id": "candle_copy",
        "title": {"en": "Candle shop copy rewrite", "es": "Reescritura de textos para tienda de velas", "fr": "Réécriture de textes pour boutique de bougies"},
        "niche": "florists",
        "format": "product copy · before/after",
        "service": "ai_content",
        "languages": ["EN", "ES"],
        "beats": [
            "before: the original scent description, unedited",
            "after: the same scent told as a specific evening",
            "the three lines that changed and why",
            "the price justified in one sentence",
        ],
        "status": "draft",
    },
    {
        "id": "n8n_automation",
        "title": {"en": "n8n automation outline", "es": "Esquema de automatización en n8n", "fr": "Plan d'automatisation n8n"},
        "niche": "restaurants",
        "format": "workflow outline · one page",
        "service": "automation",
        "languages": ["EN", "ES", "FR"],
        "beats": [
            "trigger: new review, message or booking request",
            "step 1: classify intent and language",
            "step 2: draft the reply in the customer's language",
            "step 3: route to the owner for approval — never auto-send",
            "step 4: log the exchange and the response time",
            "fallback: anything low-confidence goes to a human untouched",
        ],
        "status": "draft",
    },
    {
        "id": "multilingual_post",
        "title": {"en": "Multilingual post", "es": "Publicación multilingüe", "fr": "Publication multilingue"},
        "niche": "boutique_hotels",
        "format": "single post · 3 languages",
        "service": "ai_content",
        "languages": ["EN", "ES", "FR"],
        "beats": [
            "one hook that survives translation",
            "the same post rendered in ES, EN and FR",
            "the words that had to change per language and why",
            "the caption-length trade-off",
        ],
        "status": "draft",
    },
]

SAMPLE_STATUS: tuple[str, ...] = ("draft", "polishing", "approved", "published")

#: The free sample is capped at one hour. No exceptions, no silent creep.
FREE_SAMPLE_HOURS_CAP = 1.0


def sample_works(lang: str = "EN") -> list[dict[str, Any]]:
    key = lang_key(lang)
    return [{**work, "label": work["title"][key]} for work in SAMPLE_WORKS]


def select_samples(ids: list[str]) -> list[dict[str, Any]]:
    """The works the operator chose to polish. Unknown ids are refused, not ignored."""
    unknown = [i for i in ids if i not in {w["id"] for w in SAMPLE_WORKS}]
    if unknown:
        raise PlaybookError(f"Unknown sample work(s): {', '.join(unknown)}")
    return [dict(w, status="polishing") for w in SAMPLE_WORKS if w["id"] in ids]


def check_sample_cap(hours: float) -> float:
    """Refuse a free sample scoped past the one-hour cap."""
    try:
        value = float(hours)
    except (TypeError, ValueError) as exc:
        raise PlaybookError(f"Hours must be a number, got {hours!r}") from exc
    if value > FREE_SAMPLE_HOURS_CAP:
        raise SampleOverCap(
            f"Free sample is capped at {FREE_SAMPLE_HOURS_CAP} hour; {value} was requested. "
            "Cut the scope or quote a paid tier."
        )
    return value


# ---------------------------------------------------------------- campaign

#: "10 Businesses, 10 Free Posts" — ten organic posts across a fourteen-day
#: window. Days 1-2 are approval days; nothing goes out before them.
CAMPAIGN_NAME = "10 Businesses, 10 Free Posts"
CAMPAIGN_DAYS = 14

ORGANIC_POSTS: list[dict[str, Any]] = [
    {"id": "ORG-01", "day": 3, "topic": "What 20 local businesses are getting wrong online", "format": "carousel", "goal": "reach"},
    {"id": "ORG-02", "day": 4, "topic": "One free post, delivered: the pintxo bar", "format": "reel", "goal": "proof"},
    {"id": "ORG-03", "day": 5, "topic": "The reply that closed a client, in screenshots", "format": "carousel", "goal": "proof"},
    {"id": "ORG-04", "day": 6, "topic": "Before / after: one bio, rewritten", "format": "single image", "goal": "proof"},
    {"id": "ORG-05", "day": 7, "topic": "What I charge and why — the launch pricing", "format": "carousel", "goal": "offer"},
    {"id": "ORG-06", "day": 8, "topic": "One free post, delivered: the coach", "format": "carousel", "goal": "proof"},
    {"id": "ORG-07", "day": 9, "topic": "An automation that answers in three languages", "format": "screen recording", "goal": "proof"},
    {"id": "ORG-08", "day": 11, "topic": "The question that gets a local business to reply", "format": "single image", "goal": "reach"},
    {"id": "ORG-09", "day": 12, "topic": "One free post, delivered: the candle shop", "format": "single image", "goal": "proof"},
    {"id": "ORG-10", "day": 14, "topic": "Ten businesses, ten free posts — what I learned", "format": "carousel", "goal": "offer"},
]

CAMPAIGN_BEATS: list[tuple[int, str, str, bool]] = [
    (1, "Pick one niche and one city. Build the list of 20-30.", "Gate 1 — niche and city", True),
    (2, "Approve the outreach drafts in EN, ES and FR.", "Gate 2 — outreach drafts", True),
    (3, "Send the first touches. Organic post 1 goes out.", "First contact", False),
    (4, "Log every reply. Book the calls that came back.", "Cadence", False),
    (5, "Deliver the free samples that were accepted.", "Delivery", False),
    (6, "Day 3 reminders due. Organic post 4.", "Cadence", False),
    (7, "Day 3 reminders due. Post the pricing.", "Offer", False),
    (8, "Deliver accepted samples. Start the closing conversations.", "Delivery", False),
    (9, "Send closing messages to anyone who named a goal.", "Close", False),
    (10, "Day 7 final notes due. Close the silent threads.", "Close", False),
    (11, "Follow up the proposals that are still open.", "Close", False),
    (12, "Deliver the last free samples.", "Delivery", False),
    (13, "Count: replies, samples, proposals, signed.", "Review", False),
    (14, "Campaign review. Decide: repeat, widen, or stop.", "Gate 5 — review", True),
]


def campaign_timeline(start: date | str | None = None, days: int = CAMPAIGN_DAYS) -> list[dict[str, Any]]:
    """The fourteen-day calendar, with the human gate marked on each day."""
    day_one = parse_date(start) or _today()
    posts = {post["day"]: post for post in ORGANIC_POSTS}
    out: list[dict[str, Any]] = []
    for offset in range(1, days + 1):
        focus, beat, gate = next(
            ((f, b, g) for d, f, b, g in CAMPAIGN_BEATS if d == offset), ("", "", False)
        )
        out.append({
            "day": offset,
            "date": as_str(day_one + timedelta(days=offset - 1)),
            "focus": focus,
            "beat": beat,
            "human_gate": gate,
            "organic_post": posts.get(offset),
        })
    return out


def campaign_summary(leads: list[dict[str, Any]], start: date | str | None = None) -> dict[str, Any]:
    """Where the campaign actually stands. Counts, not adjectives."""
    replied = [lead for lead in leads if str(lead.get("reply", "")).strip()]
    return {
        "name": CAMPAIGN_NAME,
        "days": CAMPAIGN_DAYS,
        "window": f"{as_str(parse_date(start) or _today())} → "
                  f"{as_str((parse_date(start) or _today()) + timedelta(days=CAMPAIGN_DAYS - 1))}",
        "leads": len(leads),
        "messaged": sum(1 for lead in leads if lead.get("message_sent")),
        "replied": len(replied),
        "reply_rate": round(len(replied) / len(leads) * 100, 1) if leads else 0.0,
        "closed": sum(1 for lead in leads if lead.get("closed")),
        "organic_posts": len(ORGANIC_POSTS),
        "due_or_overdue": len(due_followups(leads)),
    }


# ---------------------------------------------------------------- pricing

#: Launch pricing. Fixed, in euro, and the only numbers quoted in outreach.
PRICING: list[dict[str, Any]] = [
    {
        "id": "free_sample",
        "service": "ai_content",
        "name": {"en": "Free Sample", "es": "Muestra gratis", "fr": "Échantillon offert"},
        "cadence": "one-off",
        "setup": 0.0,
        "monthly": 0.0,
        "includes": {"en": "One post or reel, capped at 1 hour of work",
                     "es": "Una publicación o reel, con un máximo de 1 hora de trabajo",
                     "fr": "Une publication ou un reel, limité à 1 heure de travail"},
        "cap_hours": FREE_SAMPLE_HOURS_CAP,
    },
    {
        "id": "content_starter",
        "service": "ai_content",
        "name": {"en": "Content Starter", "es": "Content Starter", "fr": "Content Starter"},
        "cadence": "month",
        "setup": 0.0,
        "monthly": 149.0,
        "includes": {"en": "8 posts, captions, one language",
                     "es": "8 publicaciones, textos, un idioma",
                     "fr": "8 publications, légendes, une langue"},
        "posts": 8, "languages_included": 1,
    },
    {
        "id": "social_growth",
        "service": "social_media",
        "name": {"en": "Social Growth", "es": "Social Growth", "fr": "Social Growth"},
        "cadence": "month",
        "setup": 0.0,
        "monthly": 349.0,
        "includes": {"en": "12 posts, 4 reels, DM replies, monthly report",
                     "es": "12 publicaciones, 4 reels, respuestas a mensajes, informe mensual",
                     "fr": "12 publications, 4 reels, réponses aux messages, rapport mensuel"},
        "posts": 12, "reels": 4, "dm_replies": True, "monthly_report": True, "languages_included": 1,
    },
    {
        "id": "automation_setup",
        "service": "automation",
        "name": {"en": "Automation Setup", "es": "Automatización", "fr": "Automatisation"},
        "cadence": "setup + month",
        "setup": 250.0,
        "monthly": 49.0,
        "includes": {"en": "250 setup + 49/month upkeep",
                     "es": "250 de configuración + 49/mes de mantenimiento",
                     "fr": "250 de mise en place + 49/mois de maintenance"},
    },
]

EXTRA_LANGUAGE_MONTHLY = 60.0
CURRENCY = "EUR"


def tier(tier_id: str) -> dict[str, Any]:
    for row in PRICING:
        if row["id"] == tier_id:
            return row
    raise PlaybookError(f"Unknown tier '{tier_id}'. Use one of: {', '.join(t['id'] for t in PRICING)}")


def tier_labels(lang: str = "EN") -> list[dict[str, str]]:
    key = lang_key(lang)
    return [{"id": row["id"], "name": row["name"][key], "includes": row["includes"][key]} for row in PRICING]


def assert_core_offer(services: list[str]) -> list[str]:
    """Refuse an offer built on the reserved extras.

    Design, editing, coding and tutoring are add-ons. A cold offer built on
    one of them is outside the catalogue this playbook is allowed to sell.
    """
    bad = [s for s in services if s in EXTRA_OFFERS]
    if bad:
        names = ", ".join(EXTRA_OFFERS[s]["en"] for s in bad)
        raise OfferOutOfRange(
            f"{names} is a reserved extra, not a core offer. Lead with AI content, social media "
            "management, automation or digital products, and attach the extra to that."
        )
    unknown = [s for s in services if s not in CORE_SERVICES]
    if unknown:
        raise PlaybookError(f"Unknown service(s): {', '.join(unknown)}")
    return list(services)


def _eur(amount: float) -> str:
    return _money(amount, CURRENCY)


def quote(tier_id: str, languages: int = 1, months: int = 1, lang: str = "EN") -> dict[str, Any]:
    """Price a package. Extra languages are +60/month on top of the package."""
    key = lang_key(lang)
    row = tier(tier_id)
    try:
        languages = int(languages)
    except (TypeError, ValueError) as exc:
        raise PlaybookError(f"Languages must be a whole number, got {languages!r}") from exc
    if languages < 1:
        raise PlaybookError("A package covers at least one language.")
    months = max(1, int(months))

    included = int(row.get("languages_included", 1) or 1) if row["monthly"] else 1
    if not row["monthly"] and languages > 1:
        raise PlaybookError(
            "The Free Sample covers one language — it is capped at an hour of work. "
            f"Quote a paid package for {languages} languages."
        )
    extra_langs = max(0, languages - included)
    extra_monthly = extra_langs * EXTRA_LANGUAGE_MONTHLY

    setup = float(row.get("setup", 0.0))
    monthly = float(row.get("monthly", 0.0)) + extra_monthly
    lines = [f"{row['name'][key]} — {row['includes'][key]} — {_eur(row['monthly'])}/mo"
             if row["monthly"] else f"{row['name'][key]} — {row['includes'][key]}"]
    if setup:
        lines.append(f"Setup — {_eur(setup)} one-off")
    if extra_langs:
        lines.append(f"Extra language{'s' if extra_langs > 1 else ''} — "
                     f"+{_eur(EXTRA_LANGUAGE_MONTHLY)}/mo each ({extra_langs})")
    return {
        "tier": tier_id,
        "name": row["name"][key],
        "currency": CURRENCY,
        "languages": languages,
        "extra_languages": extra_langs,
        "setup": setup,
        "monthly": round(monthly, 2),
        "months": months,
        "first_month": round(setup + monthly, 2),
        "total": round(setup + monthly * months, 2),
        "total_display": _eur(setup + monthly * months),
        "lines": lines,
    }


# ---------------------------------------------------------------- closing

CLOSING = {
    "en": """Subject: {business} — the plan, and the number

{first_name},

You told me what you want: {goals}. So here's what I'd run, and what it costs.

RECOMMENDED
{name} — {price}
{includes}

WHY THIS ONE
{reason}

OPTIONAL
{optional}

FIRST STEP
{first_step}

Two ways forward: reply "go" and I start {start_date}, or tell me the one thing to change and I'll re-price it today.

{sender}""",
    "es": """Asunto: {business} — el plan y el precio

{first_name},

Me dijiste lo que quieres: {goals}. Así que esto es lo que pondría en marcha, y lo que cuesta.

RECOMENDADO
{name} — {price}
{includes}

POR QUÉ ESTE
{reason}

OPCIONAL
{optional}

PRIMER PASO
{first_step}

Dos formas de avanzar: responde "dale" y arranco el {start_date}, o dime la única cosa que cambiarías y te lo reprécifico hoy.

{sender}""",
}

#: Closing is EN/ES only, by design — the two languages the launch market buys in.
CLOSING_LANGUAGES: tuple[str, ...] = ("EN", "ES")


def closing_draft(
    lead: dict[str, Any],
    goals: str,
    tier_id: str = "social_growth",
    languages: int = 1,
    lang: str = "ES",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The closing message for a prospect who has already stated their goals.

    Refuses to build an offer on the reserved extras, and refuses to send.
    """
    code = normalize_lang(lang)
    if code not in CLOSING_LANGUAGES:
        raise PlaybookError(
            f"Closing messages are written in EN and ES only; '{code}' was requested. "
            "Use outreach_draft for FR first contact."
        )
    if not str(goals).strip():
        raise PlaybookError("A closing message needs the prospect's own goals. Ask before you close.")

    row = tier(tier_id)
    services = [row.get("service") or "social_media"]
    assert_core_offer(services)
    priced = quote(tier_id, languages, 1, code)

    first_name = (lead.get("name") or "").strip().split(" ") or [""]
    ctx: dict[str, Any] = {
        "first_name": first_name[0] or "{first_name}",
        "business": lead.get("business") or "{business}",
        "goals": goals.strip(),
        "name": priced["name"],
        "price": f"{_eur(priced['monthly'])}/mo" if priced["monthly"] else _eur(0.0),
        "includes": priced["lines"][0],
        "reason": "{reason}",
        "optional": "· " + " · ".join(
            f"{t['name'][code.lower()]} — {t['includes'][code.lower()]}"
            for t in PRICING if t["id"] != tier_id
        ),
        "first_step": "{first_step}",
        "start_date": as_str(_today() + timedelta(days=7)),
        "sender": SIGNOFF,
    }
    if extra:
        ctx.update({k: v for k, v in extra.items() if v not in (None, "")})
    body = _fill(CLOSING[code.lower()], ctx)
    subject, _, rest = body.partition("\n")
    return {
        "kind": "closing",
        "lead_id": lead.get("id"),
        "business": lead.get("business"),
        "language": code,
        "tier": tier_id,
        "quote": priced,
        "subject": subject.replace("Subject:", "").replace("Asunto:", "").strip(),
        "body": rest.strip(),
        "unfilled": draft_gaps(rest),
        "ready_for_review": not draft_gaps(rest),
        "status": "draft",
        "requires_approval": True,
        "sent": False,
        "sent_by_human": False,
    }


# ---------------------------------------------------------------- approval gate

#: The five-point checklist. All five, or nothing runs.
APPROVAL_CHECKLIST: list[dict[str, Any]] = [
    {
        "step": 1, "key": "niche_city",
        "label": {"en": "Niche and city chosen", "es": "Nicho y ciudad elegidos", "fr": "Niche et ville choisis"},
        "detail": {"en": "One niche from the twenty categories, and one city.",
                   "es": "Un nicho de las veinte categorías y una ciudad.",
                   "fr": "Une des vingt niches, et une ville."},
    },
    {
        "step": 2, "key": "outreach_drafts",
        "label": {"en": "Outreach drafts approved", "es": "Borradores de contacto aprobados", "fr": "Brouillons d'approche approuvés"},
        "detail": {"en": "First touch, day 3 and day 7, in EN, ES and FR.",
                   "es": "Primer contacto, día 3 y día 7, en EN, ES y FR.",
                   "fr": "Premier contact, jour 3 et jour 7, en EN, ES et FR."},
    },
    {
        "step": 3, "key": "pricing",
        "label": {"en": "Pricing and offers confirmed", "es": "Precios y ofertas confirmados", "fr": "Tarifs et offres confirmés"},
        "detail": {"en": "The launch tiers, in euro, as they will be quoted.",
                   "es": "Las tarifas de lanzamiento, en euros, tal como se cotizarán.",
                   "fr": "Les tarifs de lancement, en euros, tels qu'ils seront cités."},
    },
    {
        "step": 4, "key": "duration",
        "label": {"en": "Campaign duration approved", "es": "Duración de la campaña aprobada", "fr": "Durée de campagne approuvée"},
        "detail": {"en": f"The {CAMPAIGN_DAYS}-day window and its start date.",
                   "es": f"La ventana de {CAMPAIGN_DAYS} días y su fecha de inicio.",
                   "fr": f"La fenêtre de {CAMPAIGN_DAYS} jours et sa date de début."},
    },
    {
        "step": 5, "key": "sample_files",
        "label": {"en": "Sample files selected to polish", "es": "Muestras seleccionadas para pulir", "fr": "Échantillons à finaliser choisis"},
        "detail": {"en": "Which of the five sample works get polished first.",
                   "es": "Cuáles de las cinco muestras se pulen primero.",
                   "fr": "Lesquels des cinq échantillons finaliser en premier."},
    },
]

#: Review happens in the open — a PR or an issue, not a chat message.
APPROVAL_VIA = "pull_request"


def empty_approvals() -> dict[str, Any]:
    """The checklist with nothing ticked. This is the state a campaign starts in."""
    return {
        "niche": "", "city": "",
        "outreach_drafts": {"approved": False, "kinds": [], "languages": []},
        "pricing": {"approved": False, "tiers": []},
        "duration_days": 0, "duration_approved": False, "start_date": "",
        "sample_files": [],
        "approvals": [],
    }


def record_approval(approvals: dict[str, Any], key: str, by: str, note: str = "",
                    ref: str = "") -> dict[str, Any]:
    """Stamp one checklist item as approved. Returns a copy; writes nothing."""
    known = {row["key"] for row in APPROVAL_CHECKLIST}
    if key not in known:
        raise PlaybookError(f"Unknown checklist item '{key}'. Use one of: {', '.join(sorted(known))}")
    if not by.strip():
        raise PlaybookError("An approval needs the name of the human who gave it.")
    updated = dict(approvals)
    updated["approvals"] = list(approvals.get("approvals", [])) + [{
        "key": key, "by": by.strip(), "note": note, "ref": ref,
        "at": as_str(_today()), "via": APPROVAL_VIA,
    }]
    return updated


def checklist(approvals: dict[str, Any] | None = None, lang: str = "EN") -> list[dict[str, Any]]:
    """The five points with their current state. This is the operator's screen."""
    code_key = lang_key(lang)
    a = approvals or empty_approvals()
    drafts = a.get("outreach_drafts") or {}
    pricing = a.get("pricing") or {}
    state = {
        "niche_city": bool(a.get("niche")) and bool(a.get("city")),
        "outreach_drafts": bool(drafts.get("approved"))
        and set(OUTREACH_ORDER).issubset(set(drafts.get("kinds") or []))
        and set(LANGUAGES).issubset({normalize_lang(x) for x in (drafts.get("languages") or [])}),
        "pricing": bool(pricing.get("approved")) and bool(pricing.get("tiers")),
        "duration": bool(a.get("duration_approved")) and int(a.get("duration_days") or 0) > 0
        and bool(a.get("start_date")),
        "sample_files": bool(a.get("sample_files")),
    }
    evidence = {
        "niche_city": f"{a.get('niche') or '—'} · {a.get('city') or '—'}",
        "outreach_drafts": f"{len(drafts.get('kinds') or [])}/3 steps · "
                           f"{len(drafts.get('languages') or [])}/3 languages",
        "pricing": ", ".join(pricing.get("tiers") or []) or "—",
        "duration": f"{a.get('duration_days') or 0} days from {a.get('start_date') or '—'}",
        "sample_files": ", ".join(a.get("sample_files") or []) or "—",
    }
    out: list[dict[str, Any]] = []
    for row in APPROVAL_CHECKLIST:
        key = row["key"]
        out.append({
            "step": row["step"],
            "key": key,
            "label": row["label"][code_key],
            "detail": row["detail"][code_key],
            "done": state[key],
            "evidence": evidence[key],
            "approved_by": next((x["by"] for x in reversed(a.get("approvals", [])) if x["key"] == key), ""),
        })
    return out


def missing_approvals(approvals: dict[str, Any] | None = None, lang: str = "EN") -> list[dict[str, Any]]:
    return [row for row in checklist(approvals, lang) if not row["done"]]


def is_ready(approvals: dict[str, Any] | None = None) -> bool:
    return not missing_approvals(approvals)


def assert_ready(approvals: dict[str, Any] | None = None, lang: str = "EN") -> None:
    """Raise unless all five points are signed off. The gate every run goes through."""
    missing = missing_approvals(approvals, lang)
    if missing:
        raise ApprovalRequired(missing)


def checklist_markdown(approvals: dict[str, Any] | None = None, lang: str = "EN") -> str:
    """The checklist as a PR body. Approval happens here, in the open."""
    rows = checklist(approvals, lang)
    out = [f"## Playbook approval — {len([r for r in rows if not r['done']])} of {len(rows)} open", ""]
    for row in rows:
        mark = "x" if row["done"] else " "
        out.append(f"- [{mark}] **{row['step']}. {row['label']}** — {row['evidence']}")
        out.append(f"      {row['detail']}")
    out += ["", "> Nothing sends until all five are ticked. MIM drafts; a human approves and sends."]
    return "\n".join(out)


def review_bundle(lead: dict[str, Any], extra: dict[str, Any] | None = None) -> str:
    """One lead's full three-language sequence as a reviewable PR body."""
    out = [f"## Outreach review — {lead.get('business', '[business]')}", "",
           f"- Lead: `{lead.get('id')}` · channel: {lead.get('channel')}",
           f"- Signal spotted: {lead.get('signal')}",
           f"- Qualification: {qualify(lead)['score']}/5 matched ({qualify(lead)['verdict']})", ""]
    per_lang = isinstance(extra, dict) and set(LANGUAGES).issubset(extra)
    for code in LANGUAGES:
        out.append(f"### {code}")
        for draft in outreach_set(lead, code, extra.get(code) if per_lang else extra):
            flag = "ready" if draft["ready_for_review"] else f"UNFILLED: {', '.join(draft['unfilled'])}"
            out += [f"**{draft['step']}** — {flag}", "", "```", draft["body"], "```", ""]
    out.append("> Human approval required before any of this is sent. MIM does not send.")
    return "\n".join(out)


# ---------------------------------------------------------------- campaign run

def plan_campaign(
    approvals: dict[str, Any] | None,
    leads: list[dict[str, Any]],
    start: date | str | None = None,
    lang: str = "EN",
) -> dict[str, Any]:
    """Build the run plan — after the gate, and still without sending anything.

    Raises :class:`ApprovalRequired` unless all five checklist items are
    signed off. Even then, every message in the returned plan is a draft
    marked ``requires_approval``.
    """
    assert_ready(approvals, lang)
    code = normalize_lang(lang)
    approvals = approvals or empty_approvals()
    day_one = parse_date(start) or parse_date(approvals.get("start_date")) or _today()

    messages: list[dict[str, Any]] = []
    for lead in leads:
        if lead.get("message_sent"):
            continue
        messages.append(outreach_draft("first_touch", lead, lead.get("language") or code))
    unfinished = [m for m in messages if not m["ready_for_review"]]

    return {
        "status": "pending_human_send",
        "requires_approval": True,
        "sent": False,
        "campaign": CAMPAIGN_NAME,
        "niche": approvals.get("niche"),
        "city": approvals.get("city"),
        "window": f"{as_str(day_one)} → {as_str(day_one + timedelta(days=CAMPAIGN_DAYS - 1))}",
        "timeline": campaign_timeline(day_one),
        "messages": messages,
        "messages_ready": len(messages) - len(unfinished),
        "messages_needing_edit": [
            {"lead_id": m["lead_id"], "business": m["business"], "unfilled": m["unfilled"]} for m in unfinished
        ],
        "due_followups": due_followups(leads, day_one),
        "summary": campaign_summary(leads, day_one),
    }


# ---------------------------------------------------------------- persistence

def load_state() -> dict[str, Any]:
    """Leads and approvals from ``data/playbook.json``."""
    state = _load("playbook", None)
    if not isinstance(state, dict):
        state = {}
    state.setdefault("leads", [])
    state.setdefault("approvals", empty_approvals())
    return state


def save_state(state: dict[str, Any]) -> dict[str, Any]:
    """Persist leads and approvals. Writes the file; sends nothing."""
    payload = {"leads": state.get("leads", []), "approvals": state.get("approvals") or empty_approvals()}
    _save("playbook", payload)
    return payload


def add_lead(lead: dict[str, Any], state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Append a lead and persist. The tracker is a file, not a memory."""
    current = state if state is not None else load_state()
    leads = list(current.get("leads", []))
    leads.append(lead)
    current["leads"] = leads
    save_state(current)
    return current


def log_sent(lead_id: str, on: date | str | None = None, state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Record that the operator sent the first message themselves.

    This is a log, not an action — the message left from the operator's own
    account before this was called.
    """
    current = state if state is not None else load_state()
    found = False
    for lead in current.get("leads", []):
        if lead.get("id") == lead_id:
            lead["message_sent"] = True
            lead["date"] = as_str(parse_date(on) or _today())
            steps = list(lead.get("sent_steps") or [])
            if "first_touch" not in steps:
                steps.append("first_touch")
            lead["sent_steps"] = steps
            lead["next_step"] = "Day 3 — offer the free sample."
            found = True
    if not found:
        raise PlaybookError(f"No lead with id '{lead_id}'.")
    save_state(current)
    return current


def log_step_sent(lead_id: str, kind: str, on: date | str | None = None,
                  state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Record that the operator sent one follow-up themselves.

    A log, not an action: the message already left from the operator's own
    account. Recording it is what stops the cadence nagging for it again.
    """
    if kind not in OUTREACH_ORDER:
        raise PlaybookError(f"Unknown outreach step '{kind}'. Use one of: {', '.join(OUTREACH_ORDER)}")
    current = state if state is not None else load_state()
    found = False
    for lead in current.get("leads", []):
        if lead.get("id") == lead_id:
            steps = list(lead.get("sent_steps") or [])
            if kind not in steps:
                steps.append(kind)
            lead["sent_steps"] = steps
            if not lead.get("date"):
                lead["date"] = as_str(parse_date(on) or _today())
            nxt = {"first_touch": "Day 3 — offer the free sample.",
                   "day3_reminder": "Day 7 — final polite note, then close.",
                   "day7_final": "Closed. Log the outcome."}[kind]
            lead["next_step"] = nxt
            found = True
    if not found:
        raise PlaybookError(f"No lead with id '{lead_id}'.")
    save_state(current)
    return current


# ---------------------------------------------------------------- status cli


def status(lang: str = "EN") -> str:
    """Where the playbook stands right now: the gate, the tracker, what is due."""
    code_key = lang_key(lang)
    state = load_state()
    leads = state["leads"]
    approvals = state["approvals"]
    rows = checklist(approvals, lang)
    open_items = [r for r in rows if not r["done"]]

    head = {"en": "Playbook status", "es": "Estado del playbook", "fr": "État du playbook"}[code_key]
    out = [head.upper(), "=" * len(head), "", checklist_markdown(approvals, lang), ""]

    due = due_followups(leads)
    out += [f"TRACKER — {len(leads)} lead(s)", tracker_markdown(leads) if leads else "(empty)", ""]
    out += [f"DUE OR OVERDUE — {len(due)} follow-up(s)"]
    out += [f"· {row['business']} ({row['kind']}, day {row['day']}, {row['days_late']}d late)" for row in due]

    if open_items:
        out += ["", "BLOCKED — the campaign cannot run until these are approved:"]
        out += [f"· {row['step']}. {row['label']}" for row in open_items]
    else:
        out += ["", "CLEARED — every approval is in. Drafts are ready; sending is still yours."]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    import sys

    args = list(sys.argv[1:] if argv is None else argv)
    lang = args[0] if args else "EN"
    print(status(lang))
    return 1 if missing_approvals(load_state()["approvals"], lang) else 0


if __name__ == "__main__":
    raise SystemExit(main())
