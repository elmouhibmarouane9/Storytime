"""Pillar 4 — Client Communications.

Brand voice: confident, cinematic, direct, bilingual. Every template is written
by hand, not generated boilerplate, and every draft is yours to edit before it
leaves. Nothing in this module sends anything on its own.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from .models import days_since, money, parse_date

BRAND_VOICE = (
    "Confident. Cinematic. Direct. We sell outcomes, not hours. Short sentences, "
    "no hedging, no 'just checking in'. Every message ends with a decision or a next step."
)

OPENERS = {
    "en": ["Here's where we are.", "Straight to it.", "Short version:", "One decision needed."],
    "es": ["Directo al punto:", "Aquí está la situación.", "Versión corta:", "Una decisión pendiente."],
}

SIGNOFF = {
    "en": "— MEM Digital",
    "es": "— MEM Digital",
}


def _safe_fill(template: str, ctx: dict[str, Any]) -> str:
    class _Missing(dict):
        def __missing__(self, key):  # leave unknown slots visible rather than crash
            return f"[{key}]"

    return template.format_map(_Missing(**ctx))


# ---------------------------------------------------------------- templates

TEMPLATES: dict[str, dict[str, str]] = {
    "lead_followup": {
        "en": """Subject: {company} — the story we're not telling yet

{name},

We met. You liked the direction. Then the week got loud and nothing shipped. I'm not here to chase you — I'm here to give you one idea worth replying to.

Three moves I'd make for {company} in the next 30 days:
1. {hook_1}
2. {hook_2}
3. {hook_3}

No deck, no discovery call theatre. If that's the direction, reply "go" and I'll send the scope and the number the same day.

{sender}""",
        "es": """Asunto: {company} — la historia que aún no contamos

{name},

Nos conocimos. Te gustó la dirección. Luego la semana se llenó y nada salió. No escribo para perseguirte — escribo para darte una idea que valga una respuesta.

Tres movimientos que haría para {company} en 30 días:
1. {hook_1}
2. {hook_2}
3. {hook_3}

Sin presentaciones eternas ni llamadas de relleno. Si es el camino, responde "dale" y te envío alcance y precio el mismo día.

{sender}""",
    },
    "proposal_send": {
        "en": """Subject: {company} — proposal: {project}

{name},

Proposal's attached. It's built to be decided on, not studied.

THE OUTCOME
{outcome}

WHAT WE DO
{scope}

INVESTMENT
{investment} — {terms}

TIMELINE
{timeline}

Two ways to move: reply "approved" and I start {start_date}, or tell me the one thing that's wrong and I'll fix it today.

{sender}""",
        "es": """Asunto: {company} — propuesta: {project}

{name},

La propuesta va adjunta. Está hecha para decidirse, no para estudiarse.

EL RESULTADO
{outcome}

QUÉ HACEMOS
{scope}

INVERSIÓN
{investment} — {terms}

CRONOGRAMA
{timeline}

Dos formas de avanzar: responde "aprobado" y arranco el {start_date}, o dime la única cosa que no cuadra y la corrijo hoy.

{sender}""",
    },
    "proposal_nudge": {
        "en": """Subject: {company} — one question on the proposal

{name},

You've had the proposal for {days} days. Silence usually means one of two things: the timing is wrong, or the number is wrong.

Tell me which one and we'll either move or shelve it cleanly. If it's timing — what needs to be true before you say yes?

{sender}""",
        "es": """Asunto: {company} — una pregunta sobre la propuesta

{name},

Llevas {days} días con la propuesta. El silencio suele significar una de dos cosas: el momento es equivocado, o el número es equivocado.

Dime cuál y avanzamos o lo archivamos limpio. Si es el momento — ¿qué tiene que pasar para que digas sí?

{sender}""",
    },
    "onboarding": {
        "en": """Subject: {company} — we're live Monday

{name},

Welcome aboard. Here's the only email you need this week.

1. Access: send over {access} today and I'll load everything before {start_date}.
2. Points of contact: you + me, one decision-maker brief. Approvals in 48 hours keeps the calendar honest.
3. Cadence: {cadence}.

First win lands by {first_win}. I'll send the kickoff note the moment access is in.

{sender}""",
        "es": """Asunto: {company} — arrancamos el lunes

{name},

Bienvenido a bordo. Este es el único correo que necesitas esta semana.

1. Accesos: mándame {access} hoy y cargo todo antes del {start_date}.
2. Contactos: tú y yo, un brief con quien decide. Aprobaciones en 48 horas para que el calendario se mantenga honesto.
3. Ritmo: {cadence}.

El primer resultado llega antes del {first_win}. Aviso de arranque en cuanto tenga los accesos.

{sender}""",
    },
    "project_update": {
        "en": """Subject: {company} — {project}: week {week} update

{name},

Status: {progress}% complete. {status_line}

Shipped this week
{shipped}

Next
{next}

Needs from you
{asks}

{sender}""",
        "es": """Asunto: {company} — {project}: informe semana {week}

{name},

Estado: {progress}% completado. {status_line}

Esta semana
{shipped}

Siguiente
{next}

Necesito de ti
{asks}

{sender}""",
    },
    "approval_request": {
        "en": """Subject: {company} — approval needed: {deliverable}

{name},

{deliverable} is ready for your eyes. This is the 48-hour gate — your sign-off keeps the next milestone on schedule.

What I need: approve, or one round of notes. That's it.
Where it lives: {link}
If I hear nothing by {deadline}, I'll hold the release and the schedule shifts.

{sender}""",
        "es": """Asunto: {company} — aprueba: {deliverable}

{name},

{deliverable} está listo para tu revisión. Esta es la ventana de 48 horas — tu firma mantiene la siguiente etapa en calendario.

Lo que necesito: aprobar, o una ronda de comentarios. Nada más.
Dónde verlo: {link}
Si no tengo respuesta para el {deadline}, retengo la publicación y el cronograma se corre.

{sender}""",
    },
    "approval_chase": {
        "en": """Subject: {company} — {deliverable}: day {days} of silence

{name},

{deliverable} has been sitting in approval for {days} days. Each day costs you {cost_note}.

Two paths, pick one today:
· Reply "go" — I ship it and we stay on plan.
· Reply "hold" — I stop the clock, park the milestone and we re-book the date.

Either is fine. Drift isn't.

{sender}""",
        "es": """Asunto: {company} — {deliverable}: {days} días sin respuesta

{name},

{deliverable} lleva {days} días esperando aprobación. Cada día cuesta {cost_note}.

Dos caminos, elige uno hoy:
· Responde "ya" — lo publico y seguimos en plan.
· Responde "en pausa" — paro el reloj, aparco el hito y reagendamos.

Cualquiera está bien. La deriva no.

{sender}""",
    },
    "invoice_send": {
        "en": """Subject: {company} — invoice {invoice} · {amount}

{name},

Invoice {invoice} for {amount} is attached. Work delivered: {work}.
Due {due} ({terms}).

Payment details are on the invoice. Any issue with it, tell me today so I can fix it before Friday.

{sender}""",
        "es": """Asunto: {company} — factura {invoice} · {amount}

{name},

Adjunto la factura {invoice} por {amount}. Trabajo entregado: {work}.
Vence el {due} ({terms}).

Los datos de pago están en la factura. Si algo no cuadra, dímelo hoy para corregirlo antes del viernes.

{sender}""",
    },
    "reminder_1": {
        "en": """Subject: {company} — invoice {invoice} cleared?

{name},

Invoice {invoice} ({amount}) was due {due}. Likely an admin slip, not a statement — flagging it so your accounts team can close it out.

Pay link / details on the invoice. If it's already scheduled, ignore this and we're square.

{sender}""",
        "es": """Asunto: {company} — ¿factura {invoice} pagada?

{name},

La factura {invoice} ({amount}) venció el {due}. Probablemente un tema administrativo, no un problema — te aviso para que contabilidad lo cierre.

Datos de pago en la factura. Si ya está programada, ignora esto y estamos en paz.

{sender}""",
    },
    "reminder_2": {
        "en": """Subject: {company} — {amount} outstanding on {invoice}

{name},

Invoice {invoice} is {days} days past due. {amount} outstanding. I need this settled this week to keep {project} resourced and on schedule.

Confirm today: (1) payment date, or (2) who on your side I should speak to.

{sender}""",
        "es": """Asunto: {company} — {amount} pendiente en {invoice}

{name},

La factura {invoice} lleva {days} días vencida. {amount} pendientes. Necesito cerrarlo esta semana para mantener {project} con recursos y en calendario.

Confírmame hoy: (1) fecha de pago, o (2) con quién de tu equipo debo hablar.

{sender}""",
    },
    "reminder_3": {
        "en": """Subject: {company} — final notice: invoice {invoice}

{name},

Invoice {invoice} — {days} days past due, {amount} outstanding. Reminders have gone unanswered, so this is the formal step.

Payment or a written plan by {deadline}, otherwise {escalation}. I'd rather keep this between us and get back to the work.

{sender}""",
        "es": """Asunto: {company} — aviso final: factura {invoice}

{name},

Factura {invoice} — {days} días vencida, {amount} pendiente. Los recordatorios quedaron sin respuesta, así que este es el paso formal.

Pago o un plan por escrito antes del {deadline}; de lo contrario {escalation}. Prefiero mantener esto entre nosotros y volver al trabajo.

{sender}""",
    },
    "gap_nudge": {
        "en": """Subject: {company} — checking the silence

{name},

{days} days since we last spoke — that's longer than we run. My fault as much as yours, so here's the fix: {move}

Reply with a yes and I'll handle the rest.

{sender}""",
        "es": """Asunto: {company} — el silencio

{name},

{days} días desde la última conversación — más de lo que acostumbramos. Tanto mi culpa como tuya, así que aquí va la solución: {move}

Responde con un sí y yo me encargo del resto.

{sender}""",
    },
    "upsell": {
        "en": """Subject: {company} — what {company} should do next

{name},

{trigger}

Here's what I'd put in phase two: {offer}
Why now: {why_now}

Investment: {amount}. I can start {start_date} and have the first result by {first_win}.

Say the word and I'll send the one-page scope.

{sender}""",
        "es": """Asunto: {company} — lo que sigue para {company}

{name},

{trigger}

Esto es lo que pondría en la fase dos: {offer}
Por qué ahora: {why_now}

Inversión: {amount}. Puedo arrancar el {start_date} y tener el primer resultado para el {first_win}.

Dame la señal y te envío el alcance de una página.

{sender}""",
    },
    "change_order": {
        "en": """Subject: {company} — change order: {title}

{name},

{reason}

Scope added: {scope}
Impact: {hours}h · {amount}
Schedule: {schedule_impact}

Approve below and it goes straight onto the next invoice. Decline and I'll park the work and keep the original scope intact.

Reply "approved" or "decline". Nothing else needed.

{sender}""",
        "es": """Asunto: {company} — orden de cambio: {title}

{name},

{reason}

Alcance añadido: {scope}
Impacto: {hours}h · {amount}
Cronograma: {schedule_impact}

Apruébala y entra directo a la próxima factura. Si la rechazas, aparco el trabajo y mantengo el alcance original intacto.

Responde "aprobado" o "rechazado". Nada más.

{sender}""",
    },
    "testimonial_ask": {
        "en": """Subject: {company} — 3 questions, 3 minutes

{name},

{result} — that's worth saying out loud.

Three questions, answers by voice note if easier:
1. What was the problem before we started?
2. What changed?
3. Who would you send us to?

I'll shape it into a case study and send you the draft before anything goes public.

{sender}""",
        "es": """Asunto: {company} — 3 preguntas, 3 minutos

{name},

{result} — vale la pena decirlo en voz alta.

Tres preguntas, respuestas por nota de voz si es más fácil:
1. ¿Cuál era el problema antes de empezar?
2. ¿Qué cambió?
3. ¿A quién nos recomendarías?

Lo convierto en caso de estudio y te envío el borrador antes de publicar nada.

{sender}""",
    },
}


DEFAULT_CONTEXT: dict[str, Any] = {
    "hook_1": "re-cut the offer so the offer is the hook",
    "hook_2": "build the 30-day content sprint around it",
    "hook_3": "put paid behind the one message that already converts",
    "outcome": "[the business result, in numbers]",
    "scope": "[what we do, in 4 lines max]",
    "investment": "[price + payment terms]",
    "terms": "Net 14",
    "timeline": "[weeks, milestones, dates]",
    "start_date": "[start date]",
    "days": "[n]",
    "access": "ad account, domain, and analytics",
    "project": "[project]",
    "cadence": "weekly written update, monthly strategy call",
    "first_win": "[first measurable win]",
    "progress": "[n]",
    "status_line": "",
    "shipped": "· [item]",
    "next": "· [item]",
    "asks": "· [decision or asset]",
    "deliverable": "[deliverable]",
    "link": "[link]",
    "deadline": "[date]",
    "cost_note": "a day of schedule",
    "invoice": "[invoice id]",
    "amount": "[amount]",
    "work": "[what was delivered]",
    "due": "[due date]",
    "escalation": "the account moves to prepay",
    "move": "[the smallest next step]",
    "trigger": "[why now]",
    "offer": "[phase two scope]",
    "why_now": "[the cost of waiting]",
    "title": "[change order title]",
    "reason": "This sits outside the signed scope — flagging it before it becomes a silent cost.",
    "scope": "[what was added]",
    "hours": "[n]",
    "schedule_impact": "no change" ,
    "result": "[the result you delivered]",
    "week": "[n]",
}


def context_from(client: dict | None, extra: dict[str, Any] | None = None, lang: str = "en") -> dict[str, Any]:
    ctx: dict[str, Any] = dict(DEFAULT_CONTEXT)
    ctx["sender"] = SIGNOFF[lang]
    if client:
        ctx.update({
            "name": (client.get("name") or "").split(" ")[0] or "there",
            "company": client.get("company") or client.get("name") or "[company]",
            "currency": client.get("currency", "USD"),
        })
    if extra:
        ctx.update({k: v for k, v in extra.items() if v not in (None, "")})
    return ctx


def kinds() -> list[tuple[str, str]]:
    labels = {
        "lead_followup": "Lead follow-up",
        "proposal_send": "Proposal delivery",
        "proposal_nudge": "Proposal decision nudge",
        "onboarding": "Kickoff / onboarding",
        "project_update": "Weekly project update",
        "approval_request": "Approval request",
        "approval_chase": "Approval chase (silence)",
        "invoice_send": "Invoice delivery",
        "reminder_1": "Reminder 1 · soft",
        "reminder_2": "Reminder 2 · firm",
        "reminder_3": "Reminder 3 · final notice",
        "gap_nudge": "Re-open a cold thread",
        "upsell": "Upsell / phase two",
        "change_order": "Change order",
        "testimonial_ask": "Testimonial / case study ask",
    }
    return list(labels.items())


def render(kind: str, client: dict | None, extra: dict[str, Any] | None = None, lang: str = "EN") -> tuple[str, str]:
    """Return (subject, body) for the requested kind, in EN or ES."""
    code = "es" if str(lang).lower().startswith("es") else "en"
    template = TEMPLATES.get(kind, {}).get(code)
    if template is None:
        raise KeyError(f"Unknown template: {kind}")
    ctx = context_from(client, extra, code)
    text = _safe_fill(template, ctx)
    subject, _, body = text.partition("\n")
    subject = subject.replace("Subject:", "").replace("Asunto:", "").strip()
    return subject, body.strip()


def reminder_for(invoice: dict, client: dict | None, today: date, lang: str = "EN") -> tuple[str, str]:
    from .finance import days_overdue, invoice_balance, invoice_total, reminder_tier

    tier = reminder_tier(invoice, today)
    kind = {0: "reminder_1", 1: "reminder_1", 2: "reminder_2", 3: "reminder_3"}[tier]
    extra = {
        "invoice": invoice.get("id", "—"),
        "amount": money(invoice_balance(invoice), invoice.get("currency", "USD")),
        "due": invoice.get("due_date", "—"),
        "days": days_overdue(invoice, today),
        "project": invoice.get("project_name") or "the work",
        "deadline": "[date]",
        "escalation": "the account moves to prepay",
    }
    subject, body = render(kind, client, extra, lang)
    if tier == 0:
        subject = subject.replace("cleared?", "on the way?")
    return subject, body


# ---------------------------------------------------------------- intelligence

QUESTION_HINTS = ("?", "can you", "could you", "when", "what", "how", "confirm", "advise", "please")
COMMITMENT_HINTS = ("i will", "we will", "i'll", "we'll", "will send", "will get", "by monday", "by friday", "next week", "tomorrow")
DECISION_HINTS = ("approved", "approve", "signed", "agreed", "let's go", "go ahead", "declined", "not interested", "on hold", "confirmado", "aprobado")
DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}(?:/\d{2,4})?|(?:mon|tues|wednes|thurs|fri|satur|sun)day|today|tomorrow|next week)\b", re.I)
MONEY_RE = re.compile(r"([$€£]\s?\d[\d,\.]*|\b\d[\d,\.]*\s?(?:usd|eur|gbp|k)\b)", re.I)


def summarise_thread(text: str, lang: str = "EN") -> dict[str, Any]:
    """Rule-based read of a thread: decisions, open questions, commitments, dates, money.

    Fast, deterministic, offline. Enough to brief yourself before you reply.
    """
    lines = [ln.strip(" \t-•*") for ln in (text or "").splitlines() if ln.strip()]
    decisions, open_q, commitments, dates, numbers = [], [], [], [], []
    for line in lines:
        low = line.lower()
        if any(h in low for h in DECISION_HINTS):
            decisions.append(line)
        elif any(h in low for h in QUESTION_HINTS):
            open_q.append(line)
        elif any(h in low for h in COMMITMENT_HINTS):
            commitments.append(line)
        for hit in DATE_RE.findall(line):
            dates.append(f"{hit} ← {line[:80]}")
        for hit in MONEY_RE.findall(line):
            numbers.append(f"{hit} ← {line[:80]}")
    if decisions:
        next_step = "Confirm in writing — decisions die in DMs."
    elif open_q:
        next_step = f"Answer the {len(open_q)} open question(s) directly. One reply, numbered."
    elif commitments:
        next_step = "Log the commitments and set due dates on your side."
    else:
        next_step = "No decision on the table. Send one specific ask."
    headline = decisions[0] if decisions else (open_q[0] if open_q else (lines[0] if lines else "Empty thread"))
    return {
        "headline": headline[:160],
        "decisions": _dedupe(decisions),
        "questions": _dedupe(open_q),
        "commitments": _dedupe(commitments),
        "dates": _dedupe(dates),
        "money": _dedupe(numbers),
        "next_step": next_step,
        "stats": {"lines": len(lines), "questions": len(open_q), "decisions": len(decisions)},
    }


def _dedupe(rows: list[str], limit: int = 8) -> list[str]:
    seen, out = set(), []
    for row in rows:
        key = row.lower()[:80]
        if key in seen:
            continue
        seen.add(key)
        out.append(row[:220])
    return out[:limit]


def update_email_body(project: dict, tasks_shipped: list[str], tasks_next: list[str], asks: list[str], client: dict | None, today: date, lang: str = "EN") -> tuple[str, str]:
    from .projects import deadline_risk, project_progress

    risk = deadline_risk(project, today)
    extra = {
        "project": project.get("name", "[project]"),
        "progress": f"{project_progress(project):.0f}",
        "status_line": risk["message"],
        "shipped": "\n".join(f"· {t}" for t in tasks_shipped) or "· nothing shipped this week — see below",
        "next": "\n".join(f"· {t}" for t in tasks_next) or "· [next milestone]",
        "asks": "\n".join(f"· {a}" for a in asks) or "· nothing — heads down",
        "week": today.isocalendar().week,
    }
    return render("project_update", client, extra, lang)


def gap_move(client: dict, today: date) -> str:
    stage = client.get("stage")
    days = days_since(client.get("last_contact"), today) or 0
    if stage == "Proposal Sent":
        return "the proposal gets a yes/no call this week — 15 minutes, I'll bring the decision."
    if stage in ("Lead", "Contacted"):
        return "one idea tailored to your business, no ask attached."
    if stage == "Upsell":
        return "the phase-two scope, priced and dated."
    if stage == "Completed":
        return "a 10-minute results review and the case study draft."
    return f"a written update covering the last {days} days and what's next."


def gap_draft(client: dict, today: date, lang: str = "EN") -> tuple[str, str]:
    days = days_since(client.get("last_contact"), today) or 0
    extra = {"days": days, "move": gap_move(client, today)}
    return render("gap_nudge", client, extra, lang)


def change_order_from_flag(project: dict, flag: dict, client: dict | None, settings: dict, lang: str = "EN") -> tuple[str, str]:
    rate = float(project.get("hourly_rate", 0) or 0)
    exposure = float(flag.get("exposure", 0) or 0)
    hours = round(exposure / rate, 1) if rate else 0
    extra = {
        "title": flag.get("type", "Scope change"),
        "reason": flag.get("action", "Outside the signed scope."),
        "scope": flag.get("detail", ""),
        "hours": hours,
        "amount": money(exposure, (client or {}).get("currency", "USD")),
        "schedule_impact": "adds 2-3 working days",
    }
    return render("change_order", client, extra, lang)
