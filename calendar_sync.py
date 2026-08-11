import secrets
from datetime import date, datetime, timedelta
from io import StringIO
from urllib.request import urlopen

from helpers import WORK_HOURS, format_time_slot


def ensure_calendar_token(therapist):
    if not therapist.calendar_token:
        therapist.calendar_token = secrets.token_urlsafe(24)
    return therapist.calendar_token


def _escape_ics(text):
    return str(text).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def generate_therapist_ics(therapist, appointments, site_name):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//PsikoHukuk//TR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape_ics(therapist.name)} - Randevular",
    ]

    for appt in appointments:
        if appt.status == "iptal":
            continue
        start = datetime.combine(appt.appointment_date, appt.appointment_time)
        end = start + timedelta(hours=1)
        uid = f"appt-{appt.id}@psikohukuk"
        summary = f"{appt.patient_name} — {AppointmentStatusLabel(appt)}"
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{_escape_ics(summary)}",
            f"DESCRIPTION:{_escape_ics(appt.notes or '')}",
            f"ORGANIZER;CN={_escape_ics(site_name)}:mailto:{therapist.email}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def AppointmentStatusLabel(appt):
    return appt.STATUS_LABELS.get(appt.status, appt.status)


def fetch_external_busy_slots(therapist, start_date, end_date):
    if not therapist.ical_import_url:
        return {}

    busy = {}
    try:
        with urlopen(therapist.ical_import_url, timeout=10) as response:
            content = response.read().decode("utf-8", errors="ignore")
    except Exception:
        return {}

    try:
        from icalendar import Calendar

        calendar = Calendar.from_ical(content)
        for component in calendar.walk():
            if component.name != "VEVENT":
                continue
            dtstart = component.get("DTSTART")
            dtend = component.get("DTEND")
            if not dtstart:
                continue
            start = dtstart.dt
            end = dtend.dt if dtend else start
            if isinstance(start, datetime):
                start_date_val = start.date()
                end_date_val = end.date() if isinstance(end, datetime) else end
            else:
                start_date_val = start
                end_date_val = end if hasattr(end, "year") else start

            current = start_date_val
            while current <= end_date_val:
                if start_date <= current <= end_date:
                    day_key = current.isoformat()
                    busy.setdefault(day_key, set()).update(WORK_HOURS)
                current += timedelta(days=1)
    except ImportError:
        busy.update(_parse_ics_basic(content, start_date, end_date))

    return busy


def _parse_ics_basic(content, start_date, end_date):
    busy = {}
    for line in content.splitlines():
        if line.startswith("DTSTART"):
            value = line.split(":", 1)[-1].strip()
            if len(value) >= 8:
                try:
                    day = date(int(value[:4]), int(value[4:6]), int(value[6:8]))
                    if start_date <= day <= end_date:
                        busy.setdefault(day.isoformat(), set()).update(WORK_HOURS)
                except ValueError:
                    continue
    return busy


def merge_blocked_sets(*sources):
    merged = {}
    for source in sources:
        for day_key, hours in source.items():
            merged.setdefault(day_key, set()).update(hours)
    return merged
