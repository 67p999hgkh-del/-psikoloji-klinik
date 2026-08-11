"""PsikoPlan constants, audit, analysis, and client invite helpers."""
import json
import secrets
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

APPLICATION_REASONS = [
    "Kaygı",
    "Depresif belirtiler",
    "Panik atak",
    "OKB",
    "Travma",
    "Yas",
    "İlişki problemi",
    "Çift terapisi",
    "Boşanma",
    "Çocuk-Ergen",
    "DEHB",
    "Sınav kaygısı",
    "Öfke kontrolü",
    "Bağımlılık",
    "Tükenmişlik",
    "İş stresi",
    "Mobbing",
    "Diğer",
]

SPECIALTY_FILTERS = [
    "Çocuk",
    "EMDR",
    "Çift Terapisi",
    "Kaygı",
    "DEHB",
    "Travma",
]

CONTENT_ACTION_TEMPLATES = [
    {
        "icon": "📝",
        "title": "Blog Yazısı",
        "hint": "{reason} ile başa çıkma rehberi",
        "href": "/admin/blog/ekle",
        "action": "Yazı oluştur",
    },
    {
        "icon": "🎬",
        "title": "Instagram Reels",
        "hint": "60 sn nefes / farkındalık egzersizi",
        "href": "/admin/widgetlar",
        "action": "Widget planla",
    },
    {
        "icon": "▶️",
        "title": "YouTube Videosu",
        "hint": "{reason} belirtileri ve çözümler",
        "href": "/admin/blog",
        "action": "İçerik listesi",
    },
    {
        "icon": "🎤",
        "title": "Webinar",
        "hint": "Canlı soru-cevap oturumu",
        "href": "/admin/slider",
        "action": "Duyuru ekle",
    },
    {
        "icon": "📋",
        "title": "Psikolojik Test",
        "hint": "{reason} düzeyi ön değerlendirme",
        "href": "/admin/testler",
        "action": "Testleri yönet",
    },
]


def log_audit(user, action, entity_type="", entity_id=None, detail=""):
    from models import AuditLog, db

    if isinstance(detail, (dict, list)):
        detail = json.dumps(detail, ensure_ascii=False)

    entry = AuditLog(
        user_id=user.id if user else None,
        username=user.username if user else "sistem",
        action=action,
        entity_type=entity_type or "",
        entity_id=entity_id,
        detail=detail or "",
        created_at=datetime.utcnow(),
    )
    db.session.add(entry)
    return entry


def ensure_client_invite(patient_name, patient_email, patient_phone=""):
    """Create or update a client invite for appointment email. Returns (profile, created)."""
    from models import ClientProfile, User, db
    from werkzeug.security import generate_password_hash

    email = (patient_email or "").strip().lower()
    if not email:
        return None, False

    profile = ClientProfile.query.filter_by(email=email).first()
    if profile:
        if patient_phone and not profile.phone:
            profile.phone = patient_phone
        if patient_name and profile.full_name != patient_name:
            profile.full_name = patient_name
        return profile, False

    user = User.query.filter_by(username=email).first()
    if not user:
        user = User(
            username=email,
            password_hash=generate_password_hash(secrets.token_urlsafe(16), method="pbkdf2:sha256"),
            role="client",
            is_active=True,
        )
        db.session.add(user)
        db.session.flush()

    token = secrets.token_urlsafe(24)
    profile = ClientProfile(
        user_id=user.id,
        full_name=patient_name or email,
        email=email,
        phone=patient_phone or "",
        invite_token=token,
        invite_accepted=False,
    )
    db.session.add(profile)
    return profile, True


PAYMENT_LABELS = {
    "odendi": "Ödendi",
    "bekliyor": "Bekliyor",
    "borc": "Borç",
    "yok": "Fatura yok",
}


def payment_status_map(emails, overdue_days=14):
    """Return {email: odendi|bekliyor|borc|yok} based on invoice records."""
    from models import Invoice

    emails = {(e or "").lower() for e in emails if e}
    if not emails:
        return {}

    invoices = Invoice.query.filter(Invoice.patient_email.in_(emails)).all()
    grouped = defaultdict(list)
    for invoice in invoices:
        grouped[(invoice.patient_email or "").lower()].append(invoice)

    today = date.today()
    result = {}
    for email in emails:
        rows = grouped.get(email, [])
        if not rows:
            result[email] = "yok"
            continue
        pending = [i for i in rows if i.status == "bekliyor"]
        if any(i.invoice_date and (today - i.invoice_date).days > overdue_days for i in pending):
            result[email] = "borc"
        elif pending:
            result[email] = "bekliyor"
        else:
            result[email] = "odendi"
    return result


def build_session_ai_summary(record):
    """Deterministic, rule-based session summary shown as 'AI Seans Özeti'."""
    from models import SessionRecord, TestResult

    reasons = record.reason_list()
    email = (record.patient_email or "").lower()
    history = (
        SessionRecord.query.filter(SessionRecord.patient_email.ilike(email))
        .order_by(SessionRecord.created_at.asc())
        .all()
        if email
        else [record]
    )
    tests = (
        TestResult.query.filter(TestResult.patient_email.ilike(email))
        .order_by(TestResult.created_at.desc())
        .limit(3)
        .all()
        if email
        else []
    )

    reason_counter = Counter()
    for item in history:
        for reason in item.reason_list():
            reason_counter[reason] += 1
    dominant = [r for r, _ in reason_counter.most_common(2)]

    total = len(history)
    first = history[0].created_at if history else record.created_at
    span_days = (record.created_at - first).days if history else 0

    lines = []
    if reasons:
        lines.append(
            f"Bu seansta öne çıkan başvuru nedenleri: {', '.join(reasons)}."
        )
    else:
        lines.append("Bu seans için başvuru nedeni işaretlenmemiş.")

    if total > 1:
        lines.append(
            f"Danışanın toplam {total} seans kaydı var; süreç {max(span_days, 1)} güne yayılıyor."
        )
        if dominant:
            lines.append(f"Süreç boyunca tekrar eden temalar: {', '.join(dominant)}.")
    else:
        lines.append("Bu, danışanın ilk kayıtlı seansı.")

    risk_notes = {
        "yuksek": "Risk seviyesi yüksek: seans sıklığının artırılması ve güvenlik planı önerilir.",
        "orta": "Risk seviyesi orta: iki seans arası takip ve ödev takibi önerilir.",
        "dusuk": "Risk seviyesi düşük: mevcut seans planı sürdürülebilir.",
    }
    lines.append(risk_notes.get(record.risk_level, ""))

    if tests:
        test_bits = [
            f"{t.test.title if t.test else 'Test'} ({t.level or round(t.score or 0)})" for t in tests
        ]
        lines.append(f"Son test sonuçları: {', '.join(test_bits)}.")
    else:
        lines.append("Danışana ait kayıtlı test sonucu bulunmuyor; ön değerlendirme testi önerilebilir.")

    if record.next_session_date:
        lines.append(f"Sonraki seans {record.next_session_date.strftime('%d.%m.%Y')} olarak planlandı.")
    else:
        lines.append("Sonraki seans planlanmamış; randevu oluşturulması önerilir.")

    return {
        "text": " ".join(part for part in lines if part),
        "dominant_reasons": dominant,
        "session_count": total,
    }


def sync_client_links():
    """Backfill memberships from appointments and link records to client accounts."""
    from models import Appointment, ClientProfile, Invoice, SessionRecord, TestResult, db

    sources = []
    sources += [(a.patient_email, a.patient_name, a.patient_phone) for a in Appointment.query.all()]
    sources += [(s.patient_email, s.patient_name, "") for s in SessionRecord.query.all()]
    sources += [(i.patient_email, i.patient_name, "") for i in Invoice.query.all()]
    sources += [(t.patient_email, t.patient_name, "") for t in TestResult.query.all()]

    created = 0
    seen = set()
    for raw_email, name, phone in sources:
        email = (raw_email or "").strip().lower()
        if not email or email in seen:
            continue
        seen.add(email)
        if ClientProfile.query.filter_by(email=email).first():
            continue
        _profile, was_created = ensure_client_invite(name, email, phone or "")
        if was_created:
            created += 1
    db.session.flush()

    profiles = {(p.email or "").lower(): p for p in ClientProfile.query.all()}
    linked = 0

    for record in SessionRecord.query.filter(SessionRecord.client_user_id.is_(None)).all():
        profile = profiles.get((record.patient_email or "").lower())
        if profile:
            record.client_user_id = profile.user_id
            linked += 1

    for invoice in Invoice.query.filter(Invoice.client_user_id.is_(None)).all():
        profile = profiles.get((invoice.patient_email or "").lower())
        if profile:
            invoice.client_user_id = profile.user_id
            linked += 1

    for result in TestResult.query.filter(TestResult.user_id.is_(None)).all():
        profile = profiles.get((result.patient_email or "").lower())
        if profile:
            result.user_id = profile.user_id
            linked += 1

    return {"memberships_created": created, "records_linked": linked}


def appointment_chart_stats(appointment_query):
    """Weekly/monthly counts and status distribution for Chart.js."""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    all_appts = appointment_query.all()
    weekly = sum(1 for a in all_appts if a.appointment_date >= week_start)
    monthly = sum(1 for a in all_appts if a.appointment_date >= month_start)

    status_counts = Counter(a.status for a in all_appts)
    status_labels = {
        "beklemede": "Beklemede",
        "onaylandi": "Onaylandı",
        "iptal": "İptal",
        "tamamlandi": "Tamamlandı",
    }
    status_chart = {
        "labels": [status_labels.get(k, k) for k in status_counts.keys()],
        "values": list(status_counts.values()),
    }

    # Last 8 weeks trend
    trend_labels = []
    trend_values = []
    for i in range(7, -1, -1):
        start = week_start - timedelta(weeks=i)
        end = start + timedelta(days=6)
        trend_labels.append(start.strftime("%d.%m"))
        trend_values.append(
            sum(1 for a in all_appts if start <= a.appointment_date <= end)
        )

    return {
        "weekly": weekly,
        "monthly": monthly,
        "status_chart": status_chart,
        "trend_chart": {"labels": trend_labels, "values": trend_values},
    }


def _sessions_in_range(query, start, end):
    from models import SessionRecord

    return query.filter(
        SessionRecord.created_at >= datetime.combine(start, datetime.min.time()),
        SessionRecord.created_at <= datetime.combine(end, datetime.max.time()),
    ).all()


TR_MONTHS = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]


def month_bounds(year, month):
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end


def _pct(part, whole):
    return round(part * 100 / whole) if whole else 0


def build_analiz_payload(year=None, month=None, therapist_id=None):
    from models import (
        Appointment,
        ClientProfile,
        Invoice,
        SessionRecord,
        TestResult,
        Therapist,
        User,
    )

    today = date.today()
    year = year or today.year
    month = month or today.month
    month_start, month_end = month_bounds(year, month)
    month_start_dt = datetime.combine(month_start, datetime.min.time())
    month_end_dt = datetime.combine(month_end, datetime.max.time())

    appointment_query = Appointment.query
    session_query = SessionRecord.query
    invoice_query = Invoice.query
    if therapist_id:
        appointment_query = appointment_query.filter_by(therapist_id=therapist_id)
        session_query = session_query.filter_by(therapist_id=therapist_id)
        invoice_query = invoice_query.filter_by(therapist_id=therapist_id)

    appointments = appointment_query.filter(
        Appointment.appointment_date >= month_start,
        Appointment.appointment_date <= month_end,
    ).all()
    sessions = session_query.filter(
        SessionRecord.created_at >= month_start_dt,
        SessionRecord.created_at <= month_end_dt,
    ).all()
    invoices = invoice_query.filter(
        Invoice.invoice_date >= month_start,
        Invoice.invoice_date <= month_end,
    ).all()

    scope_emails = None
    if therapist_id:
        scope_emails = {
            (a.patient_email or "").lower()
            for a in appointment_query.all()
            if a.patient_email
        }
    tests = TestResult.query.filter(
        TestResult.created_at >= month_start_dt,
        TestResult.created_at <= month_end_dt,
    ).all()
    if scope_emails is not None:
        tests = [t for t in tests if (t.patient_email or "").lower() in scope_emails]

    # ── Başvuru nedenleri
    reason_counter = Counter()
    for s in sessions:
        for reason in s.reason_list():
            reason_counter[reason] += 1
    total_reasons = sum(reason_counter.values())
    reason_stats = [
        {"label": label, "count": count, "pct": _pct(count, total_reasons)}
        for label, count in reason_counter.most_common()
    ]

    # ── Randevu durum / tür dağılımı
    status_counter = Counter(a.status for a in appointments)
    type_counter = Counter(a.session_type for a in appointments)
    completed = status_counter.get("tamamlandi", 0)
    cancelled = status_counter.get("iptal", 0)
    online_count = type_counter.get("online", 0)

    # ── Gelir
    paid = sum(i.amount or 0 for i in invoices if i.status == "odendi")
    pending_amount = sum(i.amount or 0 for i in invoices if i.status == "bekliyor")

    # ── Üyelikler
    client_base = ClientProfile.query.join(User, ClientProfile.user_id == User.id).filter(
        User.role == "client", User.is_active.is_(True)
    )
    if scope_emails is not None:
        client_base = client_base.filter(ClientProfile.email.in_(scope_emails or [""]))
    active_clients = client_base.count()
    pending_invites = client_base.filter(ClientProfile.invite_accepted.is_(False)).count()
    new_clients = client_base.filter(
        ClientProfile.created_at >= month_start_dt,
        ClientProfile.created_at <= month_end_dt,
    ).count()

    kpis = [
        {
            "icon": "📅",
            "label": "Randevu",
            "value": len(appointments),
            "sub": f"{status_counter.get('beklemede', 0)} onay bekliyor",
            "href": "/admin/randevular",
        },
        {
            "icon": "🩺",
            "label": "Seans Kaydı",
            "value": len(sessions),
            "sub": f"{total_reasons} başvuru nedeni işaretlendi",
            "href": "/admin/seanslar",
        },
        {
            "icon": "✅",
            "label": "Tamamlanma",
            "value": f"%{_pct(completed, len(appointments))}",
            "sub": f"{completed} tamamlandı · {cancelled} iptal",
            "href": "/admin/randevular",
        },
        {
            "icon": "💻",
            "label": "Online Oranı",
            "value": f"%{_pct(online_count, len(appointments))}",
            "sub": f"{online_count} online · {type_counter.get('yuz_yuze', 0)} yüz yüze",
            "href": "/admin/randevular",
        },
        {
            "icon": "💳",
            "label": "Tahsil Edilen",
            "value": f"{paid:,.0f} ₺".replace(",", "."),
            "sub": f"{pending_amount:,.0f} ₺ bekliyor".replace(",", "."),
            "href": "/admin/faturalar",
        },
        {
            "icon": "📋",
            "label": "Test Çözümü",
            "value": len(tests),
            "sub": f"{len({(t.patient_email or '').lower() for t in tests if t.patient_email})} farklı kişi",
            "href": "/admin/testler",
        },
        {
            "icon": "👥",
            "label": "Aktif Üye",
            "value": active_clients,
            "sub": f"{new_clients} yeni · {pending_invites} şifre bekliyor",
            "href": "/admin/kullanicilar",
        },
    ]

    # ── 6 aylık trend
    trend_labels, trend_appointments, trend_sessions, trend_revenue = [], [], [], []
    for offset in range(5, -1, -1):
        m = month - offset
        y = year
        while m <= 0:
            m += 12
            y -= 1
        t_start, t_end = month_bounds(y, m)
        trend_labels.append(f"{TR_MONTHS[m - 1][:3]} {str(y)[2:]}")
        trend_appointments.append(
            appointment_query.filter(
                Appointment.appointment_date >= t_start,
                Appointment.appointment_date <= t_end,
            ).count()
        )
        trend_sessions.append(
            session_query.filter(
                SessionRecord.created_at >= datetime.combine(t_start, datetime.min.time()),
                SessionRecord.created_at <= datetime.combine(t_end, datetime.max.time()),
            ).count()
        )
        trend_revenue.append(
            sum(
                i.amount or 0
                for i in invoice_query.filter(
                    Invoice.invoice_date >= t_start,
                    Invoice.invoice_date <= t_end,
                    Invoice.status == "odendi",
                ).all()
            )
        )

    # ── Şube (şehir) analizi
    city_data = defaultdict(
        lambda: {"appointments": 0, "sessions": 0, "revenue": 0.0, "reasons": Counter()}
    )
    for a in appointments:
        city = (a.therapist.city if a.therapist else "") or "Belirtilmemiş"
        city_data[city]["appointments"] += 1
    for s in sessions:
        city = s.city or (s.therapist.city if s.therapist else "") or "Belirtilmemiş"
        city_data[city]["sessions"] += 1
        for reason in s.reason_list():
            city_data[city]["reasons"][reason] += 1
    for i in invoices:
        if i.status != "odendi":
            continue
        city = (i.therapist.city if i.therapist else "") or "Belirtilmemiş"
        city_data[city]["revenue"] += i.amount or 0

    branch_cards = []
    for city, values in sorted(
        city_data.items(), key=lambda kv: (kv[1]["appointments"], kv[1]["sessions"]), reverse=True
    ):
        reason_total = sum(values["reasons"].values())
        branch_cards.append(
            {
                "city": city,
                "appointments": values["appointments"],
                "sessions": values["sessions"],
                "revenue": values["revenue"],
                "top": [
                    {"label": r, "pct": _pct(c, reason_total)}
                    for r, c in values["reasons"].most_common(3)
                ],
            }
        )

    # ── Terapist analizi
    therapist_data = defaultdict(
        lambda: {
            "appointments": 0,
            "completed": 0,
            "sessions": 0,
            "revenue": 0.0,
            "reasons": Counter(),
        }
    )
    therapist_meta = {}
    for a in appointments:
        row = therapist_data[a.therapist_id]
        row["appointments"] += 1
        if a.status == "tamamlandi":
            row["completed"] += 1
        if a.therapist:
            therapist_meta[a.therapist_id] = a.therapist
    for s in sessions:
        row = therapist_data[s.therapist_id]
        row["sessions"] += 1
        for reason in s.reason_list():
            row["reasons"][reason] += 1
        if s.therapist:
            therapist_meta.setdefault(s.therapist_id, s.therapist)
    for i in invoices:
        if i.therapist_id and i.status == "odendi":
            therapist_data[i.therapist_id]["revenue"] += i.amount or 0

    therapist_cards = []
    for tid, values in sorted(
        therapist_data.items(), key=lambda kv: kv[1]["appointments"], reverse=True
    ):
        therapist = therapist_meta.get(tid) or Therapist.query.get(tid)
        reason_total = sum(values["reasons"].values())
        therapist_cards.append(
            {
                "id": tid,
                "name": therapist.name if therapist else f"#{tid}",
                "city": therapist.city if therapist else "",
                "appointments": values["appointments"],
                "sessions": values["sessions"],
                "revenue": values["revenue"],
                "completion_pct": _pct(values["completed"], values["appointments"]),
                "reasons": [
                    {"label": r, "pct": _pct(c, reason_total)}
                    for r, c in values["reasons"].most_common(4)
                ],
            }
        )

    # ── Test analizi
    test_groups = defaultdict(lambda: {"count": 0, "score": 0.0, "levels": Counter(), "slug": ""})
    for t in tests:
        title = t.test.title if t.test else f"Test #{t.test_id}"
        row = test_groups[title]
        row["count"] += 1
        row["score"] += t.score or 0
        row["slug"] = t.test.slug if t.test else ""
        if t.level:
            row["levels"][t.level] += 1
    test_stats = [
        {
            "title": title,
            "count": row["count"],
            "avg_score": round(row["score"] / row["count"], 1) if row["count"] else 0,
            "top_level": row["levels"].most_common(1)[0][0] if row["levels"] else "—",
            "slug": row["slug"],
        }
        for title, row in sorted(test_groups.items(), key=lambda kv: kv[1]["count"], reverse=True)
    ]

    # ── Son hareketler
    recent = []
    for a in sorted(appointments, key=lambda x: x.created_at or datetime.min, reverse=True)[:4]:
        recent.append(
            {
                "icon": "📅",
                "title": f"{a.patient_name} — randevu",
                "meta": f"{a.appointment_date.strftime('%d.%m.%Y')} · {Appointment.STATUS_LABELS.get(a.status, a.status)}",
                "href": "/admin/randevular",
                "when": a.created_at,
            }
        )
    for s in sessions[:4]:
        recent.append(
            {
                "icon": "🩺",
                "title": f"{s.patient_name or s.patient_email} — seans kaydı",
                "meta": ", ".join(s.reason_list()[:3]) or "Neden belirtilmemiş",
                "href": "/admin/seanslar",
                "when": s.created_at,
            }
        )
    for i in invoices[:3]:
        recent.append(
            {
                "icon": "💳",
                "title": f"{i.patient_name or i.patient_email} — fatura",
                "meta": f"{i.amount:,.0f} ₺".replace(",", ".") + f" · {Invoice.STATUS_LABELS.get(i.status, i.status)}",
                "href": "/admin/faturalar",
                "when": i.created_at,
            }
        )
    for t in tests[:3]:
        recent.append(
            {
                "icon": "📋",
                "title": f"{t.patient_name or t.patient_email or 'Anonim'} — {t.test.title if t.test else 'test'}",
                "meta": t.level or f"Puan {t.score:.0f}",
                "href": "/admin/testler",
                "when": t.created_at,
            }
        )
    recent.sort(key=lambda r: r["when"] or datetime.min, reverse=True)
    recent_activity = recent[:8]

    # ── Sistem bütünlüğü kontrolleri
    unlinked_sessions = sum(1 for s in sessions if not s.client_user_id)
    appointments_without_session = sum(
        1
        for a in appointments
        if a.status == "tamamlandi"
        and not any((s.patient_email or "").lower() == (a.patient_email or "").lower() for s in sessions)
    )
    profile_emails = {(p.email or "").lower() for p in ClientProfile.query.all()}
    appointment_emails = {
        (a.patient_email or "").lower() for a in appointment_query.all() if a.patient_email
    }
    missing_membership = len(appointment_emails - profile_emails)
    unlinked_records = (
        session_query.filter(
            SessionRecord.client_user_id.is_(None), SessionRecord.patient_email != ""
        ).count()
        + invoice_query.filter(Invoice.client_user_id.is_(None), Invoice.patient_email != "").count()
        + TestResult.query.filter(TestResult.user_id.is_(None), TestResult.patient_email != "").count()
    )
    sync_needed = missing_membership + unlinked_records

    health = []
    if missing_membership:
        health.append(
            {
                "tone": "warn",
                "text": f"{missing_membership} randevu e-postasının üyeliği yok.",
                "href": "/admin/kullanicilar",
                "action": "Üyelikler",
            }
        )
    if pending_invites:
        health.append(
            {
                "tone": "warn",
                "text": f"{pending_invites} üye ilk giriş şifresini belirlemedi.",
                "href": "/admin/kullanicilar",
                "action": "Üyeleri gör",
            }
        )
    if unlinked_sessions:
        health.append(
            {
                "tone": "warn",
                "text": f"{unlinked_sessions} seans kaydı bir üyelikle eşleşmiyor.",
                "href": "/admin/seanslar",
                "action": "Seansları gör",
            }
        )
    if appointments_without_session:
        health.append(
            {
                "tone": "warn",
                "text": f"{appointments_without_session} tamamlanan randevunun seans kaydı yok.",
                "href": "/admin/seans/yeni",
                "action": "Seans kaydı aç",
            }
        )
    if pending_amount:
        health.append(
            {
                "tone": "warn",
                "text": f"{pending_amount:,.0f} ₺ tahsil edilmemiş fatura var.".replace(",", "."),
                "href": "/admin/faturalar",
                "action": "Faturalar",
            }
        )
    if not health:
        health.append(
            {
                "tone": "ok",
                "text": "Randevu, seans, üyelik ve fatura kayıtları birbiriyle tutarlı.",
                "href": "/admin/seanslar",
                "action": "Seanslar",
            }
        )

    tip = build_content_tips(session_query)

    return {
        "year": year,
        "month": month,
        "month_label": f"{TR_MONTHS[month - 1]} {year}",
        "months": list(enumerate(TR_MONTHS, start=1)),
        "kpis": kpis,
        "total_sessions": len(sessions),
        "total_appointments": len(appointments),
        "reason_stats": reason_stats,
        "chart": {
            "labels": [r["label"] for r in reason_stats[:8]],
            "values": [r["pct"] for r in reason_stats[:8]],
        },
        "trend_chart": {
            "labels": trend_labels,
            "appointments": trend_appointments,
            "sessions": trend_sessions,
            "revenue": trend_revenue,
        },
        "status_chart": {
            "labels": [Appointment.STATUS_LABELS.get(k, k) for k in status_counter],
            "values": list(status_counter.values()),
        },
        "type_chart": {
            "labels": [Appointment.SESSION_LABELS.get(k, k) for k in type_counter],
            "values": list(type_counter.values()),
        },
        "revenue": {"paid": paid, "pending": pending_amount, "count": len(invoices)},
        "clients": {
            "active": active_clients,
            "pending_invites": pending_invites,
            "new": new_clients,
        },
        "branch_cards": branch_cards,
        "therapist_cards": therapist_cards,
        "test_stats": test_stats,
        "recent_activity": recent_activity,
        "health": health,
        "sync_needed": sync_needed,
        "content_tip": tip,
        "top_reason": reason_stats[0] if reason_stats else None,
        "second_reason": reason_stats[1] if len(reason_stats) > 1 else None,
    }


def build_content_tips(base_query=None):
    from models import SessionRecord

    query = base_query if base_query is not None else SessionRecord.query
    today = date.today()
    recent_start = today - timedelta(days=30)
    prev_start = today - timedelta(days=60)
    prev_end = recent_start - timedelta(days=1)

    recent = _sessions_in_range(query, recent_start, today)
    previous = _sessions_in_range(query, prev_start, prev_end)

    recent_c = Counter()
    prev_c = Counter()
    for s in recent:
        for r in s.reason_list():
            recent_c[r] += 1
    for s in previous:
        for r in s.reason_list():
            prev_c[r] += 1

    best_reason = None
    best_growth = 0
    for reason, count in recent_c.items():
        prev = prev_c.get(reason, 0)
        if prev == 0:
            growth = 100 if count else 0
        else:
            growth = round((count - prev) * 100 / prev)
        if growth > best_growth:
            best_growth = growth
            best_reason = reason

    if not best_reason:
        best_reason = recent_c.most_common(1)[0][0] if recent_c else "Kaygı"
        best_growth = 0

    actions = []
    for tpl in CONTENT_ACTION_TEMPLATES:
        actions.append(
            {
                "icon": tpl["icon"],
                "title": tpl["title"],
                "hint": tpl["hint"].format(reason=best_reason),
                "href": tpl["href"],
                "action": tpl["action"],
            }
        )

    return {
        "reason": best_reason,
        "growth": best_growth,
        "recent_total": sum(recent_c.values()),
        "has_data": bool(recent_c),
        "message": f"Son 30 günde {best_reason} başvuruları %{best_growth} arttı"
        if best_growth
        else f"Son 30 günde öne çıkan başvuru nedeni: {best_reason}",
        "actions": actions,
    }