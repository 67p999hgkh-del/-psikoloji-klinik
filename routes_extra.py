"""Extra admin/client routes for PsikoPlan features."""
import csv
import io
import json
import secrets
from datetime import date, datetime, timedelta

from flask import (
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from auth import (
    client_login_required,
    get_current_user,
    login_user,
    logout_user,
    permission_required,
)
from models import (
    Appointment,
    AuditLog,
    ClientProfile,
    Invoice,
    SessionRecord,
    TestResult,
    Therapist,
    TherapistNote,
    User,
    db,
)
from psikoplan import (
    APPLICATION_REASONS,
    PAYMENT_LABELS,
    build_analiz_payload,
    build_session_ai_summary,
    ensure_client_invite,
    log_audit,
    payment_status_map,
    sync_client_links,
)
from session_bulk_ops import perform_session_bulk
from session_workspace import (
    NOTE_TEMPLATES,
    SESSION_HOMEWORK_FILTERS,
    SESSION_LIST_STATUS_FILTERS,
    THERAPY_APPROACHES,
    WORKSPACE_STATUS_LABELS,
    apply_session_filters,
    build_active_filter_chips,
    build_session_kpis,
    build_session_rows,
    build_workspace_payload,
    count_advanced_filters,
    detect_date_preset,
    filter_rows_by_extra,
    filter_sessions_by_kpi,
    refine_session_list,
)


def active_client_profiles():
    return (
        ClientProfile.query.join(User, ClientProfile.user_id == User.id)
        .filter(User.role == "client", User.is_active.is_(True))
        .order_by(ClientProfile.full_name)
        .all()
    )


def _parse_date_arg(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _session_scope(user):
    scope = SessionRecord.query
    if user.role == "therapist" and user.therapist_id:
        scope = scope.filter_by(therapist_id=user.therapist_id)
    return scope


def _apply_session_filters(scope, args):
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

    therapist_id = args.get("therapist_id", type=int)
    if therapist_id:
        scope = scope.filter_by(therapist_id=therapist_id)

    city = (args.get("city") or "").strip()
    if city:
        scope = scope.filter(SessionRecord.city == city)

    reason = (args.get("reason") or "").strip()
    if reason:
        scope = scope.filter(SessionRecord.reasons.ilike(f"%{reason}%"))

    status = (args.get("status") or "").strip()
    if status:
        scope = scope.filter(SessionRecord.status == status)

    session_type = (args.get("session_type") or "").strip()
    if session_type:
        scope = scope.filter(SessionRecord.session_type == session_type)

    date_from = _parse_date_arg(args.get("from"))
    date_to = _parse_date_arg(args.get("to"))
    if date_from:
        scope = scope.filter(SessionRecord.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        scope = scope.filter(SessionRecord.created_at <= datetime.combine(date_to, datetime.max.time()))

    return scope


def register_extra_routes(app):
    @app.route("/admin/loglar")
    @permission_required("audit")
    def admin_audit_logs():
        logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
        return render_template("admin/audit_logs.html", logs=logs)

    @app.route("/admin/analiz")
    @permission_required("analiz")
    def admin_analiz():
        user = get_current_user()
        year = request.args.get("year", type=int)
        month = request.args.get("month", type=int)
        therapist_id = user.therapist_id if user.role == "therapist" else None
        data = build_analiz_payload(year=year, month=month, therapist_id=therapist_id)
        return render_template(
            "admin/analiz.html",
            data=data,
            application_reasons=APPLICATION_REASONS,
            user=user,
        )

    @app.route("/admin/analiz/baglanti-onar", methods=["POST"])
    @permission_required("analiz")
    def admin_analiz_sync():
        user = get_current_user()
        result = sync_client_links()
        log_audit(user, "sync", "client_links", detail=result)
        db.session.commit()
        flash(
            f"{result['memberships_created']} üyelik oluşturuldu, "
            f"{result['records_linked']} kayıt üyeliklere bağlandı.",
            "success",
        )
        return redirect(url_for("admin_analiz", **request.args.to_dict()))

    @app.route("/admin/seanslar")
    @permission_required("sessions")
    def admin_sessions():
        user = get_current_user()
        base_scope = _session_scope(user)
        scope, filters = apply_session_filters(base_scope, request.args)

        all_filtered = scope.order_by(SessionRecord.created_at.desc()).all()
        all_base = base_scope.all()
        payments = payment_status_map({s.patient_email for s in all_filtered})

        today = date.today()
        kpis = build_session_kpis(all_filtered, all_base, today)

        list_sessions = all_filtered
        if filters.get("kpi"):
            list_sessions = filter_sessions_by_kpi(all_filtered, filters["kpi"], today)
        list_sessions = refine_session_list(list_sessions, filters, today)

        rows = build_session_rows(list_sessions, all_base, payments)
        rows = filter_rows_by_extra(rows, filters)

        page = max(request.args.get("page", 1, type=int), 1)
        per_page = 20
        total = len(rows)
        pages = max((total + per_page - 1) // per_page, 1)
        page = min(page, pages)
        paginated_rows = rows[(page - 1) * per_page : page * per_page]

        filter_chips = build_active_filter_chips(filters, WORKSPACE_STATUS_LABELS, PAYMENT_LABELS)
        query_args = {k: v for k, v in filters.items() if v}
        filter_chip_links = [
            {
                **chip,
                "href_args": {k: v for k, v in query_args.items() if k != chip.get("key")},
            }
            for chip in filter_chips
        ]
        therapists = Therapist.query.order_by(Therapist.name).all()
        cities = sorted(
            {t.city for t in therapists if t.city}
            | {s.city for s in all_base if s.city}
        )
        has_advanced = bool(
            filters.get("reason")
            or filters.get("visit_type")
            or filters.get("note_status")
            or filters.get("payment")
            or filters.get("session_type")
            or filters.get("city")
            or filters.get("approach")
            or (filters.get("therapist_id") and user.role != "therapist")
        )
        date_preset = detect_date_preset(filters.get("from"), filters.get("to"), today)
        advanced_filter_count = count_advanced_filters(filters, user.role == "therapist")

        return render_template(
            "admin/sessions.html",
            rows=paginated_rows,
            kpis=kpis,
            filter_chips=filter_chips,
            filter_chip_links=filter_chip_links,
            payments=payments,
            payment_labels=PAYMENT_LABELS,
            therapists=therapists,
            cities=cities,
            reasons=APPLICATION_REASONS,
            approaches=THERAPY_APPROACHES,
            status_labels=SessionRecord.STATUS_LABELS,
            workspace_status_labels=WORKSPACE_STATUS_LABELS,
            list_status_filters=SESSION_LIST_STATUS_FILTERS,
            homework_filters=SESSION_HOMEWORK_FILTERS,
            risk_labels=SessionRecord.RISK_LABELS,
            type_labels=SessionRecord.SESSION_LABELS,
            note_templates=NOTE_TEMPLATES,
            filters=filters,
            query_args=query_args,
            has_advanced=has_advanced,
            advanced_filter_count=advanced_filter_count,
            date_preset=date_preset,
            total=total,
            page=page,
            pages=pages,
            is_therapist_view=user.role == "therapist",
            user_role=user.role,
            open_session=request.args.get("open", type=int),
        )

    @app.route("/admin/seanslar/bulk", methods=["POST"])
    @permission_required("sessions")
    def admin_sessions_bulk():
        from email_service import queue_session_bulk_notify
        from app import get_site_settings

        user = get_current_user()
        settings = get_site_settings()
        ids = request.form.getlist("ids")
        action = (request.form.get("action") or "").strip()
        data = {"new_therapist_id": request.form.get("new_therapist_id")}

        _count, message, level = perform_session_bulk(
            user,
            ids,
            action,
            data,
            settings=settings,
            queue_email_fn=queue_session_bulk_notify,
            log_audit_fn=log_audit,
            db=db,
            models=None,
        )
        flash(message, level if level in ("success", "warning", "error") else "info")
        return redirect(url_for("admin_sessions"))

    @app.route("/admin/seans/<int:record_id>/workspace")
    @permission_required("sessions")
    def admin_session_workspace(record_id):
        user = get_current_user()
        record = SessionRecord.query.get_or_404(record_id)
        if user.role == "therapist" and user.therapist_id != record.therapist_id:
            return jsonify({"error": "Bu kayda erişim yetkiniz yok."}), 403
        return jsonify(build_workspace_payload(record, user))

    @app.route("/admin/seanslar/disa-aktar")
    @permission_required("sessions")
    def admin_sessions_export():
        user = get_current_user()
        scope = _apply_session_filters(_session_scope(user), request.args)
        rows = scope.order_by(SessionRecord.created_at.desc()).all()
        payments = payment_status_map({s.patient_email for s in rows})

        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=";")
        writer.writerow(
            [
                "Tarih",
                "Danışan",
                "E-posta",
                "Terapist",
                "Şube",
                "Başvuru Nedeni",
                "Tür",
                "Risk",
                "Durum",
                "Süre (dk)",
                "Sonraki Seans",
                "Ödeme",
                "Not",
            ]
        )
        for s in rows:
            writer.writerow(
                [
                    s.created_at.strftime("%d.%m.%Y %H:%M") if s.created_at else "",
                    s.patient_name or "",
                    s.patient_email or "",
                    s.therapist.name if s.therapist else "",
                    s.city or "",
                    ", ".join(s.reason_list()),
                    s.session_type_label,
                    s.risk_label,
                    s.status_label,
                    s.duration_minutes or "",
                    s.next_session_date.strftime("%d.%m.%Y") if s.next_session_date else "",
                    PAYMENT_LABELS.get(payments.get((s.patient_email or "").lower(), "yok"), ""),
                    (s.note or "").replace("\n", " "),
                ]
            )

        log_audit(user, "export", "session_record", detail={"count": len(rows)})
        db.session.commit()

        filename = f"seans-kayitlari-{date.today().isoformat()}.csv"
        return Response(
            "\ufeff" + buffer.getvalue(),
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    @app.route("/admin/seans/<int:record_id>/detay")
    @permission_required("sessions")
    def admin_session_detail(record_id):
        user = get_current_user()
        record = SessionRecord.query.get_or_404(record_id)
        if user.role == "therapist" and user.therapist_id != record.therapist_id:
            return jsonify({"error": "Bu kayda erişim yetkiniz yok."}), 403

        email = (record.patient_email or "").lower()
        profile = ClientProfile.query.filter(ClientProfile.email.ilike(email)).first() if email else None

        history = (
            SessionRecord.query.filter(SessionRecord.patient_email.ilike(email))
            .order_by(SessionRecord.created_at.desc())
            .limit(10)
            .all()
            if email
            else []
        )
        tests = (
            TestResult.query.filter(TestResult.patient_email.ilike(email))
            .order_by(TestResult.created_at.desc())
            .limit(8)
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

        summary = build_session_ai_summary(record)

        return jsonify(
            {
                "id": record.id,
                "client": {
                    "name": record.patient_name or (profile.full_name if profile else email),
                    "email": record.patient_email,
                    "phone": profile.phone if profile else "",
                    "membership": bool(profile),
                    "membership_status": (
                        "Şifre belirlendi"
                        if profile and profile.invite_accepted
                        else ("Şifre bekliyor" if profile else "Üyelik yok")
                    ),
                    "city": record.city,
                    "therapist": record.therapist.name if record.therapist else "—",
                },
                "session": {
                    "date": record.created_at.strftime("%d.%m.%Y %H:%M") if record.created_at else "",
                    "reasons": record.reason_list(),
                    "status": record.status_label,
                    "status_key": record.status,
                    "risk": record.risk_label,
                    "risk_key": record.risk_level,
                    "type": record.session_type_label,
                    "duration": record.duration_minutes,
                    "note": record.note or "",
                    "next_session": (
                        record.next_session_date.strftime("%d.%m.%Y")
                        if record.next_session_date
                        else ""
                    ),
                },
                "history": [
                    {
                        "date": h.created_at.strftime("%d.%m.%Y") if h.created_at else "",
                        "therapist": h.therapist.name if h.therapist else "—",
                        "reasons": h.reason_list(),
                        "status": h.status_label,
                        "risk": h.risk_label,
                        "current": h.id == record.id,
                    }
                    for h in history
                ],
                "tests": [
                    {
                        "title": t.test.title if t.test else "Test",
                        "date": t.created_at.strftime("%d.%m.%Y") if t.created_at else "",
                        "score": round(t.score or 0, 1),
                        "level": t.level or "—",
                    }
                    for t in tests
                ],
                "notes": [
                    {
                        "date": n.created_at.strftime("%d.%m.%Y") if n.created_at else "",
                        "body": n.body,
                        "visible": bool(n.visible_to_client),
                        "therapist": n.therapist.name if n.therapist else "—",
                    }
                    for n in notes
                ],
                "files": [],
                "payments": [
                    {
                        "date": i.invoice_date.strftime("%d.%m.%Y") if i.invoice_date else "",
                        "amount": f"{i.amount:,.0f} ₺".replace(",", "."),
                        "status": Invoice.STATUS_LABELS.get(i.status, i.status),
                        "status_key": i.status,
                        "description": i.description or "",
                    }
                    for i in invoices
                ],
                "next_appointment": (
                    {
                        "date": next_appointment.appointment_date.strftime("%d.%m.%Y"),
                        "time": next_appointment.appointment_time.strftime("%H:%M"),
                        "therapist": next_appointment.therapist.name
                        if next_appointment.therapist
                        else "—",
                        "type": Appointment.SESSION_LABELS.get(
                            next_appointment.session_type, next_appointment.session_type
                        ),
                        "status": Appointment.STATUS_LABELS.get(
                            next_appointment.status, next_appointment.status
                        ),
                    }
                    if next_appointment
                    else None
                ),
                "ai_summary": summary,
            }
        )

    @app.route("/admin/seans/yeni", methods=["GET", "POST"])
    @permission_required("sessions")
    def admin_session_new():
        user = get_current_user()
        appointment_id = request.args.get("appointment_id", type=int) or request.form.get(
            "appointment_id", type=int
        )
        appointment = Appointment.query.get(appointment_id) if appointment_id else None

        therapists = Therapist.query.filter_by(is_active=True).order_by(Therapist.name).all()
        if user.role == "therapist" and user.therapist_id:
            therapists = [t for t in therapists if t.id == user.therapist_id]
        clients = active_client_profiles()

        def form_view(selected_reasons=None):
            return render_template(
                "admin/session_form.html",
                therapists=therapists,
                clients=clients,
                appointment=appointment,
                reasons=APPLICATION_REASONS,
                selected_reasons=selected_reasons or [],
                status_labels=SessionRecord.STATUS_LABELS,
                risk_labels=SessionRecord.RISK_LABELS,
                type_labels=SessionRecord.SESSION_LABELS,
            )

        if request.method == "POST":
            therapist_id = request.form.get("therapist_id", type=int)
            if user.role == "therapist":
                therapist_id = user.therapist_id
            therapist = Therapist.query.get_or_404(therapist_id)
            reasons = request.form.getlist("reasons")
            if not reasons:
                flash("En az bir başvuru nedeni seçin.", "error")
                return form_view()

            profile_id = request.form.get("client_profile_id", type=int)
            patient_name = (request.form.get("patient_name") or "").strip()
            patient_email = (request.form.get("patient_email") or "").strip().lower()
            profile = None

            if profile_id:
                profile = ClientProfile.query.get_or_404(profile_id)
                patient_name = profile.full_name
                patient_email = profile.email
            elif patient_email:
                profile, created = ensure_client_invite(patient_name, patient_email)
                if created:
                    flash(
                        f"{patient_email} için üyelik oluşturuldu. Danışan ilk girişinde şifresini belirleyecek.",
                        "info",
                    )
                    log_audit(user, "create", "client_profile", detail={"email": patient_email})
                elif profile:
                    patient_name = profile.full_name
            else:
                flash("Kayıtlı bir üye seçin veya yeni danışanın e-postasını girin.", "error")
                return form_view(reasons)

            db.session.flush()
            session_type = request.form.get("session_type") or (
                appointment.session_type if appointment else "yuz_yuze"
            )
            record = SessionRecord(
                appointment_id=appointment.id if appointment else None,
                therapist_id=therapist.id,
                client_user_id=profile.user_id if profile else None,
                patient_name=patient_name,
                patient_email=patient_email,
                city=therapist.city or "",
                reasons=json.dumps(reasons, ensure_ascii=False),
                note=request.form.get("note", "").strip(),
                session_type=session_type
                if session_type in SessionRecord.SESSION_LABELS
                else "yuz_yuze",
                status=request.form.get("status")
                if request.form.get("status") in SessionRecord.STATUS_LABELS
                else "devam",
                risk_level=request.form.get("risk_level")
                if request.form.get("risk_level") in SessionRecord.RISK_LABELS
                else "dusuk",
                duration_minutes=request.form.get("duration_minutes", type=int) or 50,
                next_session_date=_parse_date_arg(request.form.get("next_session_date")),
            )
            db.session.add(record)
            log_audit(user, "create", "session_record", detail={"reasons": reasons, "patient": patient_email})
            db.session.commit()
            flash("Seans kaydı oluşturuldu.", "success")
            return redirect(url_for("admin_sessions"))

        return form_view()

    @app.route("/admin/faturalar")
    @permission_required("invoices")
    def admin_invoices():
        user = get_current_user()
        query = Invoice.query.order_by(Invoice.invoice_date.desc())
        if user.role == "therapist" and user.therapist_id:
            query = query.filter_by(therapist_id=user.therapist_id)
        invoices = query.limit(100).all()
        return render_template("admin/invoices.html", invoices=invoices)

    @app.route("/admin/fatura/yeni", methods=["GET", "POST"])
    @permission_required("invoices")
    def admin_invoice_new():
        user = get_current_user()
        therapists = Therapist.query.filter_by(is_active=True).order_by(Therapist.name).all()
        if request.method == "POST":
            email = (request.form.get("patient_email") or "").strip().lower()
            profile = ClientProfile.query.filter_by(email=email).first() if email else None
            therapist_id = request.form.get("therapist_id", type=int)
            if user.role == "therapist":
                therapist_id = user.therapist_id
            try:
                amount = float(request.form.get("amount") or 0)
            except ValueError:
                amount = 0
            invoice_date_raw = request.form.get("invoice_date") or date.today().isoformat()
            try:
                invoice_date = datetime.strptime(invoice_date_raw, "%Y-%m-%d").date()
            except ValueError:
                invoice_date = date.today()

            invoice = Invoice(
                client_user_id=profile.user_id if profile else None,
                patient_email=email,
                patient_name=request.form.get("patient_name", "").strip(),
                therapist_id=therapist_id,
                amount=amount,
                currency=request.form.get("currency", "TRY"),
                description=request.form.get("description", "").strip(),
                invoice_date=invoice_date,
                status=request.form.get("status", "bekliyor"),
            )
            db.session.add(invoice)
            log_audit(user, "create", "invoice", detail={"email": email, "amount": amount})
            db.session.commit()
            flash("Fatura kaydı eklendi.", "success")
            return redirect(url_for("admin_invoices"))

        return render_template("admin/invoice_form.html", therapists=therapists, today=date.today())

    @app.route("/admin/not/yeni", methods=["GET", "POST"])
    @permission_required("sessions")
    def admin_note_new():
        user = get_current_user()
        therapists = Therapist.query.filter_by(is_active=True).order_by(Therapist.name).all()
        if request.method == "POST":
            email = (request.form.get("patient_email") or "").strip().lower()
            profile = ClientProfile.query.filter_by(email=email).first() if email else None
            therapist_id = request.form.get("therapist_id", type=int)
            if user.role == "therapist":
                therapist_id = user.therapist_id
            note = TherapistNote(
                therapist_id=therapist_id,
                client_user_id=profile.user_id if profile else None,
                patient_email=email,
                body=request.form.get("body", "").strip(),
                visible_to_client="visible_to_client" in request.form,
            )
            if not note.body:
                flash("Not boş olamaz.", "error")
                return render_template("admin/note_form.html", therapists=therapists)
            db.session.add(note)
            log_audit(user, "create", "therapist_note", detail={"email": email})
            db.session.commit()
            flash("Terapist notu kaydedildi.", "success")
            return redirect(url_for("admin_sessions"))
        return render_template("admin/note_form.html", therapists=therapists)

    @app.route("/uye/giris", methods=["GET", "POST"])
    def client_login():
        current = get_current_user()
        if current and current.role == "client":
            return redirect(url_for("client_portal"))

        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(username=email, role="client", is_active=True).first()
            profile = user.client_profile if user else None

            if profile and not profile.invite_accepted:
                if not profile.invite_token:
                    profile.invite_token = secrets.token_urlsafe(24)
                    db.session.commit()
                flash("İlk girişiniz: lütfen şifrenizi belirleyin.", "info")
                return redirect(url_for("client_set_password", token=profile.invite_token))

            if not password:
                flash("Şifrenizi girin.", "error")
            elif user and check_password_hash(user.password_hash, password):
                login_user(user)
                flash("Hoş geldiniz!", "success")
                return redirect(url_for("client_portal"))
            else:
                flash("E-posta veya şifre hatalı.", "error")

        return render_template("client/login.html")

    @app.route("/uye/kayit", methods=["GET", "POST"])
    def client_register():
        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip().lower()
            phone = request.form.get("phone", "").strip()
            password = request.form.get("password", "")
            if not all([full_name, email, password]):
                flash("Zorunlu alanları doldurun.", "error")
                return render_template("client/register.html")

            pending = ClientProfile.query.filter_by(email=email, invite_accepted=False).first()
            if pending:
                pending.full_name = full_name or pending.full_name
                pending.phone = phone or pending.phone
                pending.user.password_hash = generate_password_hash(password, method="pbkdf2:sha256")
                pending.invite_accepted = True
                pending.invite_token = None
                db.session.commit()
                login_user(pending.user)
                flash("Üyeliğiniz aktifleştirildi.", "success")
                return redirect(url_for("client_portal"))

            if User.query.filter_by(username=email).first() or ClientProfile.query.filter_by(email=email).first():
                flash("Bu e-posta zaten kayıtlı. Giriş yapın.", "error")
                return redirect(url_for("client_login"))

            user = User(
                username=email,
                password_hash=generate_password_hash(password, method="pbkdf2:sha256"),
                role="client",
                is_active=True,
            )
            db.session.add(user)
            db.session.flush()
            profile = ClientProfile(
                user_id=user.id,
                full_name=full_name,
                email=email,
                phone=phone,
                invite_accepted=True,
                invite_token=None,
            )
            db.session.add(profile)
            db.session.commit()
            login_user(user)
            flash("Hesabınız oluşturuldu.", "success")
            return redirect(url_for("client_portal"))

        return render_template("client/register.html")

    @app.route("/uye/sifre-belirle/<token>", methods=["GET", "POST"])
    def client_set_password(token):
        profile = ClientProfile.query.filter_by(invite_token=token).first_or_404()
        if request.method == "POST":
            password = request.form.get("password", "")
            if len(password) < 6:
                flash("Şifre en az 6 karakter olmalı.", "error")
                return render_template("client/set_password.html", profile=profile)
            profile.user.password_hash = generate_password_hash(password, method="pbkdf2:sha256")
            profile.invite_accepted = True
            profile.invite_token = None
            db.session.commit()
            login_user(profile.user)
            flash("Şifreniz belirlendi.", "success")
            return redirect(url_for("client_portal"))
        return render_template("client/set_password.html", profile=profile)

    @app.route("/uye/cikis")
    def client_logout():
        logout_user()
        flash("Çıkış yapıldı.", "info")
        return redirect(url_for("client_login"))

    @app.route("/uye")
    @client_login_required
    def client_portal():
        user = get_current_user()
        profile = user.client_profile
        email = (profile.email if profile else user.username).lower()

        appointments = (
            Appointment.query.filter(Appointment.patient_email.ilike(email))
            .order_by(Appointment.appointment_date.desc())
            .all()
        )
        tests = (
            TestResult.query.filter(
                (TestResult.user_id == user.id) | (TestResult.patient_email.ilike(email))
            )
            .order_by(TestResult.created_at.desc())
            .limit(20)
            .all()
        )
        notes = (
            TherapistNote.query.filter(
                TherapistNote.visible_to_client.is_(True),
                (TherapistNote.client_user_id == user.id) | (TherapistNote.patient_email.ilike(email)),
            )
            .order_by(TherapistNote.created_at.desc())
            .all()
        )
        invoices = (
            Invoice.query.filter(
                (Invoice.client_user_id == user.id) | (Invoice.patient_email.ilike(email))
            )
            .order_by(Invoice.invoice_date.desc())
            .all()
        )
        return render_template(
            "client/portal.html",
            profile=profile,
            appointments=appointments,
            tests=tests,
            notes=notes,
            invoices=invoices,
        )
