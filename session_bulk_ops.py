"""Toplu seans listesi işlemleri (e-posta, CSV, durum, terapist, silme, SMS stub)."""
from datetime import date

from session_workspace import can_edit_session


def _parse_ids(raw_ids):
    ids = []
    for raw in raw_ids or []:
        try:
            ids.append(int(raw))
        except (TypeError, ValueError):
            continue
    return ids


def perform_session_bulk(user, raw_ids, action, data, *, settings, queue_email_fn, log_audit_fn, db, models):
    """Returns (count, message, level) where level is success|warning|error."""
    from models import SessionRecord, Therapist

    ids = _parse_ids(raw_ids)
    if not ids:
        return 0, "Lütfen en az bir seans seçin.", "warning"

    action = (action or "").strip().lower()
    if not action:
        return 0, "Toplu işlem türü belirtilmedi.", "error"

    records = SessionRecord.query.filter(SessionRecord.id.in_(ids)).all()
    by_id = {r.id: r for r in records}
    ordered = [by_id[i] for i in ids if i in by_id]

    count = 0
    skipped = 0
    mail_queued = 0
    sms_logged = 0

    if action == "mail":
        for record in ordered:
            if not can_edit_session(user, record):
                skipped += 1
                continue
            log = queue_email_fn(settings, record)
            if log:
                mail_queued += 1
                log_audit_fn(
                    user,
                    "notify_queued",
                    "session_record",
                    record.id,
                    {"patient": record.patient_name, "email": record.patient_email},
                )
            count += 1
        db.session.commit()
        msg = f"{mail_queued} danışana bilgilendirme e-postası kuyruğa alındı."
        if skipped:
            msg += f" {skipped} kayıt yetki dışı atlandı."
        return count, msg, "success"

    if action == "sms":
        for record in ordered:
            if not can_edit_session(user, record):
                skipped += 1
                continue
            phone = (record.patient_phone or "").strip()
            log_audit_fn(
                user,
                "sms_stub",
                "session_record",
                record.id,
                {"patient": record.patient_name, "phone": phone or "—", "note": "SMS entegrasyonu yapılandırılmadı"},
            )
            sms_logged += 1
            count += 1
        db.session.commit()
        msg = (
            f"{sms_logged} kayıt SMS kuyruğuna işlendi (stub). "
            "Gerçek SMS gönderimi için operatör entegrasyonu gerekir."
        )
        if skipped:
            msg += f" {skipped} kayıt atlandı."
        return count, msg, "warning"

    if action == "approve":
        for record in ordered:
            if not can_edit_session(user, record):
                skipped += 1
                continue
            if record.status in ("iptal", "sonlandi", "tamamlandi"):
                continue
            old = record.status
            record.status = "devam"
            log_audit_fn(
                user,
                "bulk_status",
                "session_record",
                record.id,
                {"from": old, "to": "devam", "patient": record.patient_name},
            )
            count += 1
        db.session.commit()
        msg = f"{count} seans «devam ediyor» olarak güncellendi."
        if skipped:
            msg += f" {skipped} kayıt atlandı."
        return count, msg, "success"

    if action == "therapist":
        try:
            new_tid = int((data or {}).get("new_therapist_id") or 0)
        except (TypeError, ValueError):
            new_tid = 0
        therapist = Therapist.query.get(new_tid) if new_tid else None
        if not therapist:
            return 0, "Geçerli bir terapist seçin.", "error"
        for record in ordered:
            if user.role == "therapist":
                skipped += 1
                continue
            if not can_edit_session(user, record):
                skipped += 1
                continue
            old_tid = record.therapist_id
            record.therapist_id = therapist.id
            log_audit_fn(
                user,
                "bulk_therapist",
                "session_record",
                record.id,
                {"from": old_tid, "to": therapist.id, "patient": record.patient_name},
            )
            count += 1
        db.session.commit()
        msg = f"{count} seans {therapist.name} terapistine atandı."
        if skipped:
            msg += f" {skipped} kayıt atlandı."
        return count, msg, "success"

    if action == "delete":
        if user.role != "admin":
            return 0, "Seans silme yalnızca klinik yöneticisi tarafından yapılabilir.", "error"
        for record in ordered:
            log_audit_fn(
                user,
                "delete",
                "session_record",
                record.id,
                {"patient": record.patient_name, "email": record.patient_email},
            )
            db.session.delete(record)
            count += 1
        db.session.commit()
        return count, f"{count} seans kaydı silindi.", "success"

    return 0, f"Geçersiz işlem: {action}", "error"


def sessions_for_export(user, scope_query, ids_param=None):
    """Resolve session rows for CSV export (optional id list, scope-safe)."""
    from models import SessionRecord

    if ids_param:
        id_list = []
        for part in str(ids_param).split(","):
            part = part.strip()
            if part.isdigit():
                id_list.append(int(part))
        if not id_list:
            return []
        rows = SessionRecord.query.filter(SessionRecord.id.in_(id_list)).all()
        by_id = {r.id: r for r in rows}
        ordered = [by_id[i] for i in id_list if i in by_id]
        return [r for r in ordered if can_edit_session(user, r)]

    return scope_query.order_by(SessionRecord.created_at.desc()).all()
