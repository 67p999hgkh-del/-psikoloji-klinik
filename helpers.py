import calendar
import json
import re
from datetime import date, datetime, time, timedelta

from sqlalchemy import inspect, text

from models import Appointment, Therapist, db

SITE_NAME = "PsikoHukuk Danışmanlık Merkezi"
SITE_TAGLINE = "Psikolojik Danışmanlık"
SITE_DESCRIPTION = (
    "PsikoHukuk Danışmanlık Merkezi — psikoloji alanında "
    "uzman kadro, online randevu ve profesyonel danışmanlık hizmetleri."
)
SITE_KEYWORDS = (
    "#psikoloji #danışmanlık #terapi #psikolog "
    "#randevu #istanbul #psikolojikdestek #ruhsagligi"
)

WORK_HOURS = ["09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"]
BLOCKING_STATUSES = ("onaylandi", "beklemede")
WEEKEND_DAYS = (5, 6)


def parse_time_slot(value):
    return datetime.strptime(value, "%H:%M").time()


def format_time_slot(value):
    if isinstance(value, time):
        return value.strftime("%H:%M")
    return value


def is_slot_blocked(therapist_id, appt_date, appt_time):
    return (
        Appointment.query.filter_by(
            therapist_id=therapist_id,
            appointment_date=appt_date,
            appointment_time=appt_time,
        )
        .filter(Appointment.status.in_(BLOCKING_STATUSES))
        .first()
        is not None
    )


def get_external_blocked(therapist, first_day, last_day):
    from calendar_sync import fetch_external_busy_slots

    if not therapist.ical_import_url:
        return {}
    return fetch_external_busy_slots(therapist, first_day, last_day)


def get_month_availability(therapist_id, year, month):
    therapist = Therapist.query.get(therapist_id)
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    today = date.today()

    appointments = (
        Appointment.query.filter_by(therapist_id=therapist_id)
        .filter(Appointment.appointment_date >= first_day)
        .filter(Appointment.appointment_date <= last_day)
        .filter(Appointment.status.in_(BLOCKING_STATUSES))
        .all()
    )

    blocked = {}
    for appt in appointments:
        day_key = appt.appointment_date.isoformat()
        blocked.setdefault(day_key, set()).add(format_time_slot(appt.appointment_time))

    if therapist:
        external = get_external_blocked(therapist, first_day, last_day)
        for day_key, hours in external.items():
            blocked.setdefault(day_key, set()).update(hours)

    days = {}
    current = first_day
    while current <= last_day:
        day_key = current.isoformat()
        is_past = current < today
        is_weekend = current.weekday() in WEEKEND_DAYS

        if is_past or is_weekend:
            days[day_key] = {
                "status": "closed",
                "slots": {hour: "closed" for hour in WORK_HOURS},
                "available_count": 0,
            }
        else:
            day_blocked = blocked.get(day_key, set())
            slots = {}
            available_count = 0
            for hour in WORK_HOURS:
                if hour in day_blocked:
                    slots[hour] = "busy"
                else:
                    slots[hour] = "available"
                    available_count += 1

            if available_count == 0:
                day_status = "full"
            elif available_count == len(WORK_HOURS):
                day_status = "available"
            else:
                day_status = "partial"

            days[day_key] = {
                "status": day_status,
                "slots": slots,
                "available_count": available_count,
            }

        current += timedelta(days=1)

    return {
        "therapist_id": therapist_id,
        "year": year,
        "month": month,
        "work_hours": WORK_HOURS,
        "days": days,
    }


def parse_tags(raw_tags):
    if not raw_tags:
        return []
    tags = re.findall(r"#?[\w\u0080-\uFFFF]+", raw_tags)
    cleaned = []
    for tag in tags:
        tag = tag if tag.startswith("#") else f"#{tag}"
        if tag.lower() not in {t.lower() for t in cleaned}:
            cleaned.append(tag)
    return cleaned


def tags_to_slug(tag):
    return tag.lstrip("#").lower().replace(" ", "-")


def _add_column_if_missing(table, column, definition):
    inspector = inspect(db.engine)
    if not inspector.has_table(table):
        return
    columns = {col["name"] for col in inspector.get_columns(table)}
    if column not in columns:
        db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))


def _migrate_admin_to_user():
    inspector = inspect(db.engine)
    has_admin = inspector.has_table("admin")
    has_user = inspector.has_table("user")

    if has_admin and not has_user:
        db.session.execute(
            text(
                """
                CREATE TABLE user (
                    id INTEGER PRIMARY KEY,
                    username VARCHAR(80) NOT NULL UNIQUE,
                    password_hash VARCHAR(256) NOT NULL,
                    role VARCHAR(20) NOT NULL DEFAULT 'admin',
                    therapist_id INTEGER REFERENCES therapist(id),
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME
                )
                """
            )
        )
        db.session.execute(
            text(
                """
                INSERT INTO user (id, username, password_hash, role, is_active, created_at)
                SELECT id, username, password_hash, 'admin', 1, created_at FROM admin
                """
            )
        )
        return

    if has_user:
        _add_column_if_missing("user", "role", "VARCHAR(20) NOT NULL DEFAULT 'admin'")
        _add_column_if_missing("user", "therapist_id", "INTEGER")
        _add_column_if_missing("user", "is_active", "BOOLEAN DEFAULT 1")

    if has_admin and has_user:
        user_count = db.session.execute(text("SELECT COUNT(*) FROM user")).scalar()
        admin_count = db.session.execute(text("SELECT COUNT(*) FROM admin")).scalar()
        if user_count == 0 and admin_count > 0:
            db.session.execute(
                text(
                    """
                    INSERT INTO user (id, username, password_hash, role, is_active, created_at)
                    SELECT id, username, password_hash, 'admin', 1, created_at FROM admin
                    """
                )
            )


def migrate_schema():
    db.create_all()
    _add_column_if_missing("blog_post", "category", "VARCHAR(100) DEFAULT 'Genel'")
    _add_column_if_missing("blog_post", "tags", "VARCHAR(500) DEFAULT ''")
    _add_column_if_missing("blog_post", "seo_title", "VARCHAR(200) DEFAULT ''")
    _add_column_if_missing("blog_post", "seo_description", "TEXT DEFAULT ''")
    _add_column_if_missing("blog_post", "featured_image", "VARCHAR(300) DEFAULT ''")
    _add_column_if_missing("therapist", "calendar_token", "VARCHAR(64)")
    _add_column_if_missing("therapist", "ical_import_url", "VARCHAR(500) DEFAULT ''")
    _add_column_if_missing("psychological_test", "seo_title", "VARCHAR(200) DEFAULT ''")
    _add_column_if_missing("psychological_test", "seo_description", "TEXT DEFAULT ''")
    _add_column_if_missing("psychological_test", "seo_keywords", "VARCHAR(500) DEFAULT ''")
    _add_column_if_missing("psychological_test", "hero_title", "VARCHAR(200) DEFAULT ''")
    _add_column_if_missing("psychological_test", "hero_subtitle", "TEXT DEFAULT ''")
    _add_column_if_missing("psychological_test", "duration_minutes", "INTEGER DEFAULT 5")
    _add_column_if_missing("psychological_test", "accent_color", "VARCHAR(20) DEFAULT '#2d6a6a'")
    _add_column_if_missing("psychological_test", "benefits", "TEXT DEFAULT ''")
    _add_column_if_missing("psychological_test", "match_tags", "VARCHAR(300) DEFAULT ''")
    _add_column_if_missing("therapist", "city", "VARCHAR(80) DEFAULT 'İstanbul'")
    _add_column_if_missing("therapist", "languages_spoken", "VARCHAR(120) DEFAULT 'tr'")
    _add_column_if_missing("therapist", "supports_online", "BOOLEAN DEFAULT 1")
    _add_column_if_missing("blog_post", "seo_keywords", "VARCHAR(500) DEFAULT ''")
    _add_column_if_missing("psychological_test", "test_group", "VARCHAR(50) DEFAULT 'mood'")
    _add_column_if_missing("psychological_test", "available_langs", "VARCHAR(50) DEFAULT 'tr,en,de'")
    _add_column_if_missing("session_record", "session_type", "VARCHAR(20) DEFAULT 'yuz_yuze'")
    _add_column_if_missing("session_record", "status", "VARCHAR(20) DEFAULT 'devam'")
    _add_column_if_missing("session_record", "risk_level", "VARCHAR(20) DEFAULT 'dusuk'")
    _add_column_if_missing("session_record", "duration_minutes", "INTEGER DEFAULT 50")
    _add_column_if_missing("session_record", "next_session_date", "DATE")
    _add_column_if_missing("therapist", "profile_data", "TEXT DEFAULT '{}'")
    _add_column_if_missing("session_record", "workspace_data", "TEXT DEFAULT '{}'")
    _add_column_if_missing("blog_post", "updated_at", "DATETIME")
    _add_column_if_missing("blog_post", "cms_data", "TEXT DEFAULT '{}'")
    _add_column_if_missing("slider", "updated_at", "DATETIME")
    _add_column_if_missing("slider", "cms_data", "TEXT DEFAULT '{}'")
    _add_column_if_missing("widget", "updated_at", "DATETIME")
    _add_column_if_missing("widget", "cms_data", "TEXT DEFAULT '{}'")
    _add_column_if_missing("psychological_test", "updated_at", "DATETIME")
    _add_column_if_missing("psychological_test", "cms_data", "TEXT DEFAULT '{}'")
    _add_column_if_missing("site_settings", "theme_data", "TEXT DEFAULT '{}'")
    _add_column_if_missing("site_settings", "email_data", "TEXT DEFAULT '{}'")
    _add_column_if_missing("site_settings", "subscription_plan", "VARCHAR(30) DEFAULT 'enterprise'")
    _add_column_if_missing("user", "account_data", "TEXT DEFAULT '{}'")
    _add_column_if_missing("client_profile", "invite_sent_at", "DATETIME")
    _add_column_if_missing("client_profile", "gender", "VARCHAR(20) DEFAULT ''")
    _add_column_if_missing("client_profile", "birth_date", "DATE")
    _migrate_admin_to_user()
    db.session.commit()
