from functools import wraps

from flask import flash, redirect, session, url_for

STAFF_ROLES = ("admin", "editor", "therapist")
ROLES = ("admin", "editor", "therapist", "client")

ROLE_LABELS = {
    "admin": "Klinik Yöneticisi",
    "editor": "Operasyon Editörü",
    "therapist": "Uzman Terapist",
    "client": "Danışan",
}

PERMISSIONS = {
    "dashboard": frozenset(STAFF_ROLES),
    "sliders": frozenset({"admin", "editor"}),
    "therapists": frozenset({"admin"}),
    "appointments": frozenset({"admin", "therapist"}),
    "blog": frozenset({"admin", "editor"}),
    "social": frozenset({"admin", "editor"}),
    "widgets": frozenset({"admin", "editor"}),
    "tests": frozenset({"admin", "editor"}),
    "theme": frozenset({"admin"}),
    "email": frozenset({"admin"}),
    "users": frozenset({"admin"}),
    "audit": frozenset({"admin"}),
    "analiz": frozenset({"admin", "editor"}),
    "sessions": frozenset({"admin", "therapist"}),
    "invoices": frozenset({"admin"}),
    "therapist_portal": frozenset({"therapist"}),
}


def role_has_permission(role, permission):
    return role in PERMISSIONS.get(permission, frozenset())


def plan_allows_module(plan_id, permission):
    from subscription_plans import plan_has_module

    return plan_has_module(plan_id, permission)


def user_can_access(user, permission, plan_id=None):
    if not user:
        return False
    if not role_has_permission(user.role, permission):
        return False
    if plan_id is None:
        from subscription_plans import get_active_plan

        plan_id = get_active_plan().get("id")
    return plan_allows_module(plan_id, permission)


def get_current_user():
    from models import User

    user_id = session.get("user_id")
    if not user_id:
        return None
    user = User.query.get(user_id)
    if not user or not user.is_active:
        return None
    return user


def login_user(user):
    session.clear()
    session["user_id"] = user.id
    session["username"] = user.username
    session["user_role"] = user.role
    if user.therapist_id:
        session["therapist_id"] = user.therapist_id
    try:
        from datetime import datetime

        acc = user.account_dict()
        acc["last_login_at"] = datetime.utcnow().isoformat(timespec="seconds")
        user.set_account_dict(acc)
        from models import db

        db.session.commit()
    except Exception:
        pass


def logout_user():
    session.clear()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user or user.role == "client":
            flash("Devam etmek için giriş yapın.", "warning")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)

    return decorated


def client_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user or user.role != "client":
            flash("Devam etmek için üye girişi yapın.", "warning")
            return redirect(url_for("client_login"))
        return f(*args, **kwargs)

    return decorated


def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            user = get_current_user()
            if not user or user.role == "client":
                flash("Devam etmek için giriş yapın.", "warning")
                return redirect(url_for("admin_login"))
            if not role_has_permission(user.role, permission):
                flash("Bu sayfaya erişim yetkiniz yok.", "error")
                return redirect(url_for("admin_dashboard"))
            from subscription_plans import get_active_plan

            plan = get_active_plan()
            if not plan_allows_module(plan.get("id"), permission):
                flash(
                    f"«{plan.get('label', 'Mevcut paket')}» paketinde bu modül yer almıyor. "
                    "Paket yükseltmesi için Abonelik sayfasına bakın.",
                    "warning",
                )
                return redirect(url_for("admin_subscription"))
            return f(*args, **kwargs)

        return wrapped

    return decorator


def therapist_appointment_scope(user, appointment):
    if user.role != "therapist":
        return True
    return user.therapist_id == appointment.therapist_id


def therapist_record_scope(user, therapist_id):
    if user.role != "therapist":
        return True
    return user.therapist_id == therapist_id


def require_therapist_profile(user):
    if not user or user.role != "therapist" or not user.therapist_id:
        return None
    return user.therapist_id
