"""Week/day slot schedule helpers for admin Randevular."""
from collections import defaultdict
from datetime import date, datetime, timedelta

SCHEDULE_HOURS = tuple(range(8, 21))  # 08:00–20:00
WEEKDAY_SHORT = ("Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz")
TR_MONTHS = (
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


def parse_schedule_date(raw, fallback=None):
    fallback = fallback or date.today()
    if not raw:
        return fallback
    try:
        return datetime.strptime(str(raw).strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return fallback


def week_monday(d):
    return d - timedelta(days=d.weekday())


def _schedule_appointment_card(appt):
    t = appt.appointment_time
    return {
        "id": appt.id,
        "patient_name": appt.patient_name or "—",
        "therapist_name": appt.therapist.name if appt.therapist else "—",
        "time": t.strftime("%H:%M") if t else "—",
        "hour": t.hour if t else None,
        "status": appt.status,
        "session_type": appt.session_type,
        "duration_minutes": getattr(appt, "duration_minutes", None) or 50,
    }


def build_week_schedule(appointments, week_start, today=None):
    today = today or date.today()
    week_end = week_start + timedelta(days=6)
    by_day = defaultdict(list)
    for appt in appointments:
        if not appt.appointment_date:
            continue
        if appt.appointment_date < week_start or appt.appointment_date > week_end:
            continue
        if appt.status == "iptal":
            continue
        by_day[appt.appointment_date].append(_schedule_appointment_card(appt))

    days = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        cards = sorted(by_day.get(d, []), key=lambda c: c["time"])
        days.append(
            {
                "date": d,
                "iso": d.isoformat(),
                "label": WEEKDAY_SHORT[i],
                "is_today": d == today,
                "count": len(cards),
                "appointments": cards,
            }
        )

    hours = []
    for h in SCHEDULE_HOURS:
        cells = []
        for day in days:
            hour_cards = [c for c in day["appointments"] if c["hour"] == h]
            cells.append(
                {
                    "date": day["date"],
                    "iso": day["iso"],
                    "appointments": hour_cards,
                    "create_time": f"{h:02d}:00",
                    "is_today": day["is_today"],
                }
            )
        hours.append({"hour": h, "label": f"{h:02d}:00", "cells": cells})

    return {
        "week_start": week_start,
        "week_end": week_end,
        "prev_start": week_start - timedelta(days=7),
        "next_start": week_start + timedelta(days=7),
        "days": days,
        "hours": hours,
        "total": sum(d["count"] for d in days),
        "title": (
            f"{week_start.day:02d}.{week_start.month:02d} – "
            f"{week_end.day:02d}.{week_end.month:02d}.{week_end.year}"
        ),
    }


def build_day_schedule(appointments, focus_day, today=None):
    today = today or date.today()
    cards = []
    for appt in appointments:
        if appt.appointment_date != focus_day or appt.status == "iptal":
            continue
        cards.append(_schedule_appointment_card(appt))
    cards.sort(key=lambda c: c["time"])

    slots = []
    for h in SCHEDULE_HOURS:
        hour_cards = [c for c in cards if c["hour"] == h]
        slots.append(
            {
                "hour": h,
                "label": f"{h:02d}:00",
                "appointments": hour_cards,
                "create_time": f"{h:02d}:00",
            }
        )

    return {
        "date": focus_day,
        "iso": focus_day.isoformat(),
        "is_today": focus_day == today,
        "prev": focus_day - timedelta(days=1),
        "next": focus_day + timedelta(days=1),
        "slots": slots,
        "appointments": cards,
        "count": len(cards),
        "title": f"{focus_day.day:02d} {TR_MONTHS[focus_day.month]} {focus_day.year}",
        "weekday": WEEKDAY_SHORT[focus_day.weekday()],
    }


def schedule_nav_args(
    *,
    view,
    cal=None,
    day=None,
    status="",
    q="",
    date_from="",
    date_to="",
    therapist_id=None,
    is_therapist_view=False,
):
    args = {"view": view}
    if status:
        args["status"] = status
    if q:
        args["q"] = q
    if date_from:
        args["from"] = date_from
    if date_to:
        args["to"] = date_to
    if therapist_id and not is_therapist_view:
        args["therapist_id"] = therapist_id
    if cal is not None:
        args["cal"] = cal.isoformat() if hasattr(cal, "isoformat") else str(cal)
    if day is not None:
        args["day"] = day.isoformat() if hasattr(day, "isoformat") else str(day)
    return args


def appointment_create_href(appt_date, appt_time):
    """Path to Yeni Randevu with date/time prefill (works once create route exists)."""
    iso = appt_date.isoformat() if hasattr(appt_date, "isoformat") else str(appt_date)
    return f"/admin/randevu/yeni?appointment_date={iso}&appointment_time={appt_time}"
