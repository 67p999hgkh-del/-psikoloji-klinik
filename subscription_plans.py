"""Abonelik paketleri — modül erişimi, limitler ve fiyatlandırma."""

from __future__ import annotations

PLAN_IDS = ("starter", "professional", "enterprise", "custom")

ALL_MODULES = frozenset({
    "dashboard",
    "appointments",
    "sessions",
    "blog",
    "sliders",
    "social",
    "widgets",
    "tests",
    "theme",
    "email",
    "users",
    "audit",
    "analiz",
    "invoices",
    "therapists",
})

PLANS = {
    "starter": {
        "id": "starter",
        "label": "Başlangıç — Klinik Dijital",
        "tagline": "1–3 terapistli yeni klinikler için",
        "modules": frozenset({
            "dashboard", "appointments", "sessions", "blog", "theme", "therapists", "email", "users",
        }),
        "limits": {"therapists": 3, "branches": 1, "storage_gb": 5},
        "setup_price": 65000,
        "monthly_price": 4000,
        "features_included": [
            "Kurumsal web sitesi",
            "Online randevu & danışan portalı",
            "Terapist paneli",
            "Temel seans kaydı",
            "Blog CMS",
            "E-posta bildirimleri",
            "Tema & logo",
            "Mobil admin panel",
        ],
        "features_excluded": [
            "Sosyal medya hub",
            "Widget CMS",
            "PsikoPlan tam analitik",
            "AI asistanlar",
            "Fatura modülü",
        ],
    },
    "professional": {
        "id": "professional",
        "label": "Profesyonel — Klinik Operasyon",
        "tagline": "4–10 terapistli aktif klinikler için",
        "modules": frozenset({
            "dashboard", "appointments", "sessions", "blog", "sliders", "tests",
            "theme", "therapists", "email", "users", "analiz", "invoices",
        }),
        "limits": {"therapists": 10, "branches": 2, "storage_gb": 20},
        "setup_price": 140000,
        "monthly_price": 9000,
        "features_included": [
            "Başlangıç paketindeki tüm özellikler",
            "Tam seans çalışma alanı (SOAP/DAP)",
            "Psikolojik testler CMS",
            "Slider yönetimi",
            "Randevu operasyon merkezi",
            "Fatura & ödeme takibi",
            "PsikoPlan temel analitik",
            "Seans AI özeti",
        ],
        "features_excluded": [
            "Sosyal medya hub",
            "Widget CMS (19 tip)",
            "Denetim logları",
        ],
    },
    "enterprise": {
        "id": "enterprise",
        "label": "Kurumsal — Klinik + Pazarlama",
        "tagline": "Büyük klinikler ve pazarlama odaklı yapılar",
        "modules": ALL_MODULES,
        "limits": {"therapists": 999, "branches": 5, "storage_gb": 50},
        "setup_price": 270000,
        "monthly_price": 19000,
        "features_included": [
            "Profesyonel paketteki tüm özellikler",
            "Sosyal Medya Hub",
            "Widget CMS",
            "Blog ↔ Sosyal ↔ Slider entegrasyonu",
            "PsikoPlan tam analitik",
            "AI içerik koçu",
            "Çok şube yönetimi",
            "Denetim logları",
            "Öncelikli destek",
        ],
        "features_excluded": [],
    },
    "custom": {
        "id": "custom",
        "label": "Özel — Enterprise / White Label",
        "tagline": "Zincir klinikler, franchise, kurumsal yapılar",
        "modules": ALL_MODULES,
        "limits": {"therapists": 9999, "branches": 99, "storage_gb": 500},
        "setup_price": 400000,
        "monthly_price": 25000,
        "features_included": [
            "Kurumsal paketteki tüm özellikler",
            "White label",
            "Özel entegrasyonlar (iyzico, SMS)",
            "SLA garantisi",
            "Özel modül geliştirme",
            "Yerinde kurulum seçeneği",
        ],
        "features_excluded": [],
    },
}

DEFAULT_PLAN = "enterprise"

MODULE_LABELS = {
    "dashboard": "Dashboard",
    "appointments": "Randevular",
    "sessions": "Seanslar",
    "blog": "Blog",
    "sliders": "Slider",
    "social": "Sosyal Medya",
    "widgets": "Widgetlar",
    "tests": "Testler",
    "theme": "Tema & Logo",
    "email": "E-posta",
    "users": "Kullanıcılar",
    "audit": "Denetim Logları",
    "analiz": "PsikoPlan Analiz",
    "invoices": "Faturalar",
    "therapists": "Terapistler",
}


def get_plan(plan_id: str | None) -> dict:
    pid = (plan_id or DEFAULT_PLAN).strip().lower()
    if pid not in PLANS:
        pid = DEFAULT_PLAN
    return PLANS[pid]


def get_active_plan(settings=None) -> dict:
    if settings is None:
        from models import SiteSettings

        settings = SiteSettings.get()
    return get_plan(getattr(settings, "subscription_plan", None) or DEFAULT_PLAN)


def plan_has_module(plan_id: str | None, permission: str) -> bool:
    plan = get_plan(plan_id)
    return permission in plan["modules"]


def plan_label(plan_id: str | None) -> str:
    return get_plan(plan_id)["label"]


def plan_limits(plan_id: str | None) -> dict:
    return dict(get_plan(plan_id)["limits"])


def format_try(amount: int) -> str:
    return f"{amount:,}".replace(",", ".") + " ₺"


def all_plans_public() -> list[dict]:
    return [PLANS[pid] for pid in PLAN_IDS if pid != "custom"] + [PLANS["custom"]]
