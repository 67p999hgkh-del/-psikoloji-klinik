"""Public pricing page helpers."""

from subscription_plans import PLANS, PLAN_IDS, format_try


def build_pricing_page_context():
    plans = []
    for pid in PLAN_IDS:
        p = PLANS[pid]
        plans.append({
            **p,
            "setup_display": format_try(p["setup_price"]),
            "monthly_display": format_try(p["monthly_price"]),
            "yearly_display": format_try(int(p["monthly_price"] * 12 * 0.85)),
            "is_popular": pid == "professional",
            "is_enterprise": pid in ("enterprise", "custom"),
        })
    return {
        "pricing_plans": plans,
        "pricing_addons": [
            {"label": "Ek terapist (limit üstü)", "price": "800 – 1.200 ₺/ay"},
            {"label": "Ek şube", "price": "2.000 – 4.000 ₺/ay"},
            {"label": "İçerik paketi (4 blog + 8 sosyal/ay)", "price": "8.000 – 15.000 ₺/ay"},
            {"label": "Veri migrasyonu", "price": "15.000 – 40.000 ₺"},
            {"label": "Özel entegrasyon (iyzico, SMS)", "price": "25.000 – 60.000 ₺"},
            {"label": "Ek eğitim", "price": "1.500 – 2.500 ₺/saat"},
        ],
    }
