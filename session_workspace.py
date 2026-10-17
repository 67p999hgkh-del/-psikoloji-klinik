"""Clinical Session Workspace — list KPIs, filters, drawer payload, permissions."""
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

from psikoplan import APPLICATION_REASONS, PAYMENT_LABELS, build_session_ai_summary, payment_status_map

NOTE_TEMPLATES = {
    "free": "Serbest Klinik Not",
    "soap": "SOAP",
    "dap": "DAP",
    "birp": "BIRP",
    "intake": "İlk Görüşme Formu",
    "child": "Çocuk-Ergen Görüşme Formu",
    "couple": "Çift Terapisi Notu",
    "crisis": "Kriz Görüşmesi Notu",
}

NOTE_TEMPLATE_FIELDS = {
    "soap": ["subjective", "objective", "assessment", "plan"],
    "dap": ["data", "assessment", "plan"],
    "birp": ["behavior", "intervention", "response", "plan"],
    "intake": ["presenting_problem", "history", "assessment", "plan"],
    "child": ["observation", "interaction", "assessment", "plan"],
    "couple": ["dynamics", "intervention", "response", "plan"],
    "crisis": ["trigger", "presentation", "intervention", "safety_plan"],
    "free": ["body"],
}

THERAPY_APPROACHES = [
    "BDT",
    "EMDR",
    "Psikanalitik",
    "Sistemik",
    "ACT",
    "DBT",
    "Oyun Terapisi",
    "Çözüm Odaklı",
    "Diğer",
]

WORKSPACE_STATUS_LABELS = {
    "planlandi": "Planlandı",
    "basladi": "Başladı",
    "tamamlandi": "Tamamlandı",
    "not_bekliyor": "Not Bekliyor",
    "taslak": "Taslak",
    "imzalandi": "İmzalandı",
    "iptal": "İptal",
    "gelmedi": "Gelmedi",
    "devam": "Devam Ediyor",
    "beklemede": "Beklemede",
    "sonlandi": "Sonlandı",
}

HOMEWORK_TEMPLATES = [
    "Düşünce kaydı",
    "Duygu günlüğü",
    "Maruz bırakma çalışması",
    "Nefes egzersizi",
    "Uyku günlüğü",
    "Davranış aktivasyonu",
    "İletişim çalışması",
    "Farkındalık egzersizi",
]

TASK_TYPES = [
    "Danışanı ara",
    "Test sonucu kontrol et",
    "Ödev geri bildirimi incele",
    "Süpervizyon notu ekle",
    "Psikiyatri yönlendirmesini takip et",
    "Belge bekleniyor",
    "Randevu oluştur",
    "Ödeme takibi",
    "Risk takibi",
]

DOCUMENT_TYPES = [
    "Onam formu",
    "Aydınlatma metni",
    "Test raporu",
    "Doktor raporu",
    "Değerlendirme formu",
    "Danışan belgesi",
    "Seans PDF",
    "Görsel",
    "Diğer",
]


def can_view_clinical(user):
    return user.role in ("admin", "therapist")


def can_view_risk(user):
    return user.role in ("admin", "therapist")


def can_view_supervision(user):
    return user.role == "admin"


def can_edit_session(user, record):
    if user.role == "admin":
        return True
    if user.role == "therapist" and user.therapist_id == record.therapist_id:
        return True
    return False


def _default_workspace(record):
    ws = record.workspace_dict()
    note = ws.get("note") or {}
    if not note:
        note = {
            "template": "free",
            "status": "taslak",
            "fields": {"body": record.note or ""},
            "last_saved_at": None,
            "signed_at": None,
            "locked": False,
        }
        ws["note"] = note
    ws.setdefault("therapy_plan", {"status": "taslak", "approach": "", "goals": [], "history": []})
    ws.setdefault("goals", [])
    ws.setdefault("homework", [])
    for list_key in ("goals", "homework", "assigned_tests", "documents", "follow_up_tasks"):
        if not isinstance(ws.get(list_key), list):
            ws[list_key] = []
    ws.setdefault("risk", {"level": record.risk_level, "notes": "", "safety_plan": ""})
    ws.setdefault("documents", [])
    ws.setdefault("follow_up_tasks", [])
    ws.setdefault("supervision", {"requests": []})
    ws.setdefault("timer", {"planned_minutes": record.duration_minutes or 50, "elapsed_seconds": 0, "running": False})
    ws.setdefault("ai_summary", {"sections": {}, "generated_at": None})
    return ws


def workspace_display_status(record, ws=None):
    ws = ws or _default_workspace(record)
    note_status = (ws.get("note") or {}).get("status", "taslak")
    if record.status == "gelmedi":
        return "gelmedi", WORKSPACE_STATUS_LABELS["gelmedi"]
    if note_status == "imzalandi":
        return "imzalandi", WORKSPACE_STATUS_LABELS["imzalandi"]
    if note_status == "taslak" and not (record.note or "").strip():
        return "not_bekliyor", WORKSPACE_STATUS_LABELS["not_bekliyor"]
    if note_status == "taslak":
        return "taslak", WORKSPACE_STATUS_LABELS["taslak"]
    if record.status == "sonlandi":
        return "tamamlandi", WORKSPACE_STATUS_LABELS["tamamlandi"]
    if record.status == "devam":
        timer = ws.get("timer") or {}
        if timer.get("running"):
            return "basladi", WORKSPACE_STATUS_LABELS["basladi"]
        return "devam", WORKSPACE_STATUS_LABELS["devam"]
    if record.status == "beklemede":
        return "planlandi", WORKSPACE_STATUS_LABELS["planlandi"]
    return record.status, WORKSPACE_STATUS_LABELS.get(record.status, record.status_label)


def note_status_label(record, ws=None):
    ws = ws or _default_workspace(record)
    note = ws.get("note") or {}
    status = note.get("status", "taslak")
    fields = note.get("fields") or {}
    has_content = any(str(v).strip() for v in fields.values()) or (record.note or "").strip()
    if status == "imzalandi":
        return "İmzalandı"
    if status == "locked":
        return "Kilitli"
    if not has_content:
        return "Not eksik"
    return "Taslak"


def apply_session_filters(scope, args):
    from models import SessionRecord, db

    search = (args.get("q") or "").strip()
    if search:
        like = f"%{search}%"
        scope = scope.filter(
            db.or_(
                SessionRecord.patient_name.ilike(like),
                SessionRecord.patient_email.ilike(like),
                SessionRecord.note.ilike(like),
            )
        )

    therapist_id = args.get("therapist_id")
    if therapist_id:
        try:
            scope = scope.filter_by(therapist_id=int(therapist_id))
        except (ValueError, TypeError):
            pass

    for key, col in [
        ("city", SessionRecord.city),
        ("status", SessionRecord.status),
        ("session_type", SessionRecord.session_type),
        ("risk", SessionRecord.risk_level),
    ]:
        val = (args.get(key) or "").strip()
        if val:
            scope = scope.filter(col == val)

    reason = (args.get("reason") or "").strip()
    if reason:
        scope = scope.filter(SessionRecord.reasons.ilike(f"%{reason}%"))

    approach = (args.get("approach") or "").strip()
    if approach:
        scope = scope.filter(SessionRecord.workspace_data.ilike(f"%{approach}%"))

    date_from = _parse_date(args.get("from"))
    date_to = _parse_date(args.get("to"))
    if date_from:
        scope = scope.filter(SessionRecord.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        scope = scope.filter(SessionRecord.created_at <= datetime.combine(date_to, datetime.max.time()))

    filters = {
        "q": search,
        "therapist_id": int(therapist_id) if therapist_id else None,
        "city": (args.get("city") or "").strip(),
        "reason": reason,
        "status": (args.get("status") or "").strip(),
        "view_status": (args.get("view_status") or "").strip(),
        "session_type": (args.get("session_type") or "").strip(),
        "risk": (args.get("risk") or "").strip(),
        "approach": approach,
        "visit_type": (args.get("visit_type") or "").strip(),
        "note_status": (args.get("note_status") or "").strip(),
        "payment": (args.get("payment") or "").strip(),
        "from": (args.get("from") or "").strip(),
        "to": (args.get("to") or "").strip(),
        "kpi": (args.get("kpi") or "").strip(),
        "homework": (args.get("homework") or "").strip(),
    }
    return scope, filters


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def reason_slug_for_session(session):
    """Map first başvuru nedeni to CSS modifier used by session list badges."""
    reasons = session.reason_list() if hasattr(session, "reason_list") else []
    if not reasons:
        return "default"
    raw = (reasons[0] or "").strip().lower()
    mapping = (
        ("kaygı", "kaygi"),
        ("kaygi", "kaygi"),
        ("depres", "depresyon"),
        ("panik", "panik"),
        ("okb", "okb"),
        ("travma", "travma"),
        ("yas", "yas"),
        ("ilişki", "iliski"),
        ("iliski", "iliski"),
        ("çift", "cift"),
        ("cift", "cift"),
        ("dehb", "dehb"),
        ("sınav", "sinav"),
        ("sinav", "sinav"),
    )
    for needle, slug in mapping:
        if needle in raw:
            return slug
    return "default"


def build_session_rows(sessions, all_sessions, payments):
    by_email = defaultdict(list)
    for s in sorted(all_sessions, key=lambda x: x.created_at or datetime.min):
        if s.patient_email:
            by_email[(s.patient_email or "").lower()].append(s)

    rows = []
    for s in sessions:
        email = (s.patient_email or "").lower()
        prior = [x for x in by_email.get(email, []) if x.id != s.id and (x.created_at or datetime.min) <= (s.created_at or datetime.min)]
        visit_type = "İlk Görüşme" if not prior else "Takip"
        ws = _default_workspace(s)
        disp_key, disp_label = workspace_display_status(s, ws)
        date_label, time_label = format_session_datetime_tr(s.created_at)
        rows.append(
            {
                "session": s,
                "visit_type": visit_type,
                "session_number": len(prior) + 1,
                "date_label": date_label,
                "time_label": time_label,
                "display_status_key": disp_key,
                "display_status_label": disp_label,
                "list_status_label": disp_label,
                "reason_slug": reason_slug_for_session(s),
                "note_status_label": note_status_label(s, ws),
                "payment_key": payments.get(email, "yok"),
                "payment_label": PAYMENT_LABELS.get(payments.get(email, "yok"), "—"),
            }
        )
    return rows


def filter_rows_by_extra(rows, filters):
    result = rows
    if filters.get("visit_type"):
        result = [r for r in result if r["visit_type"] == filters["visit_type"]]
    if filters.get("note_status"):
        ns = filters["note_status"]
        result = [r for r in result if _note_status_key(r) == ns]
    if filters.get("payment"):
        result = [r for r in result if r["payment_key"] == filters["payment"]]
    return result


def _note_status_key(row):
    label = row["note_status_label"]
    if label == "Not eksik":
        return "eksik"
    if label == "İmzalandı":
        return "imzalandi"
    if label == "Kilitli":
        return "kilitli"
    return "taslak"


SESSION_LIST_STATUS_FILTERS = [
    ("planlandi", "Planlandı"),
    ("basladi", "Başladı"),
    ("devam", "Devam Ediyor"),
    ("tamamlandi", "Tamamlandı"),
    ("not_bekliyor", "Not Bekliyor"),
    ("gelmedi", "Gelmedi"),
    ("iptal", "İptal"),
    ("sonlandi", "Sonlandı"),
]

HOMEWORK_CLOSED_STATUSES = {"tamamlandi", "iptal", "taslak"}

SESSION_HOMEWORK_FILTERS = [
    ("open", "Açık ödev var"),
    ("overdue", "Geciken ödev"),
]

HOMEWORK_FILTER_LABELS = dict(SESSION_HOMEWORK_FILTERS)


def _parse_hw_due(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def session_homework_flags(session, today=None):
    """Return (has_open, has_overdue) for workspace homework items."""
    today = today or date.today()
    ws = _default_workspace(session)
    has_open = has_overdue = False
    for hw in ws.get("homework") or []:
        status = hw.get("status") or "atandi"
        if status in HOMEWORK_CLOSED_STATUSES:
            continue
        has_open = True
        due = _parse_hw_due(hw.get("due_date"))
        if due and due < today:
            has_overdue = True
    return has_open, has_overdue


def filter_sessions_by_homework(sessions, mode, today=None):
    today = today or date.today()
    if mode == "open":
        return [s for s in sessions if session_homework_flags(s, today)[0]]
    if mode == "overdue":
        return [s for s in sessions if session_homework_flags(s, today)[1]]
    return sessions


def filter_sessions_by_view_status(sessions, view_status):
    if not view_status:
        return sessions
    return [
        s
        for s in sessions
        if workspace_display_status(s, _default_workspace(s))[0] == view_status
    ]


def refine_session_list(sessions, filters, today=None):
    today = today or date.today()
    result = filter_sessions_by_view_status(sessions, filters.get("view_status"))
    return filter_sessions_by_homework(result, filters.get("homework") or "", today)

KPI_STATUS_KEYS = {
    "pending": {"not_bekliyor", "planlandi", "basladi", "devam", "beklemede", "taslak"},
    "noshow": {"gelmedi"},
    "done": {"tamamlandi", "imzalandi", "sonlandi"},
    "cancelled": {"iptal"},
}


def format_session_datetime_tr(dt):
    if not dt:
        return "—", "—"
    months = (
        "",
        "Ocak",
        "Şubat",
        "Mart",
        "Nisan",
        "Mayıs",
        "Haziran",
        "Temmuz",
        "Ağustos",
        "Eylül",
        "Ekim",
        "Kasım",
        "Aralık",
    )
    date_label = f"{dt.day:02d} {months[dt.month]} {dt.year}"
    time_label = dt.strftime("%H:%M")
    return date_label, time_label


def detect_date_preset(date_from, date_to, today=None):
    today = today or date.today()
    if not date_from and not date_to:
        return ""
    try:
        start = datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else None
        end = datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else None
    except (ValueError, TypeError):
        return "custom"
    if start == end == today:
        return "today"
    week_start = today - timedelta(days=today.weekday())
    if start == week_start and end == today:
        return "week"
    month_start = today.replace(day=1)
    if start == month_start and end == today:
        return "month"
    return "custom"


def count_advanced_filters(filters, is_therapist_view=False):
    keys = ["reason", "visit_type", "note_status", "payment", "city", "approach", "session_type", "homework"]
    if not is_therapist_view:
        keys.append("therapist_id")
    return sum(1 for key in keys if filters.get(key))


def filter_sessions_by_kpi(sessions, kpi, today=None):
    today = today or date.today()
    if kpi == "today":
        start = datetime.combine(today, datetime.min.time())
        end = datetime.combine(today, datetime.max.time())
        return [s for s in sessions if s.created_at and start <= s.created_at <= end]
    allowed = KPI_STATUS_KEYS.get(kpi)
    if not allowed:
        return sessions
    return [s for s in sessions if workspace_display_status(s)[0] in allowed]


def build_session_list_kpis(filtered_sessions, today):
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    today_count = sum(
        1 for s in filtered_sessions if s.created_at and today_start <= s.created_at <= today_end
    )
    pending = no_show = completed = cancelled = 0
    for s in filtered_sessions:
        key, _ = workspace_display_status(s, _default_workspace(s))
        if key == "gelmedi":
            no_show += 1
        elif key == "iptal":
            cancelled += 1
        elif key in ("tamamlandi", "imzalandi", "sonlandi"):
            completed += 1
        elif key in ("not_bekliyor", "planlandi", "basladi", "devam", "beklemede", "taslak"):
            pending += 1
    return [
        {"label": "Bugünkü Seanslar", "value": today_count, "key": "today"},
        {"label": "Bekleyen", "value": pending, "key": "pending"},
        {"label": "Gelmeyen", "value": no_show, "key": "noshow"},
        {"label": "Tamamlanan", "value": completed, "key": "done"},
        {"label": "İptal", "value": cancelled, "key": "cancelled"},
    ]


def build_kpi_filter_urls(filters):
    base = {k: v for k, v in filters.items() if v and k not in ("kpi", "page")}
    urls = {}
    for key in ("today", "pending", "noshow", "done", "cancelled"):
        if filters.get("kpi") == key:
            urls[key] = base
        else:
            urls[key] = {**base, "kpi": key}
    return urls


def build_session_kpis(filtered_sessions, all_sessions, today):
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    today_list = [s for s in filtered_sessions if s.created_at and today_start <= s.created_at <= today_end]

    missing_notes = 0
    risk_notes = 0
    for s in filtered_sessions:
        ws = _default_workspace(s)
        if note_status_label(s, ws) == "Not eksik":
            missing_notes += 1
        risk = ws.get("risk") or {}
        if s.risk_level in ("orta", "yuksek") or (risk.get("notes") or "").strip():
            risk_notes += 1

    follow_up_pending = sum(
        1
        for s in filtered_sessions
        if s.status == "devam" and not s.next_session_date
    )

    return [
        {"label": "Bugünkü Seans", "value": len(today_list), "tone": "blue"},
        {"label": "Devam Eden", "value": sum(1 for s in filtered_sessions if s.status == "devam"), "tone": "cyan"},
        {"label": "Tamamlanan", "value": sum(1 for s in filtered_sessions if s.status == "sonlandi"), "tone": "emerald"},
        {"label": "Notu Eksik", "value": missing_notes, "tone": "amber"},
        {"label": "Takip Bekleyen", "value": follow_up_pending, "tone": "violet"},
        {"label": "Risk Notu", "value": risk_notes, "tone": "rose"},
        {"label": "Online", "value": sum(1 for s in filtered_sessions if s.session_type == "online"), "tone": "indigo"},
        {"label": "Yüz Yüze", "value": sum(1 for s in filtered_sessions if s.session_type == "yuz_yuze"), "tone": "slate"},
    ]


def build_active_filter_chips(filters, status_labels, payment_labels):
    chips = []
    mapping = {
        "q": ("Arama", filters.get("q")),
        "therapist_id": ("Terapist", filters.get("therapist_id")),
        "city": ("Şube", filters.get("city")),
        "reason": ("Neden", filters.get("reason")),
        "status": ("Durum", status_labels.get(filters.get("status"), filters.get("status"))),
        "session_type": ("Tür", filters.get("session_type")),
        "risk": ("Risk", filters.get("risk")),
        "approach": ("Yaklaşım", filters.get("approach")),
        "visit_type": ("Seans türü", filters.get("visit_type")),
        "note_status": ("Not", filters.get("note_status")),
        "payment": ("Ödeme", payment_labels.get(filters.get("payment"), filters.get("payment"))),
        "from": ("Başlangıç", filters.get("from")),
        "to": ("Bitiş", filters.get("to")),
        "view_status": ("Liste durumu", dict(SESSION_LIST_STATUS_FILTERS).get(filters.get("view_status"), filters.get("view_status"))),
        "homework": ("Ödev", HOMEWORK_FILTER_LABELS.get(filters.get("homework"), filters.get("homework"))),
    }
    for key, (label, val) in mapping.items():
        if val:
            chips.append({"key": key, "label": label, "value": val})
    return chips


def build_workspace_payload(record, user):
    from models import Appointment, ClientProfile, Invoice, SessionRecord, TestResult, TherapistNote

    email = (record.patient_email or "").lower()
    profile = ClientProfile.query.filter(ClientProfile.email.ilike(email)).first() if email else None
    ws = _default_workspace(record)

    all_client_sessions = (
        SessionRecord.query.filter(SessionRecord.patient_email.ilike(email))
        .order_by(SessionRecord.created_at.desc())
        .all()
        if email
        else []
    )
    tests = (
        TestResult.query.filter(TestResult.patient_email.ilike(email))
        .order_by(TestResult.created_at.desc())
        .limit(10)
        .all()
        if email
        else []
    )
    notes = (
        TherapistNote.query.filter(TherapistNote.patient_email.ilike(email))
        .order_by(TherapistNote.created_at.desc())
        .limit(8)
        .all()
        if email
        else []
    )
    invoices = (
        Invoice.query.filter(Invoice.patient_email.ilike(email))
        .order_by(Invoice.invoice_date.desc())
        .limit(8)
        .all()
        if email
        else []
    )
    next_appointment = (
        Appointment.query.filter(
            Appointment.patient_email.ilike(email),
            Appointment.appointment_date >= date.today(),
            Appointment.status.in_(["beklemede", "onaylandi"]),
        )
        .order_by(Appointment.appointment_date.asc(), Appointment.appointment_time.asc())
        .first()
        if email
        else None
    )

    first_session = all_client_sessions[-1] if all_client_sessions else None
    disp_key, disp_label = workspace_display_status(record, ws)
    clinical_visible = can_view_clinical(user)
    risk_visible = can_view_risk(user)
    supervision_visible = can_view_supervision(user)

    therapy_plan = ws.get("therapy_plan") or {}
    note_fields = (ws.get("note") or {}).get("fields") or {}
    note_body = " ".join(str(v).strip() for v in note_fields.values() if v).strip() or (record.note or "").strip()
    approach = therapy_plan.get("approach") or ""
    homework_open = [h for h in (ws.get("homework") or []) if h.get("status") not in ("tamamlandi", "iptal")]

    overview = {
        "name": record.patient_name or (profile.full_name if profile else email) or "—",
        "email": record.patient_email if clinical_visible else "—",
        "phone": (profile.phone if profile else "") if clinical_visible else "—",
        "age_group": ws.get("age_group") or "",
        "age_group_label": ws.get("age_group") or "—",
        "reasons": record.reason_list(),
        "first_session_date": first_session.created_at.strftime("%d.%m.%Y") if first_session and first_session.created_at else "—",
        "total_sessions": len(all_client_sessions),
        "last_session_date": (
            all_client_sessions[1].created_at.strftime("%d.%m.%Y")
            if len(all_client_sessions) > 1 and all_client_sessions[1].created_at
            else (record.created_at.strftime("%d.%m.%Y") if record.created_at else "—")
        ),
        "approach": approach,
        "approach_label": approach or "—",
        "active_goals": [g for g in ws.get("goals", []) if g.get("status") == "devam"],
        "active_homework_count": len(homework_open),
        "recent_tests": [
            {"title": t.test.title if t.test else "Test", "level": t.level or "—", "date": t.created_at.strftime("%d.%m.%Y") if t.created_at else ""}
            for t in tests[:3]
        ],
        "open_tasks": [t for t in ws.get("follow_up_tasks", []) if t.get("status") in ("acik", "devam")],
        "display_status": disp_label,
        "display_status_key": disp_key,
        "payment_status": PAYMENT_LABELS.get(payment_status_map({email}).get(email, "yok"), "—"),
        "next_appointment_label": (
            f"{next_appointment.appointment_date.strftime('%d.%m.%Y')} · {next_appointment.appointment_time.strftime('%H:%M')}"
            if next_appointment and next_appointment.appointment_time
            else (next_appointment.appointment_date.strftime("%d.%m.%Y") if next_appointment else "Planlanmadı")
        ),
        "note_preview_label": (note_body[:120] + ("…" if len(note_body) > 120 else "")) if note_body else "Henüz not girilmedi",
        "plan_summary_label": (therapy_plan.get("goals_text") or therapy_plan.get("primary_reason") or "Henüz plan oluşturulmadı").strip()[:120],
    }

    history = []
    for h in all_client_sessions:
        hws = _default_workspace(h)
        history.append(
            {
                "id": h.id,
                "date": h.created_at.strftime("%d.%m.%Y %H:%M") if h.created_at else "",
                "type": h.session_type_label,
                "therapist": h.therapist.name if h.therapist else "—",
                "theme": (hws.get("note") or {}).get("fields", {}).get("assessment") or (h.note or "")[:80] or "—",
                "test": "",
                "homework": len(hws.get("homework") or []),
                "risk_note": (hws.get("risk") or {}).get("notes", "")[:60] if risk_visible else "—",
                "next_plan": h.next_session_date.strftime("%d.%m.%Y") if h.next_session_date else "—",
                "note_status": note_status_label(h, hws),
                "current": h.id == record.id,
            }
        )

    ai_draft = generate_ai_summary_draft(record, ws) if clinical_visible else None

    return {
        "id": record.id,
        "permissions": {
            "clinical": clinical_visible,
            "risk": risk_visible,
            "supervision": supervision_visible,
            "edit": can_edit_session(user, record),
        },
        "header": {
            "title": overview["name"],
            "subtitle": f"{record.created_at.strftime('%d.%m.%Y %H:%M') if record.created_at else ''} · {record.session_type_label} · {record.duration_minutes or 50} dk",
            "status": disp_label,
            "status_key": disp_key,
        },
        "overview": overview,
        "note": ws.get("note") if clinical_visible else None,
        "note_templates": NOTE_TEMPLATES,
        "note_template_fields": NOTE_TEMPLATE_FIELDS,
        "therapy_plan": ws.get("therapy_plan") if clinical_visible else None,
        "therapy_approaches": THERAPY_APPROACHES,
        "goals": ws.get("goals") if clinical_visible else [],
        "homework": ws.get("homework") if clinical_visible else [],
        "assigned_tests": ws.get("assigned_tests") if clinical_visible else [],
        "homework_templates": HOMEWORK_TEMPLATES,
        "risk": ws.get("risk") if risk_visible else None,
        "documents": ws.get("documents") if clinical_visible else [],
        "document_types": DOCUMENT_TYPES,
        "payments": [
            {
                "date": i.invoice_date.strftime("%d.%m.%Y") if i.invoice_date else "",
                "amount": f"{i.amount:,.0f} ₺".replace(",", "."),
                "status": Invoice.STATUS_LABELS.get(i.status, i.status),
            }
            for i in invoices
        ],
        "history": history if clinical_visible else [],
        "follow_up_tasks": ws.get("follow_up_tasks") if clinical_visible else [],
        "task_types": TASK_TYPES,
        "supervision": ws.get("supervision") if supervision_visible else None,
        "timer": ws.get("timer"),
        "tests": [
            {
                "title": t.test.title if t.test else "Test",
                "date": t.created_at.strftime("%d.%m.%Y") if t.created_at else "",
                "score": round(t.score or 0, 1),
                "level": t.level or "—",
            }
            for t in tests
        ],
        "therapist_notes": [
            {"date": n.created_at.strftime("%d.%m.%Y") if n.created_at else "", "body": n.body, "therapist": n.therapist.name if n.therapist else "—"}
            for n in notes
        ] if clinical_visible else [],
        "ai_summary": ai_draft,
        "ai_disclaimer": "Bu içerik yapay zekâ tarafından oluşturulan düzenlenebilir bir taslaktır. Klinik değerlendirme ve nihai kayıt terapiste aittir.",
        "next_appointment": (
            {
                "date": next_appointment.appointment_date.strftime("%d.%m.%Y"),
                "time": next_appointment.appointment_time.strftime("%H:%M"),
                "therapist": next_appointment.therapist.name if next_appointment.therapist else "—",
            }
            if next_appointment
            else None
        ),
        "legacy_summary": build_session_ai_summary(record),
    }


def generate_ai_summary_draft(record, ws):
    note = ws.get("note") or {}
    fields = note.get("fields") or {}
    body = " ".join(str(v) for v in fields.values() if v).strip() or (record.note or "")
    reasons = ", ".join(record.reason_list()[:3]) or "belirtilmemiş"
    if not body.strip():
        return None
    words = body.split()
    excerpt = " ".join(words[:40]) + ("…" if len(words) > 40 else "")
    return {
        "sections": {
            "summary": f"Seans kapsamında {reasons} odaklı görüşme gerçekleştirildi. {excerpt}",
            "themes": f"Başvuru nedenleri: {reasons}.",
            "interventions": "Seans notundaki müdahale alanlarını gözden geçirin.",
            "responses": "Danışanın seans içi tepkileri not alanından derlenebilir.",
            "follow_up": "Takip gerektiren konular bir sonraki seans gündemine eklenebilir.",
            "next_agenda": record.next_session_date.strftime("%d.%m.%Y") if record.next_session_date else "Sonraki seans tarihi planlanmadı.",
            "homework_draft": "Ev ödevi taslağı terapist tarafından düzenlenmelidir.",
        },
        "generated_at": datetime.utcnow().isoformat(),
    }


def save_workspace_section(record, section, data, user):
    if not can_edit_session(user, record):
        return False, "Bu kaydı düzenleme yetkiniz yok."

    ws = _default_workspace(record)
    old_note = json.dumps(ws.get("note", {}), ensure_ascii=False)

    if section == "note":
        incoming = data or {}
        current = ws.get("note") or {}
        if current.get("status") == "imzalandi" and not incoming.get("change_reason"):
            return False, "İmzalı not değiştirmek için gerekçe gerekir."
        if current.get("locked") and section == "note":
            return False, "Not kilitli."
        current.update({k: v for k, v in incoming.items() if k != "change_reason"})
        current["last_saved_at"] = datetime.utcnow().isoformat()
        ws["note"] = current
        body = (current.get("fields") or {}).get("body") or ""
        if not body:
            body = " ".join(str(v) for k, v in (current.get("fields") or {}).items() if v)
        record.note = body
    elif section == "risk":
        from models import SessionRecord as _SessionRecord

        ws["risk"] = data or {}
        level = (data or {}).get("level")
        if level and level in _SessionRecord.RISK_LABELS:
            record.risk_level = level
    elif section in ("goals", "homework", "assigned_tests", "documents", "follow_up_tasks"):
        ws[section] = data if isinstance(data, list) else []
    elif section in ws:
        ws[section] = data
    else:
        ws[section] = data

    record.set_workspace_dict(ws)
    return True, old_note

def has_note_content(record, ws=None):
    ws = ws or _default_workspace(record)
    note = ws.get("note") or {}
    fields = note.get("fields") or {}
    return any(str(v).strip() for v in fields.values()) or bool((record.note or "").strip())


def get_completion_checklist(record, ws, user):
    email = (record.patient_email or "").lower()
    pay = payment_status_map({email}).get(email, "yok") if email else "yok"
    return {
        "timer_saved": bool((ws.get("timer") or {}).get("finished")),
        "has_note": has_note_content(record, ws),
        "has_next_appointment": bool(record.next_session_date),
        "has_homework_or_task": bool(ws.get("homework")) or bool(ws.get("follow_up_tasks")),
        "payment_status": PAYMENT_LABELS.get(pay, pay),
        "payment_ok": pay == "odendi",
    }


def handle_workspace_action(record, user, action, data):
    from models import Appointment, PsychologicalTest, Therapist, db

    if not can_edit_session(user, record):
        return False, "Bu işlem için yetkiniz yok."

    ws = _default_workspace(record)
    data = data or {}

    if action == "add_document":
        doc = {
            "id": len(ws.get("documents") or []) + 1,
            "title": (data.get("title") or data.get("file_name") or "Belge").strip(),
            "doc_type": (data.get("doc_type") or "Diğer").strip(),
            "file_name": (data.get("file_name") or "").strip(),
            "storage_path": (data.get("storage_path") or "").strip(),
            "size_bytes": int(data.get("size_bytes") or 0),
            "notes": (data.get("notes") or "").strip(),
            "visible_to_client": bool(data.get("visible_to_client", False)),
            "created_at": datetime.utcnow().isoformat(),
            "created_by": user.username,
        }
        if not doc["storage_path"]:
            return False, "Dosya yolu gerekli."
        ws.setdefault("documents", []).append(doc)
        record.set_workspace_dict(ws)
        return True, {"item": doc, "documents": ws["documents"]}

    if action == "remove_document":
        doc_id = data.get("id")
        if doc_id is None:
            return False, "Belge kimliği gerekli."
        before = len(ws.get("documents") or [])
        ws["documents"] = [d for d in (ws.get("documents") or []) if str(d.get("id")) != str(doc_id)]
        if len(ws["documents"]) == before:
            return False, "Belge bulunamadı."
        record.set_workspace_dict(ws)
        return True, {"documents": ws["documents"]}

    if action == "remove_homework":
        hw_id = data.get("id")
        if hw_id is None:
            return False, "Ödev kimliği gerekli."
        before = len(ws.get("homework") or [])
        ws["homework"] = [h for h in (ws.get("homework") or []) if str(h.get("id")) != str(hw_id)]
        if len(ws["homework"]) == before:
            return False, "Ödev bulunamadı."
        record.set_workspace_dict(ws)
        return True, {"homework": ws["homework"]}

    if action == "update_homework":
        hw_id = data.get("id")
        if hw_id is None:
            return False, "Ödev kimliği gerekli."
        for item in ws.get("homework") or []:
            if str(item.get("id")) == str(hw_id):
                for key in (
                    "title",
                    "status",
                    "due_date",
                    "start_date",
                    "description",
                    "therapist_note",
                    "template",
                    "visible_to_client",
                    "file_name",
                ):
                    if key in data:
                        item[key] = data[key]
                record.set_workspace_dict(ws)
                return True, {"item": item, "homework": ws["homework"]}
        return False, "Ödev bulunamadı."

    if action == "add_goal":
        goals = ws.setdefault("goals", [])
        goal = {
            "id": data.get("id") or f"g-{len(goals) + 1}",
            "name": (data.get("name") or data.get("title") or "Terapi hedefi").strip(),
            "description": (data.get("description") or "").strip(),
            "status": data.get("status") or "devam",
            "progress": int(data.get("progress") or 0),
        }
        goals.append(goal)
        record.set_workspace_dict(ws)
        return True, {"goal": goal, "goals": goals}

    if action == "update_goal":
        gid = data.get("id")
        if gid is None:
            return False, "Hedef kimliği gerekli."
        for goal in ws.get("goals") or []:
            if str(goal.get("id")) == str(gid):
                for key in ("name", "title", "description", "status", "progress"):
                    if key in data:
                        val = data[key]
                        if key == "title":
                            goal["name"] = val
                        elif key == "progress":
                            goal["progress"] = int(val)
                        else:
                            goal[key] = val
                record.set_workspace_dict(ws)
                return True, {"goal": goal, "goals": ws["goals"]}
        return False, "Hedef bulunamadı."

    if action == "remove_goal":
        gid = data.get("id")
        if gid is None:
            return False, "Hedef kimliği gerekli."
        before = len(ws.get("goals") or [])
        ws["goals"] = [g for g in (ws.get("goals") or []) if str(g.get("id")) != str(gid)]
        if len(ws["goals"]) == before:
            return False, "Hedef bulunamadı."
        record.set_workspace_dict(ws)
        return True, {"goals": ws["goals"]}

    if action == "homework":
        status = data.get("status") or "atandi"
        item = {
            "id": len(ws.get("homework", [])) + 1,
            "title": (data.get("title") or "").strip() or data.get("template") or "Ödev",
            "template": data.get("template") or "Özel ödev",
            "description": (data.get("description") or "").strip(),
            "start_date": data.get("start_date") or date.today().isoformat(),
            "due_date": data.get("due_date") or "",
            "status": status,
            "visible_to_client": bool(data.get("visible_to_client", True)),
            "therapist_note": (data.get("therapist_note") or "").strip(),
            "file_name": (data.get("file_name") or "").strip(),
            "created_at": datetime.utcnow().isoformat(),
            "created_by": user.username,
            "notify_email": bool(data.get("notify_email", True)),
        }
        ws.setdefault("homework", []).append(item)
        record.set_workspace_dict(ws)
        return True, {"item": item, "homework": ws["homework"]}

    if action == "assign_test":
        test_id = data.get("test_id")
        test = PsychologicalTest.query.get(test_id) if test_id else None
        item = {
            "id": len(ws.get("assigned_tests", [])) + 1,
            "test_id": test_id,
            "title": test.title if test else (data.get("title") or "Test"),
            "phase": data.get("phase") or "on_test",
            "assigned_date": data.get("assigned_date") or date.today().isoformat(),
            "due_date": data.get("due_date") or "",
            "note": (data.get("note") or "").strip(),
            "send_to_client": bool(data.get("send_to_client", False)),
            "status": "atandi",
            "created_at": datetime.utcnow().isoformat(),
            "created_by": user.username,
        }
        ws.setdefault("assigned_tests", []).append(item)
        record.set_workspace_dict(ws)
        return True, {"item": item, "assigned_tests": ws["assigned_tests"]}

    if action == "appointment":
        therapist_id = data.get("therapist_id") or record.therapist_id
        therapist = Therapist.query.get(therapist_id)
        if not therapist:
            return False, "Terapist bulunamadı."
        try:
            appt_date = datetime.strptime(data.get("date"), "%Y-%m-%d").date()
            appt_time = datetime.strptime(data.get("time"), "%H:%M").time()
        except (ValueError, TypeError):
            return False, "Geçerli tarih ve saat girin."
        duration = int(data.get("duration") or record.duration_minutes or 50)
        appointment = Appointment(
            therapist_id=therapist.id,
            patient_name=record.patient_name or data.get("patient_name") or "",
            patient_email=record.patient_email or "",
            patient_phone=data.get("patient_phone") or "",
            appointment_date=appt_date,
            appointment_time=appt_time,
            session_type=data.get("session_type") or record.session_type or "yuz_yuze",
            notes=(data.get("notes") or "").strip(),
            status="beklemede",
        )
        db.session.add(appointment)
        record.next_session_date = appt_date
        record.set_workspace_dict(ws)
        db.session.flush()
        return True, {
            "appointment_id": appointment.id,
            "date": appt_date.strftime("%d.%m.%Y"),
            "time": appt_time.strftime("%H:%M"),
            "therapist": therapist.name,
        }

    if action == "sign_note":
        if not has_note_content(record, ws):
            return False, "Seans notu boşken imzalanamaz."
        note = ws.get("note") or {}
        if note.get("status") == "imzalandi":
            return False, "Not zaten imzalanmış."
        note["status"] = "imzalandi"
        note["signed_at"] = datetime.utcnow().isoformat()
        note["signed_by"] = user.username
        ws["note"] = note
        record.set_workspace_dict(ws)
        return True, {"note": note}

    if action == "complete":
        force = bool(data.get("force"))
        checklist = get_completion_checklist(record, ws, user)
        if not force and not checklist["has_note"]:
            return False, "Seans notu olmadan tamamlanamaz. Yine de devam etmek için onaylayın."
        record.status = "sonlandi"
        ws["completed_at"] = datetime.utcnow().isoformat()
        ws["completed_by"] = user.username
        timer = ws.get("timer") or {}
        if timer.get("running"):
            timer["running"] = False
            timer["finished"] = True
            ws["timer"] = timer
        record.set_workspace_dict(ws)
        return True, {"status": "sonlandi", "checklist": checklist}

    if action == "timer":
        timer = ws.get("timer") or {}
        timer.update(data or {})
        ws["timer"] = timer
        record.set_workspace_dict(ws)
        return True, {"timer": timer}

    return False, "Geçersiz işlem."


def process_homework_due_reminders(settings, days_ahead=2):
    """C2 — teslim tarihi yaklaşan ödevler için hatırlatma e-postası kuyruğu."""
    from email_service import queue_homework_due_reminder
    from models import SessionRecord, db

    today = date.today()
    horizon = today + timedelta(days=max(int(days_ahead), 0))
    queued = 0
    for record in SessionRecord.query.all():
        ws = _default_workspace(record)
        touched = False
        for item in ws.get("homework") or []:
            if item.get("reminder_sent_at"):
                continue
            due_raw = (item.get("due_date") or "").strip()[:10]
            if not due_raw:
                continue
            try:
                due = datetime.strptime(due_raw, "%Y-%m-%d").date()
            except ValueError:
                continue
            if due < today or due > horizon:
                continue
            log = queue_homework_due_reminder(settings, record, item)
            if log is None:
                continue
            item["reminder_sent_at"] = datetime.utcnow().isoformat()
            item["reminder_email_log_id"] = log.id
            touched = True
            queued += 1
        if touched:
            record.set_workspace_dict(ws)
    if queued:
        db.session.commit()
    return queued


def list_client_homework_items(email):
    """Aggregate danışana görünür ödevler (tüm seans kayıtlarından)."""
    from models import SessionRecord

    email_norm = (email or "").strip().lower()
    if not email_norm:
        return []
    records = (
        SessionRecord.query.filter(SessionRecord.patient_email.ilike(email_norm))
        .order_by(SessionRecord.created_at.desc(), SessionRecord.id.desc())
        .all()
    )
    out = []
    for record in records:
        ws = _default_workspace(record)
        session_label = record.created_at.date().isoformat() if record.created_at else ""
        for hw in ws.get("homework") or []:
            if hw.get("visible_to_client") is False:
                continue
            out.append(
                {
                    "record_id": record.id,
                    "session_date": session_label,
                    "homework": dict(hw),
                }
            )
    return out


def list_client_document_items(email):
    """Danışana görünür seans belgeleri."""
    from models import SessionRecord

    email_norm = (email or "").strip().lower()
    if not email_norm:
        return []
    records = (
        SessionRecord.query.filter(SessionRecord.patient_email.ilike(email_norm))
        .order_by(SessionRecord.created_at.desc(), SessionRecord.id.desc())
        .all()
    )
    out = []
    for record in records:
        ws = _default_workspace(record)
        session_label = record.created_at.date().isoformat() if record.created_at else ""
        for doc in ws.get("documents") or []:
            if not doc.get("visible_to_client"):
                continue
            if not doc.get("storage_path"):
                continue
            out.append(
                {
                    "record_id": record.id,
                    "session_date": session_label,
                    "document": dict(doc),
                }
            )
    return out


def client_update_homework(record, client_email, hw_id, data):
    """Danışanın kendi ödev durumunu / yanıtını güncellemesi."""
    email_norm = (client_email or "").strip().lower()
    if not email_norm or (record.patient_email or "").strip().lower() != email_norm:
        return False, "Bu ödeve erişim yetkiniz yok."
    ws = _default_workspace(record)
    data = data or {}
    for item in ws.get("homework") or []:
        if str(item.get("id")) != str(hw_id):
            continue
        if item.get("visible_to_client") is False:
            return False, "Bu ödev danışana görünür değil."
        if "status" in data:
            status = data["status"]
            if status not in ("baslandi", "tamamlandi"):
                return False, "Geçersiz durum."
            item["status"] = status
        if "client_response" in data:
            item["client_response"] = (data.get("client_response") or "").strip()[:4000]
        item["client_updated_at"] = datetime.utcnow().isoformat()
        record.set_workspace_dict(ws)
        return True, {"item": item}
    return False, "Ödev bulunamadı."


