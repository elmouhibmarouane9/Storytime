"""Console chrome translations. Draft templates live in comms.py (EN/ES)."""

from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    "EN": {
        "tagline": "MEM Digital · Operations Console",
        "nav": "Navigate",
        "dashboard": "Dashboard",
        "clients": "Clients",
        "invoices": "Invoices",
        "finance": "Finance",
        "projects": "Projects",
        "comms": "Comms",
        "settings": "Settings",
        "today": "Today",
        "snapshot": "Snapshot",
        "collected": "Collected MTD",
        "overdue": "Overdue",
        "at_risk": "Projects at risk",
        "language": "Console language",
        "sample": "Sample book loaded — swap in real data from Settings.",
    },
    "ES": {
        "tagline": "MEM Digital · Consola de operaciones",
        "nav": "Navegación",
        "dashboard": "Panel",
        "clients": "Clientes",
        "invoices": "Facturas",
        "finance": "Finanzas",
        "projects": "Proyectos",
        "comms": "Comunicación",
        "settings": "Ajustes",
        "today": "Hoy",
        "snapshot": "Resumen",
        "collected": "Cobrado este mes",
        "overdue": "Vencido",
        "at_risk": "Proyectos en riesgo",
        "language": "Idioma de la consola",
        "sample": "Datos de ejemplo cargados — cambia a datos reales en Ajustes.",
    },
    "FR": {
        "tagline": "MEM Digital · Console d'opérations",
        "nav": "Navigation",
        "dashboard": "Tableau de bord",
        "clients": "Clients",
        "invoices": "Factures",
        "finance": "Finance",
        "projects": "Projets",
        "comms": "Communication",
        "settings": "Réglages",
        "today": "Aujourd'hui",
        "snapshot": "Aperçu",
        "collected": "Encaissé ce mois",
        "overdue": "En retard",
        "at_risk": "Projets à risque",
        "language": "Langue de la console",
        "sample": "Données d'exemple — remplacez-les dans Réglages.",
    },
    "AR": {
        "tagline": "MEM Digital · لوحة العمليات",
        "nav": "التنقل",
        "dashboard": "لوحة التحكم",
        "clients": "العملاء",
        "invoices": "الفواتير",
        "finance": "المالية",
        "projects": "المشاريع",
        "comms": "التواصل",
        "settings": "الإعدادات",
        "today": "اليوم",
        "snapshot": "لمحة",
        "collected": "المحصّل هذا الشهر",
        "overdue": "متأخر",
        "at_risk": "مشاريع في خطر",
        "language": "لغة الواجهة",
        "sample": "تم تحميل بيانات تجريبية — استبدلها من الإعدادات.",
    },
}


NAV_ICONS = {"dashboard": "◆", "clients": "◉", "invoices": "▤", "finance": "◈",
             "projects": "▣", "comms": "✉", "settings": "⚙"}

PAGE_KEYS = ["dashboard", "clients", "invoices", "finance", "projects", "comms", "settings"]


def nav_labels(lang: str = "EN") -> list[str]:
    return [f"{NAV_ICONS[key]}  {t(key, lang)}" for key in PAGE_KEYS]


def t(key: str, lang: str = "EN") -> str:
    table = STRINGS.get(lang) or STRINGS["EN"]
    return table.get(key, STRINGS["EN"].get(key, key))
