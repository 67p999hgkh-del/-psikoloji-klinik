from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="admin")
    therapist_id = db.Column(db.Integer, db.ForeignKey("therapist.id"), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    account_data = db.Column(db.Text, default="{}")

    therapist = db.relationship("Therapist", backref=db.backref("user_account", uselist=False))

    ROLE_LABELS = {
        "admin": "Klinik Yöneticisi",
        "editor": "Operasyon Editörü",
        "therapist": "Uzman Terapist",
        "client": "Danışan",
    }

    STAFF_DISPLAY_NAMES = {
        "admin": "Genel Yönetim",
        "editor": "Operasyon Editörü",
        "therapist": "Uzman Terapist",
    }

    @property
    def role_label(self):
        return self.ROLE_LABELS.get(self.role, self.role)

    @property
    def display_name(self):
        acc = self.account_dict()
        custom = (acc.get("display_name") or acc.get("full_name") or "").strip()
        if custom:
            return custom
        return self.STAFF_DISPLAY_NAMES.get(self.role, self.username)

    def account_dict(self):
        import json

        try:
            data = json.loads(self.account_data or "{}")
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_account_dict(self, data):
        import json

        self.account_data = json.dumps(data or {}, ensure_ascii=False)


class Therapist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    bio = db.Column(db.Text, nullable=False)
    specialties = db.Column(db.String(300), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    city = db.Column(db.String(80), default="İstanbul")
    languages_spoken = db.Column(db.String(120), default="tr")
    supports_online = db.Column(db.Boolean, default=True)
    photo = db.Column(db.String(120), default="default.jpg")
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    calendar_token = db.Column(db.String(64), unique=True, nullable=True)
    ical_import_url = db.Column(db.String(500), default="")
    profile_data = db.Column(db.Text, default="{}")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    appointments = db.relationship("Appointment", backref="therapist", lazy=True)

    def language_codes(self):
        if not self.languages_spoken:
            return ["tr"]
        return [code.strip() for code in self.languages_spoken.split(",") if code.strip()]

    def profile_dict(self):
        import json

        try:
            data = json.loads(self.profile_data or "{}")
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_profile_dict(self, data):
        import json

        self.profile_data = json.dumps(data or {}, ensure_ascii=False)

    def specialty_list(self):
        return [s.strip() for s in (self.specialties or "").split(",") if s.strip()]


class SiteSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    logo_url = db.Column(db.String(500), default="")
    logo_icon = db.Column(db.String(20), default="🧠")
    site_name = db.Column(db.String(200), default="PsikoHukuk Danışmanlık Merkezi")
    site_tagline = db.Column(db.String(300), default="Psikolojik Danışmanlık")
    site_description = db.Column(db.Text, default="")
    site_keywords = db.Column(db.Text, default="")
    primary_color = db.Column(db.String(20), default="#2d6a6a")
    primary_dark = db.Column(db.String(20), default="#1f4f4f")
    accent_color = db.Column(db.String(20), default="#c4846c")
    bg_color = db.Column(db.String(20), default="#faf9f7")
    smtp_host = db.Column(db.String(120), default="")
    smtp_port = db.Column(db.Integer, default=587)
    smtp_user = db.Column(db.String(120), default="")
    smtp_password = db.Column(db.String(200), default="")
    smtp_from = db.Column(db.String(120), default="")
    admin_email = db.Column(db.String(120), default="")
    email_enabled = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    theme_data = db.Column(db.Text, default="{}")
    email_data = db.Column(db.Text, default="{}")
    subscription_plan = db.Column(db.String(30), default="enterprise")

    @classmethod
    def get(cls):
        settings = cls.query.first()
        if not settings:
            from helpers import SITE_DESCRIPTION, SITE_KEYWORDS, SITE_NAME, SITE_TAGLINE

            settings = cls(
                site_name=SITE_NAME,
                site_tagline=SITE_TAGLINE,
                site_description=SITE_DESCRIPTION,
                site_keywords=SITE_KEYWORDS,
            )
            db.session.add(settings)
            db.session.commit()
        return settings

    def theme_dict(self):
        import json

        try:
            data = json.loads(self.theme_data or "{}")
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_theme_dict(self, data):
        import json

        self.theme_data = json.dumps(data or {}, ensure_ascii=False)

    def email_dict(self):
        import json

        try:
            data = json.loads(self.email_data or "{}")
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_email_dict(self, data):
        import json

        self.email_data = json.dumps(data or {}, ensure_ascii=False)


class EmailLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    template_key = db.Column(db.String(80), default="")
    subject = db.Column(db.String(300), default="")
    recipient = db.Column(db.String(200), default="")
    sender = db.Column(db.String(200), default="")
    module = db.Column(db.String(50), default="")
    status = db.Column(db.String(30), default="queued", index=True)
    provider_message_id = db.Column(db.String(200), default="")
    attempt_count = db.Column(db.Integer, default=0)
    error_code = db.Column(db.String(50), default="")
    error_message = db.Column(db.Text, default="")
    duration_ms = db.Column(db.Integer, default=0)
    is_test = db.Column(db.Boolean, default=False)
    language = db.Column(db.String(5), default="tr")
    branch = db.Column(db.String(80), default="Merkez")

    STATUS_LABELS = {
        "queued": "Kuyrukta",
        "sending": "Gönderiliyor",
        "sent": "Gönderildi",
        "delivered": "Teslim Edildi",
        "opened": "Açıldı",
        "clicked": "Tıklandı",
        "failed": "Başarısız",
        "bounced": "Geri Döndü",
        "spam": "Spam Olarak İşaretlendi",
    }

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, self.status)


class Lawyer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    bio = db.Column(db.Text, nullable=False)
    specialties = db.Column(db.String(300), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    bar_association = db.Column(db.String(120), default="")
    photo = db.Column(db.String(120), default="default.jpg")
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    therapist_id = db.Column(db.Integer, db.ForeignKey("therapist.id"), nullable=False)
    patient_name = db.Column(db.String(120), nullable=False)
    patient_email = db.Column(db.String(120), nullable=False)
    patient_phone = db.Column(db.String(30), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    session_type = db.Column(db.String(20), default="yuz_yuze")
    visit_type = db.Column(db.String(30), default="")
    duration_minutes = db.Column(db.Integer, default=50)
    notes = db.Column(db.Text, default="")
    status = db.Column(db.String(20), default="beklemede")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    STATUS_LABELS = {
        "beklemede": "Beklemede",
        "onaylandi": "Onaylandı",
        "iptal": "İptal",
        "tamamlandi": "Tamamlandı",
    }

    SESSION_LABELS = {
        "yuz_yuze": "Yüz Yüze",
        "online": "Online",
    }

    VISIT_LABELS = {
        "ilk": "İlk Görüşme",
        "kontrol": "Kontrol",
    }


class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    excerpt = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(100), default="Genel")
    tags = db.Column(db.String(500), default="")
    seo_title = db.Column(db.String(200), default="")
    seo_description = db.Column(db.Text, default="")
    seo_keywords = db.Column(db.String(500), default="")
    featured_image = db.Column(db.String(300), default="")
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def tag_list(self):
        from helpers import parse_tags

        return parse_tags(self.tags)

    def keyword_list(self):
        from helpers import parse_tags

        combined = " ".join(filter(None, [self.tags, self.seo_keywords]))
        return parse_tags(combined)

    def seo_keyword_list(self):
        from helpers import parse_tags

        return parse_tags(self.seo_keywords)


class Slider(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subtitle = db.Column(db.String(300), default="")
    image_url = db.Column(db.String(500), default="")
    button_text = db.Column(db.String(80), default="")
    button_link = db.Column(db.String(300), default="")
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Widget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    widget_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def parsed_content(self):
        import json

        try:
            return json.loads(self.content)
        except (json.JSONDecodeError, TypeError):
            return {}


class PsychologicalTest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(80), default="Genel")
    icon = db.Column(db.String(20), default="📋")
    source_note = db.Column(db.String(300), default="")
    seo_title = db.Column(db.String(200), default="")
    seo_description = db.Column(db.Text, default="")
    seo_keywords = db.Column(db.String(500), default="")
    hero_title = db.Column(db.String(200), default="")
    hero_subtitle = db.Column(db.Text, default="")
    duration_minutes = db.Column(db.Integer, default=5)
    accent_color = db.Column(db.String(20), default="#2d6a6a")
    benefits = db.Column(db.Text, default="")
    match_tags = db.Column(db.String(300), default="")
    test_group = db.Column(db.String(50), default="mood")
    available_langs = db.Column(db.String(50), default="tr,en,de")
    questions = db.Column(db.Text, nullable=False)
    scoring_type = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def question_list(self):
        import json

        try:
            return json.loads(self.questions)
        except (json.JSONDecodeError, TypeError):
            return []

    def benefit_list(self):
        import json

        try:
            return json.loads(self.benefits or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    def match_tag_list(self):
        if not self.match_tags:
            return []
        return [tag.strip() for tag in self.match_tags.split(",") if tag.strip()]

    def display_seo_title(self):
        return self.seo_title or self.hero_title or self.title

    def estimated_minutes(self):
        if self.duration_minutes:
            return self.duration_minutes
        return max(3, round(len(self.question_list()) * 0.5))

    def available_lang_codes(self):
        raw = self.available_langs or "tr,en,de"
        return [code.strip() for code in raw.split(",") if code.strip()]

    def supports_lang(self, lang):
        return lang in self.available_lang_codes()

    def keyword_list(self):
        from helpers import parse_tags

        return parse_tags(self.seo_keywords or "")


class VisitorHit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.String(64), nullable=False, index=True)
    path = db.Column(db.String(300), default="/")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class ClientProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30), default="")
    invite_token = db.Column(db.String(64), unique=True, nullable=True)
    invite_accepted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("client_profile", uselist=False))


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    username = db.Column(db.String(80), default="")
    action = db.Column(db.String(80), nullable=False)
    entity_type = db.Column(db.String(80), default="")
    entity_id = db.Column(db.Integer, nullable=True)
    detail = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship("User", backref=db.backref("audit_logs", lazy=True))


class SessionRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointment.id"), nullable=True)
    therapist_id = db.Column(db.Integer, db.ForeignKey("therapist.id"), nullable=False)
    client_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    patient_name = db.Column(db.String(120), default="")
    patient_email = db.Column(db.String(120), default="", index=True)
    city = db.Column(db.String(80), default="")
    reasons = db.Column(db.Text, default="[]")
    note = db.Column(db.Text, default="")
    session_type = db.Column(db.String(20), default="yuz_yuze")
    status = db.Column(db.String(20), default="devam")
    risk_level = db.Column(db.String(20), default="dusuk")
    duration_minutes = db.Column(db.Integer, default=50)
    next_session_date = db.Column(db.Date, nullable=True)
    workspace_data = db.Column(db.Text, default="{}")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    therapist = db.relationship("Therapist", backref=db.backref("session_records", lazy=True))
    appointment = db.relationship("Appointment", backref=db.backref("session_records", lazy=True))
    client_user = db.relationship("User", backref=db.backref("session_records", lazy=True))

    STATUS_LABELS = {
        "devam": "Devam ediyor",
        "beklemede": "Beklemede",
        "sonlandi": "Sonlandı",
        "gelmedi": "Gelmedi",
    }

    RISK_LABELS = {
        "dusuk": "Düşük Risk",
        "orta": "Orta Risk",
        "yuksek": "Yüksek Risk",
    }

    SESSION_LABELS = {
        "yuz_yuze": "Yüz Yüze",
        "online": "Online",
    }

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, self.status)

    @property
    def risk_label(self):
        return self.RISK_LABELS.get(self.risk_level, self.risk_level)

    @property
    def session_type_label(self):
        return self.SESSION_LABELS.get(self.session_type, self.session_type)

    def reason_list(self):
        import json

        try:
            data = json.loads(self.reasons or "[]")
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    def workspace_dict(self):
        import json

        try:
            data = json.loads(self.workspace_data or "{}")
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_workspace_dict(self, data):
        import json

        self.workspace_data = json.dumps(data or {}, ensure_ascii=False)


class TherapistNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    therapist_id = db.Column(db.Integer, db.ForeignKey("therapist.id"), nullable=False)
    client_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    patient_email = db.Column(db.String(120), default="", index=True)
    body = db.Column(db.Text, nullable=False)
    visible_to_client = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    therapist = db.relationship("Therapist", backref=db.backref("client_notes", lazy=True))
    client_user = db.relationship("User", backref=db.backref("therapist_notes", lazy=True))


class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    patient_email = db.Column(db.String(120), default="", index=True)
    patient_name = db.Column(db.String(120), default="")
    therapist_id = db.Column(db.Integer, db.ForeignKey("therapist.id"), nullable=True)
    amount = db.Column(db.Float, nullable=False, default=0)
    currency = db.Column(db.String(10), default="TRY")
    description = db.Column(db.String(300), default="")
    invoice_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), default="bekliyor")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    STATUS_LABELS = {
        "bekliyor": "Bekliyor",
        "odendi": "Ödendi",
        "iptal": "İptal",
    }

    therapist = db.relationship("Therapist", backref=db.backref("invoices", lazy=True))
    client_user = db.relationship("User", backref=db.backref("invoices", lazy=True))


class TestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey("psychological_test.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    patient_email = db.Column(db.String(120), default="", index=True)
    patient_name = db.Column(db.String(120), default="")
    score = db.Column(db.Float, default=0)
    level = db.Column(db.String(80), default="")
    summary = db.Column(db.Text, default="")
    result_json = db.Column(db.Text, default="{}")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    test = db.relationship("PsychologicalTest", backref=db.backref("results", lazy=True))
    user = db.relationship("User", backref=db.backref("test_results", lazy=True))

    def parsed_result(self):
        import json

        try:
            return json.loads(self.result_json or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}


