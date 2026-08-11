"""Ticari dokümanlar — hizmet sağlayıcı (SaaS) şirket profili."""

from __future__ import annotations

# Müşteriye özel teklif alanları şablonda [MÜŞTERİ_...] olarak kalır;
# aşağıdaki bilgiler hizmet sağlayıcı (siz) içindir.

COMPANY = {
    "legal_name": "MindCare Yazılım ve Teknoloji A.Ş.",
    "brand_name": "MindCare Klinik Platformu",
    "tagline": "Psikoloji klinikleri için uçtan uca yönetim yazılımı",
    "address": "Muratpaşa, Antalya Teknokent, 07070 Antalya / Türkiye",
    "tax_office": "Antalya Kurumlar Vergi Dairesi",
    "tax_number": "1234567890",
    "mersis": "0123456789012345",
    "trade_registry": "Antalya Ticaret Sicil No: 123456",
    "email": "info@mindcare.com.tr",
    "sales_email": "satis@mindcare.com.tr",
    "phone": "+90 242 000 00 00",
    "website": "https://mindcare.com.tr",
    "authorized_person": "Ahmet Yılmaz",
    "authorized_title": "Genel Müdür",
    "bank_name": "Ziraat Bankası",
    "bank_iban": "TR00 0000 0000 0000 0000 0000 00",
    "data_location": "Türkiye (İstanbul & Antalya veri merkezleri)",
    "support_hours": "Pazartesi – Cuma, 09:00 – 18:00",
    "dispute_city": "Antalya",
}

# Varsayılan teklif parametreleri (Profesyonel paket örneği)
DEFAULT_QUOTE = {
    "quote_no": "TEKLIF-2026-001",
    "validity_days": 30,
    "plan_id": "professional",
    "customer_name": "[Klinik / Kurum Adı]",
    "customer_contact": "[Yetkili Ad Soyad — Unvan]",
    "customer_email": "[musteri@klinik.com]",
    "customer_phone": "[+90 5XX XXX XX XX]",
    "payment_terms": [
        ("Sözleşme imzası", 40, 56000),
        ("Canlıya alma (go-live)", 40, 56000),
        ("30 gün stabilizasyon sonrası", 20, 28000),
    ],
    "setup_weeks": "2–3 hafta",
    "training_hours": 2,
}


def company_display() -> dict:
    return dict(COMPANY)


def merge_quote(overrides: dict | None = None) -> dict:
    q = dict(DEFAULT_QUOTE)
    if overrides:
        q.update(overrides)
    return q
