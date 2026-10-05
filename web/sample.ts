import { bookSchema, type Book } from "./domain.js";

const anchor = "2026-10-05";
const sample = {
  "settings": {
    "sample_data": true,
    "agency": {
      "name": "MEM Digital",
      "owner": "Marouane El Mouhib",
      "email": "hello@memdigital.studio",
      "phone": "+1 (555) 014-8802",
      "address": "Remote-first · serving US, EU & MENA",
      "tax_id": "TAX-0000000",
      "website": "memdigital.studio",
      "base_currency": "USD"
    },
    "brand_voice": "Confident. Cinematic. Direct. Outcomes over hours.",
    "default_language": "EN",
    "supported_languages": [
      "EN",
      "ES"
    ],
    "currency": "USD",
    "fx_rates": {
      "USD": 1.0,
      "EUR": 1.08,
      "GBP": 1.27,
      "AED": 0.27,
      "MAD": 0.1,
      "MXN": 0.058
    },
    "invoice": {
      "prefix": "MEM",
      "next_number": 4,
      "default_terms": "Net 14",
      "tax_rate": 0.0
    },
    "targets": {
      "monthly_revenue": 18000,
      "quarterly_revenue": 54000
    },
    "cadence_days": {
      "Lead": 3,
      "Contacted": 5,
      "Proposal Sent": 4,
      "Active": 7,
      "Completed": 21,
      "Upsell": 14
    },
    "reminder_policy": [
      {
        "tier": 1,
        "trigger": "-2 days to +7 days",
        "tone": "Friendly admin nudge",
        "escalation": "None"
      },
      {
        "tier": 2,
        "trigger": "8-21 days",
        "tone": "Firm, decision-forcing",
        "escalation": "Request payment date"
      },
      {
        "tier": 3,
        "trigger": "22+ days",
        "tone": "Formal final notice",
        "escalation": "Prepay terms + pause work"
      }
    ]
  },
  "clients": [
    {
      "id": "C-001",
      "name": "Daniel Voss",
      "company": "Nordwind Media",
      "email": "daniel@nordwindmedia.com",
      "phone": "+1 415 555 0117",
      "role": "CMO",
      "location": "Austin, US",
      "language": "EN",
      "stage": "Active",
      "tags": [
        "retainer",
        "slow payer"
      ],
      "deal_value": 57600,
      "currency": "USD",
      "since": "2025-08-21",
      "source": "Referral",
      "timezone": "CST",
      "communication_style": "Executive brevity. Reads the headline, forwards the detail. Hates being CC'd on noise.",
      "preferences": [
        "Numbers over adjectives",
        "Friday summaries",
        "Slack over email"
      ],
      "payment_behaviour": "Slow but reliable — pays 3-4 weeks late, always in full.",
      "notes": "Q3 retainer renewal is the upgrade window. Wants a podcast arm in 2027 budget.",
      "last_contact": "2026-09-26",
      "next_action": {
        "note": "Send Q4 plan + renewal options",
        "due": "2026-10-07"
      },
      "stage_history": [
        {
          "from": "Lead",
          "to": "Contacted",
          "date": "2025-08-21",
          "value": 57600
        },
        {
          "from": "Contacted",
          "to": "Proposal Sent",
          "date": "2025-09-05",
          "value": 57600
        },
        {
          "from": "Proposal Sent",
          "to": "Active",
          "date": "2025-09-20",
          "value": 57600
        }
      ]
    },
    {
      "id": "C-002",
      "name": "Lucía Ferrer",
      "company": "Casa Ferrer",
      "email": "lucia@casaferrer.es",
      "phone": "+34 600 555 018",
      "role": "Founder",
      "location": "Madrid, ES",
      "language": "ES",
      "stage": "Proposal Sent",
      "tags": [
        "altura",
        "DTC"
      ],
      "deal_value": 24000,
      "currency": "EUR",
      "since": "2026-08-02",
      "source": "LinkedIn",
      "timezone": "CET",
      "communication_style": "Visual thinker. Wants the story before the spreadsheet. Replies in voice notes.",
      "preferences": [
        "Spanish-first",
        "Moodboards",
        "WhatsApp for quick approvals"
      ],
      "payment_behaviour": "Pays on time when the invoice is in Spanish. Ignores English ones.",
      "notes": "Proposal for a full rebrand + launch campaign. Wants to be live in 3 weeks — timeline needs a reality check.",
      "last_contact": "2026-09-19",
      "next_action": {
        "note": "Decision nudge on proposal — offer 15-min call",
        "due": "2026-10-02"
      },
      "stage_history": [
        {
          "from": "Lead",
          "to": "Contacted",
          "date": "2026-08-02",
          "value": 24000
        },
        {
          "from": "Contacted",
          "to": "Proposal Sent",
          "date": "2026-09-19",
          "value": 24000
        }
      ]
    },
    {
      "id": "C-003",
      "name": "Omar Haddad",
      "company": "Haddad Hospitality",
      "email": "omar@haddadhospitality.ae",
      "phone": "+971 50 555 0142",
      "role": "Group Marketing Director",
      "location": "Dubai, AE",
      "language": "EN",
      "stage": "Active",
      "tags": [
        "multi-property",
        "scope creep"
      ],
      "deal_value": 42000,
      "currency": "AED",
      "since": "2026-04-08",
      "source": "Instagram",
      "timezone": "GST",
      "communication_style": "Direct, fast, transactional. Approves in one word. Expects the same.",
      "preferences": [
        "Arabic greetings land well",
        "No long decks",
        "Sunday working week"
      ],
      "payment_behaviour": "Pays early — wants suppliers who move fast.",
      "notes": "Third property added scope outside the SOW. Change orders ready to bill.",
      "last_contact": "2026-10-01",
      "next_action": {
        "note": "Push change order HAD-CO-02 to invoice",
        "due": "2026-10-06"
      },
      "stage_history": [
        {
          "from": "Lead",
          "to": "Contacted",
          "date": "2026-04-08",
          "value": 42000
        },
        {
          "from": "Proposal Sent",
          "to": "Active",
          "date": "2026-04-28",
          "value": 42000
        }
      ]
    },
    {
      "id": "C-004",
      "name": "Amelia Chen",
      "company": "Pureform Studio",
      "email": "amelia@pureform.studio",
      "phone": "+1 628 555 0193",
      "role": "Creative Director",
      "location": "San Francisco, US",
      "language": "EN",
      "stage": "Completed",
      "tags": [
        "brand-film"
      ],
      "deal_value": 8500,
      "currency": "USD",
      "since": "2026-02-15",
      "source": "Referral",
      "timezone": "PST",
      "communication_style": "Detail-obsessed on craft, loose on process. Needs deadline pressure to approve.",
      "preferences": [
        "Frame.io review links",
        "Explicit version numbers"
      ],
      "payment_behaviour": "Immediate. Wire clears same week, every time.",
      "notes": "Delivered brand film, results strong. Perfect testimonial + case study candidate. Unsold retainer.",
      "last_contact": "2026-09-05",
      "next_action": {
        "note": "Testimonial ask + retainer conversation",
        "due": "2026-10-08"
      },
      "stage_history": [
        {
          "from": "Lead",
          "to": "Proposal Sent",
          "date": "2026-02-15",
          "value": 8500
        },
        {
          "from": "Proposal Sent",
          "to": "Active",
          "date": "2026-02-21",
          "value": 8500
        },
        {
          "from": "Active",
          "to": "Completed",
          "date": "2026-09-14",
          "value": 8500
        }
      ]
    },
    {
      "id": "C-005",
      "name": "Marta Ruiz",
      "company": "Vega Health",
      "email": "marta.ruiz@vegahealth.com",
      "phone": "+34 611 555 027",
      "role": "Head of Growth",
      "location": "Barcelona, ES",
      "language": "ES",
      "stage": "Upsell",
      "tags": [
        "retainer",
        "healthtech",
        "expansion"
      ],
      "deal_value": 36000,
      "currency": "EUR",
      "since": "2025-12-09",
      "source": "Referral",
      "timezone": "CET",
      "communication_style": "Data-heavy. Wants the model, not the opinion. Challenges every number — come armed.",
      "preferences": [
        "Spanish-first",
        "Dashboard screenshots",
        "Wednesday calls"
      ],
      "payment_behaviour": "On time, every time.",
      "notes": "Upsell candidate: second retainer line to cover paid social. Strong case study material.",
      "last_contact": "2026-10-02",
      "next_action": {
        "note": "Present retainer expansion at 10% uplift",
        "due": "2026-10-06"
      },
      "stage_history": [
        {
          "from": "Lead",
          "to": "Contacted",
          "date": "2025-12-09",
          "value": 36000
        },
        {
          "from": "Contacted",
          "to": "Active",
          "date": "2025-12-24",
          "value": 36000
        },
        {
          "from": "Active",
          "to": "Completed",
          "date": "2026-08-26",
          "value": 36000
        },
        {
          "from": "Completed",
          "to": "Upsell",
          "date": "2026-09-21",
          "value": 36000
        }
      ]
    }
  ],
  "invoices": [
    {
      "id": "MEM-2026-001",
      "client_id": "C-001",
      "project_id": "P-001",
      "issue_date": "2026-07-01",
      "due_date": "2026-07-15",
      "currency": "USD",
      "terms": "Net 14",
      "status": "sent",
      "tax_rate": 0.0,
      "discount": 0,
      "notes": "Nordwind retainer — month 1",
      "items": [
        {
          "desc": "Retainer — strategy, content & paid (month 1)",
          "qty": 1,
          "rate": 4800,
          "unit": "mo"
        }
      ],
      "payments": [
        {
          "date": "2026-07-18",
          "amount": 4800,
          "method": "wire",
          "note": "Paid in full"
        }
      ],
      "reminders": []
    },
    {
      "id": "MEM-2026-002",
      "client_id": "C-001",
      "project_id": "P-001",
      "issue_date": "2026-07-31",
      "due_date": "2026-08-14",
      "currency": "USD",
      "terms": "Net 14",
      "status": "sent",
      "tax_rate": 0.0,
      "discount": 0,
      "notes": "Nordwind retainer — month 2",
      "items": [
        {
          "desc": "Retainer — strategy, content & paid (month 2)",
          "qty": 1,
          "rate": 4800,
          "unit": "mo"
        }
      ],
      "payments": [
        {
          "date": "2026-09-14",
          "amount": 2400,
          "method": "wire",
          "note": "Half now, half on month 3"
        }
      ],
      "reminders": [
        {
          "date": "2026-08-28",
          "tier": 1,
          "channel": "email"
        },
        {
          "date": "2026-09-11",
          "tier": 2,
          "channel": "email"
        }
      ]
    },
    {
      "id": "MEM-2026-003",
      "client_id": "C-001",
      "project_id": "P-001",
      "issue_date": "2026-07-20",
      "due_date": "2026-08-03",
      "currency": "USD",
      "terms": "Net 14",
      "status": "sent",
      "tax_rate": 0.0,
      "discount": 0,
      "notes": "Nordwind retainer — month 3",
      "items": [
        {
          "desc": "Retainer — strategy, content & paid (month 3)",
          "qty": 1,
          "rate": 4800,
          "unit": "mo"
        }
      ],
      "payments": [],
      "reminders": [
        {
          "date": "2026-08-22",
          "tier": 2,
          "channel": "email"
        },
        {
          "date": "2026-09-05",
          "tier": 3,
          "channel": "email"
        }
      ]
    },
    {
      "id": "MEM-2026-004",
      "client_id": "C-003",
      "project_id": "P-002",
      "issue_date": "2026-08-18",
      "due_date": "2026-09-01",
      "currency": "AED",
      "terms": "Net 14",
      "status": "sent",
      "tax_rate": 0.05,
      "discount": 0,
      "notes": "Haddad — property 1 & 2 launch sprint",
      "items": [
        {
          "desc": "Launch sprint — property 1 (strategy + creative)",
          "qty": 1,
          "rate": 18000,
          "unit": "fixed"
        },
        {
          "desc": "Property 2 social rollout",
          "qty": 1,
          "rate": 6000,
          "unit": "fixed"
        }
      ],
      "payments": [
        {
          "date": "2026-09-02",
          "amount": 21000,
          "method": "transfer",
          "note": "Partial — remainder held for snag list"
        }
      ],
      "reminders": [
        {
          "date": "2026-09-15",
          "tier": 1,
          "channel": "email"
        }
      ]
    },
    {
      "id": "MEM-2026-005",
      "client_id": "C-005",
      "project_id": "P-004",
      "issue_date": "2026-08-28",
      "due_date": "2026-09-11",
      "currency": "EUR",
      "terms": "Net 14",
      "status": "sent",
      "tax_rate": 0.0,
      "discount": 0,
      "notes": "Vega Health — content engine, phase 1",
      "items": [
        {
          "desc": "Content engine — 12 assets + distribution",
          "qty": 1,
          "rate": 7200,
          "unit": "fixed"
        }
      ],
      "payments": [],
      "reminders": [
        {
          "date": "2026-09-21",
          "tier": 1,
          "channel": "email"
        },
        {
          "date": "2026-09-28",
          "tier": 2,
          "channel": "email"
        }
      ]
    },
    {
      "id": "MEM-2026-006",
      "client_id": "C-004",
      "project_id": "P-003",
      "issue_date": "2026-09-05",
      "due_date": "2026-09-19",
      "currency": "USD",
      "terms": "Net 14",
      "status": "paid",
      "tax_rate": 0.0,
      "discount": 0,
      "source": "manual",
      "notes": "Pureform — brand film, final",
      "items": [
        {
          "desc": "Brand film — edit, grade, sound & delivery",
          "qty": 1,
          "rate": 8500,
          "unit": "fixed"
        }
      ],
      "payments": [
        {
          "date": "2026-09-11",
          "amount": 8500,
          "method": "wire",
          "note": "Paid on receipt"
        }
      ],
      "reminders": []
    },
    {
      "id": "MEM-2026-007",
      "client_id": "C-003",
      "project_id": "P-002",
      "issue_date": "2026-09-26",
      "due_date": "2026-10-10",
      "currency": "AED",
      "terms": "Net 14",
      "status": "sent",
      "tax_rate": 0.05,
      "discount": 0,
      "notes": "Haddad — change order HAD-CO-01 (third property)",
      "items": [
        {
          "desc": "Property 3 creative adaptation",
          "qty": 1,
          "rate": 3200,
          "unit": "fixed"
        }
      ],
      "payments": [],
      "reminders": []
    },
    {
      "id": "MEM-2026-008",
      "client_id": "C-005",
      "project_id": "P-004",
      "issue_date": "2026-10-03",
      "due_date": "2026-10-17",
      "currency": "EUR",
      "terms": "Net 14",
      "status": "draft",
      "tax_rate": 0.0,
      "discount": 0,
      "notes": "Vega — retainer conversion, month 1",
      "items": [
        {
          "desc": "Growth retainer — month 1",
          "qty": 1,
          "rate": 3000,
          "unit": "mo"
        }
      ],
      "payments": [],
      "reminders": []
    }
  ],
  "projects": [
    {
      "id": "P-001",
      "client_id": "C-001",
      "name": "Nordwind Retainer — Q4 Sprint",
      "status": "Active",
      "start": "2026-07-01",
      "due": "2026-10-14",
      "budget": 14400,
      "currency": "USD",
      "hourly_rate": 110,
      "included_revisions": 2,
      "scope_summary": "Monthly retainer: strategy, 8 content assets, paid media management.",
      "tasks": [
        {
          "id": "T-001",
          "name": "Q4 content calendar",
          "status": "Done",
          "progress": 100,
          "due": "2026-08-26",
          "estimated_hours": 10,
          "logged_hours": 9,
          "assignee": "MEM"
        },
        {
          "id": "T-002",
          "name": "Paid media audit",
          "status": "Done",
          "progress": 100,
          "due": "2026-09-10",
          "estimated_hours": 8,
          "logged_hours": 11,
          "assignee": "MEM"
        },
        {
          "id": "T-003",
          "name": "Content batch — month 3",
          "status": "In Progress",
          "progress": 60,
          "due": "2026-10-03",
          "estimated_hours": 16,
          "logged_hours": 12,
          "assignee": "MEM"
        },
        {
          "id": "T-004",
          "name": "Podcast pilot script",
          "status": "Not Started",
          "progress": 0,
          "due": "2026-10-10",
          "estimated_hours": 12,
          "logged_hours": 4,
          "assignee": "MEM"
        },
        {
          "id": "T-005",
          "name": "Performance review + renewal deck",
          "status": "Not Started",
          "progress": 0,
          "due": "2026-10-14",
          "estimated_hours": 6,
          "logged_hours": 0,
          "assignee": "MEM"
        }
      ],
      "deliverables": [
        {
          "name": "Q4 content calendar",
          "status": "Delivered",
          "due": "2026-08-28",
          "revisions": 2,
          "approval": {
            "state": "approved",
            "requested": "2026-08-21",
            "decided": "2026-08-26"
          }
        },
        {
          "name": "Month 3 content batch",
          "status": "In Progress",
          "due": "2026-10-06",
          "revisions": 1,
          "approval": {
            "state": "none"
          }
        },
        {
          "name": "Podcast pilot script",
          "status": "Planned",
          "due": "2026-10-11",
          "revisions": 0,
          "approval": {
            "state": "none"
          }
        }
      ],
      "time_entries": [
        {
          "id": "TE-001",
          "date": "2026-09-01",
          "task_id": "T-001",
          "hours": 9,
          "note": "Calendar build",
          "in_scope": true,
          "billable": true,
          "invoiced": true
        },
        {
          "id": "TE-002",
          "date": "2026-09-13",
          "task_id": "T-002",
          "hours": 11,
          "note": "Audit + reporting rebuild",
          "in_scope": true,
          "billable": true,
          "invoiced": true
        },
        {
          "id": "TE-003",
          "date": "2026-09-29",
          "task_id": "T-003",
          "hours": 12,
          "note": "Batch production (covered by month-3 retainer)",
          "in_scope": true,
          "billable": true,
          "invoiced": true
        },
        {
          "id": "TE-004",
          "date": "2026-10-02",
          "task_id": "T-004",
          "hours": 4,
          "note": "Podcast research (never scoped)",
          "in_scope": false,
          "billable": true,
          "invoiced": false
        }
      ],
      "change_orders": [],
      "risks": [
        "Podcast pilot is outside the retainer SOW — raise change order."
      ],
      "health_flag": "At Risk",
      "scope_exposure": true
    },
    {
      "id": "P-002",
      "client_id": "C-003",
      "name": "Haddad — Multi-Property Launch",
      "status": "Active",
      "start": "2026-08-06",
      "due": "2026-10-03",
      "budget": 24000,
      "currency": "AED",
      "hourly_rate": 420,
      "included_revisions": 2,
      "scope_summary": "Launch campaign for property 1 & 2: strategy, creative, social rollout.",
      "tasks": [
        {
          "id": "T-011",
          "name": "Property 1 launch film",
          "status": "Done",
          "progress": 100,
          "due": "2026-09-05",
          "estimated_hours": 20,
          "logged_hours": 24
        },
        {
          "id": "T-012",
          "name": "Property 2 social rollout",
          "status": "Done",
          "progress": 100,
          "due": "2026-09-19",
          "estimated_hours": 14,
          "logged_hours": 15
        },
        {
          "id": "T-013",
          "name": "Property 3 adaptation (unscheduled)",
          "status": "In Progress",
          "progress": 45,
          "due": "2026-10-09",
          "estimated_hours": 12,
          "logged_hours": 14
        },
        {
          "id": "T-014",
          "name": "Launch performance report",
          "status": "Blocked",
          "progress": 0,
          "due": "2026-10-06",
          "estimated_hours": 6,
          "logged_hours": 0
        }
      ],
      "deliverables": [
        {
          "name": "Property 1 launch film",
          "status": "Delivered",
          "due": "2026-09-05",
          "revisions": 4,
          "approval": {
            "state": "approved",
            "requested": "2026-08-24",
            "decided": "2026-08-28"
          }
        },
        {
          "name": "Property 2 creative set",
          "status": "Delivered",
          "due": "2026-09-21",
          "revisions": 2,
          "approval": {
            "state": "approved",
            "requested": "2026-09-15",
            "decided": "2026-09-17"
          }
        },
        {
          "name": "Property 3 creative adaptation",
          "status": "In Review",
          "due": "2026-10-09",
          "revisions": 0,
          "approval": {
            "state": "pending",
            "requested": "2026-09-27"
          }
        }
      ],
      "time_entries": [
        {
          "id": "TE-011",
          "date": "2026-09-01",
          "task_id": "T-011",
          "hours": 24,
          "note": "Film production",
          "in_scope": true,
          "billable": true,
          "invoiced": true
        },
        {
          "id": "TE-012",
          "date": "2026-09-17",
          "task_id": "T-012",
          "hours": 15,
          "note": "Social rollout",
          "in_scope": true,
          "billable": true,
          "invoiced": true
        },
        {
          "id": "TE-013",
          "date": "2026-09-30",
          "task_id": "T-013",
          "hours": 14,
          "note": "Property 3 creative — not in SOW",
          "in_scope": false,
          "billable": true,
          "invoiced": false
        },
        {
          "id": "TE-014",
          "date": "2026-10-03",
          "task_id": "T-014",
          "hours": 0,
          "note": "Blocked: awaiting property 3 media plan",
          "in_scope": true,
          "billable": true,
          "invoiced": false
        }
      ],
      "change_orders": [
        {
          "id": "HAD-CO-01",
          "title": "Property 3 creative adaptation",
          "amount": 3200,
          "hours": 12,
          "status": "Billed",
          "date": "2026-09-23"
        },
        {
          "id": "HAD-CO-02",
          "title": "Property 3 media plan + rollout",
          "amount": 2800,
          "hours": 10,
          "status": "Approved",
          "date": "2026-10-01"
        }
      ],
      "risks": [
        "Project deadline passed — report blocked on client media plan.",
        "Approved change order HAD-CO-02 not yet invoiced."
      ],
      "health_flag": "At Risk",
      "scope_exposure": true
    },
    {
      "id": "P-003",
      "client_id": "C-004",
      "name": "Pureform — Brand Film",
      "status": "Completed",
      "start": "2026-07-27",
      "due": "2026-09-07",
      "budget": 8500,
      "currency": "USD",
      "hourly_rate": 125,
      "included_revisions": 3,
      "scope_summary": "60-second brand film: concept, shoot, edit, grade.",
      "tasks": [
        {
          "id": "T-021",
          "name": "Concept + treatment",
          "status": "Done",
          "progress": 100,
          "due": "2026-08-08",
          "estimated_hours": 8,
          "logged_hours": 7
        },
        {
          "id": "T-022",
          "name": "Shoot (2 days)",
          "status": "Done",
          "progress": 100,
          "due": "2026-08-21",
          "estimated_hours": 24,
          "logged_hours": 26
        },
        {
          "id": "T-023",
          "name": "Edit + grade",
          "status": "Done",
          "progress": 100,
          "due": "2026-09-03",
          "estimated_hours": 22,
          "logged_hours": 24
        },
        {
          "id": "T-024",
          "name": "Delivery + masters",
          "status": "Done",
          "progress": 100,
          "due": "2026-09-07",
          "estimated_hours": 4,
          "logged_hours": 3
        }
      ],
      "deliverables": [
        {
          "name": "Brand film — final master",
          "status": "Delivered",
          "due": "2026-09-07",
          "revisions": 3,
          "approval": {
            "state": "approved",
            "requested": "2026-08-30",
            "decided": "2026-09-05"
          }
        }
      ],
      "time_entries": [
        {
          "id": "TE-021",
          "date": "2026-08-16",
          "task_id": "T-021",
          "hours": 7,
          "note": "Treatment",
          "in_scope": true,
          "billable": true,
          "invoiced": true
        },
        {
          "id": "TE-022",
          "date": "2026-08-22",
          "task_id": "T-022",
          "hours": 26,
          "note": "Shoot days",
          "in_scope": true,
          "billable": true,
          "invoiced": true
        },
        {
          "id": "TE-023",
          "date": "2026-09-02",
          "task_id": "T-023",
          "hours": 24,
          "note": "Edit + grade",
          "in_scope": true,
          "billable": true,
          "invoiced": true
        },
        {
          "id": "TE-024",
          "date": "2026-09-06",
          "task_id": "T-024",
          "hours": 3,
          "note": "Mastering",
          "in_scope": true,
          "billable": true,
          "invoiced": true
        }
      ],
      "change_orders": [],
      "risks": [],
      "health_flag": "Healthy",
      "scope_exposure": false
    },
    {
      "id": "P-004",
      "client_id": "C-005",
      "name": "Vega Health — Content Engine",
      "status": "Active",
      "start": "2026-08-21",
      "due": "2026-10-23",
      "budget": 12000,
      "currency": "EUR",
      "hourly_rate": 95,
      "included_revisions": 2,
      "scope_summary": "12 content assets + distribution engine, phase 1 of retainer conversion.",
      "tasks": [
        {
          "id": "T-031",
          "name": "Message architecture",
          "status": "Done",
          "progress": 100,
          "due": "2026-08-31",
          "estimated_hours": 8,
          "logged_hours": 8
        },
        {
          "id": "T-032",
          "name": "Asset production (12)",
          "status": "In Progress",
          "progress": 70,
          "due": "2026-10-15",
          "estimated_hours": 24,
          "logged_hours": 20
        },
        {
          "id": "T-033",
          "name": "Distribution setup",
          "status": "In Progress",
          "progress": 30,
          "due": "2026-10-21",
          "estimated_hours": 10,
          "logged_hours": 4
        }
      ],
      "deliverables": [
        {
          "name": "Message architecture",
          "status": "Approved",
          "due": "2026-09-01",
          "revisions": 1,
          "approval": {
            "state": "approved",
            "requested": "2026-08-28",
            "decided": "2026-08-31"
          }
        },
        {
          "name": "Content set A (6 assets)",
          "status": "Awaiting Approval",
          "due": "2026-10-04",
          "revisions": 2,
          "approval": {
            "state": "pending",
            "requested": "2026-09-29"
          }
        },
        {
          "name": "Content set B (6 assets)",
          "status": "In Progress",
          "due": "2026-10-17",
          "revisions": 0,
          "approval": {
            "state": "none"
          }
        }
      ],
      "time_entries": [
        {
          "id": "TE-031",
          "date": "2026-08-30",
          "task_id": "T-031",
          "hours": 8,
          "note": "Architecture",
          "in_scope": true,
          "billable": true,
          "invoiced": true
        },
        {
          "id": "TE-032",
          "date": "2026-09-25",
          "task_id": "T-032",
          "hours": 20,
          "note": "Asset production",
          "in_scope": true,
          "billable": true,
          "invoiced": false
        },
        {
          "id": "TE-033",
          "date": "2026-10-01",
          "task_id": "T-033",
          "hours": 4,
          "note": "Distribution setup",
          "in_scope": true,
          "billable": true,
          "invoiced": false
        }
      ],
      "change_orders": [],
      "risks": [
        "Content set A awaiting approval 6 days — blocks set B production."
      ],
      "health_flag": "Healthy",
      "scope_exposure": false
    }
  ],
  "messages": [
    {
      "id": "M-001",
      "client_id": "C-002",
      "date": "2026-09-19",
      "channel": "email",
      "direction": "out",
      "subject": "Casa Ferrer — proposal: rebrand + launch",
      "summary": "Proposal delivered: rebrand + 3-week launch, €24,000, two payment stages."
    },
    {
      "id": "M-002",
      "client_id": "C-002",
      "date": "2026-09-26",
      "channel": "whatsapp",
      "direction": "in",
      "subject": "Propuesta recibida",
      "summary": "Lucía confirms receipt, asks whether the timeline can compress to 2 weeks, will discuss with her partner."
    },
    {
      "id": "M-003",
      "client_id": "C-002",
      "date": "2026-09-28",
      "channel": "email",
      "direction": "out",
      "subject": "Re: timeline — what a 2-week version actually costs",
      "summary": "Explained the 2-week compression requires paid ad spend pre-approved and a locked brand direction by Friday."
    },
    {
      "id": "M-004",
      "client_id": "C-001",
      "date": "2026-09-26",
      "channel": "slack",
      "direction": "in",
      "subject": "Q4 plan",
      "summary": "Daniel wants Q4 plan + renewal options before their board meeting. Asked for the podcast line item."
    },
    {
      "id": "M-005",
      "client_id": "C-001",
      "date": "2026-08-22",
      "channel": "email",
      "direction": "out",
      "subject": "Reminder: invoice MEM-2026-003",
      "summary": "Final notice sent on month-3 retainer — $4,800, 30+ days late.",
      "reminder_tier": 3
    },
    {
      "id": "M-006",
      "client_id": "C-003",
      "date": "2026-10-01",
      "channel": "whatsapp",
      "direction": "in",
      "subject": "Property 3",
      "summary": "Omar approves HAD-CO-02 (2,800 AED) verbally and wants it live before their weekend."
    },
    {
      "id": "M-007",
      "client_id": "C-003",
      "date": "2026-09-27",
      "channel": "email",
      "direction": "out",
      "subject": "Approval needed: Property 3 creative adaptation",
      "summary": "Sent creative for approval — still pending, blocking production."
    },
    {
      "id": "M-008",
      "client_id": "C-004",
      "date": "2026-09-05",
      "channel": "email",
      "direction": "out",
      "subject": "Pureform — brand film delivered",
      "summary": "Final masters delivered, invoice cleared same week. Testimonial ask pending."
    },
    {
      "id": "M-009",
      "client_id": "C-005",
      "date": "2026-10-02",
      "channel": "call",
      "direction": "out",
      "subject": "Vega — Q1 planning",
      "summary": "Marta open to retainer expansion, wants the model with CAC assumptions before deciding. Wants it in Spanish."
    },
    {
      "id": "M-010",
      "client_id": "C-005",
      "date": "2026-09-29",
      "channel": "email",
      "direction": "out",
      "subject": "Approval: Content set A",
      "summary": "Six assets sent for approval, awaiting sign-off before set B goes into production."
    },
    {
      "id": "M-011",
      "client_id": "C-005",
      "date": "2026-09-28",
      "channel": "email",
      "direction": "out",
      "subject": "Reminder: invoice MEM-2026-005",
      "summary": "Firm reminder sent — €7,200 now 7 days past due.",
      "reminder_tier": 2
    },
    {
      "id": "M-012",
      "client_id": "C-001",
      "date": "2026-10-03",
      "channel": "email",
      "direction": "out",
      "subject": "Q4 plan draft for review",
      "summary": "Draft Q4 plan sent for Daniel's board meeting prep."
    }
  ]
};

export function sampleBook(reference = new Date().toISOString().slice(0, 10)): Book {
  const shift = Date.parse(`${reference}T00:00:00Z`) - Date.parse(`${anchor}T00:00:00Z`);
  const adjusted = JSON.stringify(sample).replace(/"(\d{4}-\d{2}-\d{2})"/g, (_, value: string) => JSON.stringify(new Date(Date.parse(`${value}T00:00:00Z`) + shift).toISOString().slice(0, 10)));
  return bookSchema.parse(JSON.parse(adjusted));
}

export const templates: Record<string, Record<string, string>> = {
  "lead_followup": {
    "en": "Subject: {company} — the story we're not telling yet\n\n{name},\n\nWe met. You liked the direction. Then the week got loud and nothing shipped. I'm not here to chase you — I'm here to give you one idea worth replying to.\n\nThree moves I'd make for {company} in the next 30 days:\n1. {hook_1}\n2. {hook_2}\n3. {hook_3}\n\nNo deck, no discovery call theatre. If that's the direction, reply \"go\" and I'll send the scope and the number the same day.\n\n{sender}",
    "es": "Asunto: {company} — la historia que aún no contamos\n\n{name},\n\nNos conocimos. Te gustó la dirección. Luego la semana se llenó y nada salió. No escribo para perseguirte — escribo para darte una idea que valga una respuesta.\n\nTres movimientos que haría para {company} en 30 días:\n1. {hook_1}\n2. {hook_2}\n3. {hook_3}\n\nSin presentaciones eternas ni llamadas de relleno. Si es el camino, responde \"dale\" y te envío alcance y precio el mismo día.\n\n{sender}"
  },
  "proposal_send": {
    "en": "Subject: {company} — proposal: {project}\n\n{name},\n\nProposal's attached. It's built to be decided on, not studied.\n\nTHE OUTCOME\n{outcome}\n\nWHAT WE DO\n{scope}\n\nINVESTMENT\n{investment} — {terms}\n\nTIMELINE\n{timeline}\n\nTwo ways to move: reply \"approved\" and I start {start_date}, or tell me the one thing that's wrong and I'll fix it today.\n\n{sender}",
    "es": "Asunto: {company} — propuesta: {project}\n\n{name},\n\nLa propuesta va adjunta. Está hecha para decidirse, no para estudiarse.\n\nEL RESULTADO\n{outcome}\n\nQUÉ HACEMOS\n{scope}\n\nINVERSIÓN\n{investment} — {terms}\n\nCRONOGRAMA\n{timeline}\n\nDos formas de avanzar: responde \"aprobado\" y arranco el {start_date}, o dime la única cosa que no cuadra y la corrijo hoy.\n\n{sender}"
  },
  "proposal_nudge": {
    "en": "Subject: {company} — one question on the proposal\n\n{name},\n\nYou've had the proposal for {days} days. Silence usually means one of two things: the timing is wrong, or the number is wrong.\n\nTell me which one and we'll either move or shelve it cleanly. If it's timing — what needs to be true before you say yes?\n\n{sender}",
    "es": "Asunto: {company} — una pregunta sobre la propuesta\n\n{name},\n\nLlevas {days} días con la propuesta. El silencio suele significar una de dos cosas: el momento es equivocado, o el número es equivocado.\n\nDime cuál y avanzamos o lo archivamos limpio. Si es el momento — ¿qué tiene que pasar para que digas sí?\n\n{sender}"
  },
  "onboarding": {
    "en": "Subject: {company} — we're live Monday\n\n{name},\n\nWelcome aboard. Here's the only email you need this week.\n\n1. Access: send over {access} today and I'll load everything before {start_date}.\n2. Points of contact: you + me, one decision-maker brief. Approvals in 48 hours keeps the calendar honest.\n3. Cadence: {cadence}.\n\nFirst win lands by {first_win}. I'll send the kickoff note the moment access is in.\n\n{sender}",
    "es": "Asunto: {company} — arrancamos el lunes\n\n{name},\n\nBienvenido a bordo. Este es el único correo que necesitas esta semana.\n\n1. Accesos: mándame {access} hoy y cargo todo antes del {start_date}.\n2. Contactos: tú y yo, un brief con quien decide. Aprobaciones en 48 horas para que el calendario se mantenga honesto.\n3. Ritmo: {cadence}.\n\nEl primer resultado llega antes del {first_win}. Aviso de arranque en cuanto tenga los accesos.\n\n{sender}"
  },
  "project_update": {
    "en": "Subject: {company} — {project}: week {week} update\n\n{name},\n\nStatus: {progress}% complete. {status_line}\n\nShipped this week\n{shipped}\n\nNext\n{next}\n\nNeeds from you\n{asks}\n\n{sender}",
    "es": "Asunto: {company} — {project}: informe semana {week}\n\n{name},\n\nEstado: {progress}% completado. {status_line}\n\nEsta semana\n{shipped}\n\nSiguiente\n{next}\n\nNecesito de ti\n{asks}\n\n{sender}"
  },
  "approval_request": {
    "en": "Subject: {company} — approval needed: {deliverable}\n\n{name},\n\n{deliverable} is ready for your eyes. This is the 48-hour gate — your sign-off keeps the next milestone on schedule.\n\nWhat I need: approve, or one round of notes. That's it.\nWhere it lives: {link}\nIf I hear nothing by {deadline}, I'll hold the release and the schedule shifts.\n\n{sender}",
    "es": "Asunto: {company} — aprueba: {deliverable}\n\n{name},\n\n{deliverable} está listo para tu revisión. Esta es la ventana de 48 horas — tu firma mantiene la siguiente etapa en calendario.\n\nLo que necesito: aprobar, o una ronda de comentarios. Nada más.\nDónde verlo: {link}\nSi no tengo respuesta para el {deadline}, retengo la publicación y el cronograma se corre.\n\n{sender}"
  },
  "approval_chase": {
    "en": "Subject: {company} — {deliverable}: day {days} of silence\n\n{name},\n\n{deliverable} has been sitting in approval for {days} days. Each day costs you {cost_note}.\n\nTwo paths, pick one today:\n· Reply \"go\" — I ship it and we stay on plan.\n· Reply \"hold\" — I stop the clock, park the milestone and we re-book the date.\n\nEither is fine. Drift isn't.\n\n{sender}",
    "es": "Asunto: {company} — {deliverable}: {days} días sin respuesta\n\n{name},\n\n{deliverable} lleva {days} días esperando aprobación. Cada día cuesta {cost_note}.\n\nDos caminos, elige uno hoy:\n· Responde \"ya\" — lo publico y seguimos en plan.\n· Responde \"en pausa\" — paro el reloj, aparco el hito y reagendamos.\n\nCualquiera está bien. La deriva no.\n\n{sender}"
  },
  "invoice_send": {
    "en": "Subject: {company} — invoice {invoice} · {amount}\n\n{name},\n\nInvoice {invoice} for {amount} is attached. Work delivered: {work}.\nDue {due} ({terms}).\n\nPayment details are on the invoice. Any issue with it, tell me today so I can fix it before Friday.\n\n{sender}",
    "es": "Asunto: {company} — factura {invoice} · {amount}\n\n{name},\n\nAdjunto la factura {invoice} por {amount}. Trabajo entregado: {work}.\nVence el {due} ({terms}).\n\nLos datos de pago están en la factura. Si algo no cuadra, dímelo hoy para corregirlo antes del viernes.\n\n{sender}"
  },
  "reminder_1": {
    "en": "Subject: {company} — invoice {invoice} cleared?\n\n{name},\n\nInvoice {invoice} ({amount}) was due {due}. Likely an admin slip, not a statement — flagging it so your accounts team can close it out.\n\nPay link / details on the invoice. If it's already scheduled, ignore this and we're square.\n\n{sender}",
    "es": "Asunto: {company} — ¿factura {invoice} pagada?\n\n{name},\n\nLa factura {invoice} ({amount}) venció el {due}. Probablemente un tema administrativo, no un problema — te aviso para que contabilidad lo cierre.\n\nDatos de pago en la factura. Si ya está programada, ignora esto y estamos en paz.\n\n{sender}"
  },
  "reminder_2": {
    "en": "Subject: {company} — {amount} outstanding on {invoice}\n\n{name},\n\nInvoice {invoice} is {days} days past due. {amount} outstanding. I need this settled this week to keep {project} resourced and on schedule.\n\nConfirm today: (1) payment date, or (2) who on your side I should speak to.\n\n{sender}",
    "es": "Asunto: {company} — {amount} pendiente en {invoice}\n\n{name},\n\nLa factura {invoice} lleva {days} días vencida. {amount} pendientes. Necesito cerrarlo esta semana para mantener {project} con recursos y en calendario.\n\nConfírmame hoy: (1) fecha de pago, o (2) con quién de tu equipo debo hablar.\n\n{sender}"
  },
  "reminder_3": {
    "en": "Subject: {company} — final notice: invoice {invoice}\n\n{name},\n\nInvoice {invoice} — {days} days past due, {amount} outstanding. Reminders have gone unanswered, so this is the formal step.\n\nPayment or a written plan by {deadline}, otherwise {escalation}. I'd rather keep this between us and get back to the work.\n\n{sender}",
    "es": "Asunto: {company} — aviso final: factura {invoice}\n\n{name},\n\nFactura {invoice} — {days} días vencida, {amount} pendiente. Los recordatorios quedaron sin respuesta, así que este es el paso formal.\n\nPago o un plan por escrito antes del {deadline}; de lo contrario {escalation}. Prefiero mantener esto entre nosotros y volver al trabajo.\n\n{sender}"
  },
  "gap_nudge": {
    "en": "Subject: {company} — checking the silence\n\n{name},\n\n{days} days since we last spoke — that's longer than we run. My fault as much as yours, so here's the fix: {move}\n\nReply with a yes and I'll handle the rest.\n\n{sender}",
    "es": "Asunto: {company} — el silencio\n\n{name},\n\n{days} días desde la última conversación — más de lo que acostumbramos. Tanto mi culpa como tuya, así que aquí va la solución: {move}\n\nResponde con un sí y yo me encargo del resto.\n\n{sender}"
  },
  "upsell": {
    "en": "Subject: {company} — what {company} should do next\n\n{name},\n\n{trigger}\n\nHere's what I'd put in phase two: {offer}\nWhy now: {why_now}\n\nInvestment: {amount}. I can start {start_date} and have the first result by {first_win}.\n\nSay the word and I'll send the one-page scope.\n\n{sender}",
    "es": "Asunto: {company} — lo que sigue para {company}\n\n{name},\n\n{trigger}\n\nEsto es lo que pondría en la fase dos: {offer}\nPor qué ahora: {why_now}\n\nInversión: {amount}. Puedo arrancar el {start_date} y tener el primer resultado para el {first_win}.\n\nDame la señal y te envío el alcance de una página.\n\n{sender}"
  },
  "change_order": {
    "en": "Subject: {company} — change order: {title}\n\n{name},\n\n{reason}\n\nScope added: {scope}\nImpact: {hours}h · {amount}\nSchedule: {schedule_impact}\n\nApprove below and it goes straight onto the next invoice. Decline and I'll park the work and keep the original scope intact.\n\nReply \"approved\" or \"decline\". Nothing else needed.\n\n{sender}",
    "es": "Asunto: {company} — orden de cambio: {title}\n\n{name},\n\n{reason}\n\nAlcance añadido: {scope}\nImpacto: {hours}h · {amount}\nCronograma: {schedule_impact}\n\nApruébala y entra directo a la próxima factura. Si la rechazas, aparco el trabajo y mantengo el alcance original intacto.\n\nResponde \"aprobado\" o \"rechazado\". Nada más.\n\n{sender}"
  },
  "testimonial_ask": {
    "en": "Subject: {company} — 3 questions, 3 minutes\n\n{name},\n\n{result} — that's worth saying out loud.\n\nThree questions, answers by voice note if easier:\n1. What was the problem before we started?\n2. What changed?\n3. Who would you send us to?\n\nI'll shape it into a case study and send you the draft before anything goes public.\n\n{sender}",
    "es": "Asunto: {company} — 3 preguntas, 3 minutos\n\n{name},\n\n{result} — vale la pena decirlo en voz alta.\n\nTres preguntas, respuestas por nota de voz si es más fácil:\n1. ¿Cuál era el problema antes de empezar?\n2. ¿Qué cambió?\n3. ¿A quién nos recomendarías?\n\nLo convierto en caso de estudio y te envío el borrador antes de publicar nada.\n\n{sender}"
  }
};
