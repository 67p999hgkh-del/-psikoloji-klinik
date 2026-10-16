import json
import os
import secrets
from datetime import date, datetime, timedelta

from flask import (
    Flask,
    Response,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import func

from auth import (
    ROLE_LABELS,
    ROLES,
    STAFF_ROLES,
    get_current_user,
    login_required,
    login_user,
    logout_user,
    permission_required,
    therapist_appointment_scope,
)
from calendar_sync import ensure_calendar_token, generate_therapist_ics
from email_service import notify_appointment_confirmed, notify_appointment_created
from i18n import SUPPORTED_LANGUAGES, translate
from helpers import (
    SITE_DESCRIPTION,
    SITE_KEYWORDS,
    SITE_NAME,
    SITE_TAGLINE,
    WORK_HOURS,
    format_time_slot,
    get_month_availability,
    is_slot_blocked,
    migrate_schema,
    parse_tags,
    parse_time_slot,
    tags_to_slug,
)
from models import Appointment, BlogPost, PsychologicalTest, SiteSettings, Slider, Therapist, User, VisitorHit, Widget, db
from site_content import (
    COUNTRY_FLAG,
    LANG_FLAGS,
    POPULAR_CITIES,
    get_booking_steps,
    get_info_slides,
    get_test_groups,
    get_therapist_tip,
)
from test_data import TESTIMONIALS, seed_psychological_tests, upgrade_psychological_tests
from test_matching import get_recommended_therapists
from tests_engine import score_test
from uploads import save_person_photo
from psikoplan import SPECIALTY_FILTERS, appointment_chart_stats, ensure_client_invite, log_audit
from routes_extra import register_extra_routes
from models import ClientProfile, SessionRecord, TestResult
import json as json_lib

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "psikohukuk-gizli-anahtar")
_default_db = "sqlite:///" + os.path.join(INSTANCE_DIR, "klinik.db")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", _default_db)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 86400
STATIC_VERSION = "20261016analiz1"

db.init_app(app)

WIDGET_TYPES = {
    "hero": "Hero Banner",
    "stats": "İstatistikler",
    "testimonials": "Referanslar",
    "faq": "Sık Sorulan Sorular",
    "cta": "Çağrı Butonu",
    "hours": "Çalışma Saatleri",
    "text": "Metin Bloğu",
    "social": "Sosyal Medya",
}

BLOG_CATEGORIES = ["Genel", "Psikoloji", "Kişisel Gelişim", "Aile", "Çocuk"]

VISITOR_LIVE_MINUTES = 5


def should_track_visit():
    if not request.endpoint:
        return False
    if request.endpoint == "static":
        return False
    if request.endpoint.startswith("admin") or request.path.startswith("/admin"):
        return False
    return True


def track_page_visit():
    if not should_track_visit():
        return

    visitor_id = session.get("visitor_id")
    if not visitor_id:
        visitor_id = secrets.token_hex(16)
        session["visitor_id"] = visitor_id

    now = datetime.utcnow()
    last_track = session.get("visitor_tracked_at")
    if last_track:
        try:
            if (now - datetime.fromisoformat(last_track)).total_seconds() < 60:
                return
        except ValueError:
            pass

    session["visitor_tracked_at"] = now.isoformat()
    db.session.add(VisitorHit(visitor_id=visitor_id, path=(request.path or "/")[:300]))
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


def get_visitor_stats():
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    live_since = now - timedelta(minutes=VISITOR_LIVE_MINUTES)
    return {
        "total": VisitorHit.query.count(),
        "monthly": VisitorHit.query.filter(VisitorHit.created_at >= month_start).count(),
        "live": db.session.query(func.count(func.distinct(VisitorHit.visitor_id)))
        .filter(VisitorHit.created_at >= live_since)
        .scalar()
        or 0,
    }


@app.before_request
def before_request_track_visit():
    track_page_visit()


def get_lang():
    lang = session.get("lang", "tr")
    return lang if lang in dict(SUPPORTED_LANGUAGES) else "tr"


def t(key, **kwargs):
    return translate(key, get_lang(), **kwargs)


def parse_lang_codes(form, field="languages_spoken", default="tr"):
    codes = form.getlist(field)
    cleaned = [code.strip() for code in codes if code.strip()]
    return ",".join(cleaned) if cleaned else default


def filter_tests_for_lang(tests, lang):
    return [test for test in tests if test.supports_lang(lang)]


def filter_tests_for_lang(tests, lang):
    return [test for test in tests if test.supports_lang(lang)]


BLOG_FEATURED_IMAGES = {
    "kaygiyla-basa-cikmanin-5-yolu": "https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=800&h=450&fit=crop",
    "bosanma-surecinde-duygusal-destek": "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=800&h=450&fit=crop",
    "cocuklarda-duygusal-gelisim": "https://images.unsplash.com/photo-1503454537841-d6e83f1a4212?w=800&h=450&fit=crop",
    "cift-terapisinde-iletisim": "https://images.unsplash.com/photo-1529336953122-58e48760d1f0?w=800&h=450&fit=crop",
    "cift-terapisinde-iletisimin-onemi": "https://images.unsplash.com/photo-1516589178581-6cd7833ae3b2?w=800&h=450&fit=crop",
    "online-terapi-evden-guvenli-destek": "https://images.unsplash.com/photo-1604881991720-f8add664547e?w=800&h=450&fit=crop",
    "depresyon-belirtilerini-erken-fark-etmek": "https://images.unsplash.com/photo-1499203531755-b5ee34a2a7a0?w=800&h=450&fit=crop",
    "panik-atakla-basa-cikma-rehberi": "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=800&h=450&fit=crop",
    "is-yerinde-mobbing-ve-psikolojik-destek": "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=800&h=450&fit=crop",
}


def ensure_blog_featured_images():
    changed = False
    for post in BlogPost.query.all():
        image = BLOG_FEATURED_IMAGES.get(post.slug)
        if image and post.featured_image != image:
            post.featured_image = image
            changed = True
    return changed


EXTRA_BLOG_POST_DATA = [
    {
        "title": "Çift Terapisinde İletişimin Önemi",
        "slug": "cift-terapisinde-iletisimin-onemi",
        "excerpt": "İlişkide sağlıklı iletişim kurmanın yolları ve çift terapisinin rolü.",
        "content": (
            "<p>Çift terapisinde en sık karşılaşılan zorluklardan biri, duyguları yargılamadan ifade edememektir. "
            "Aktif dinleme, empati ve net sınır koyma; ilişkide güveni yeniden inşa etmenin temel adımlarıdır.</p>"
            "<p>Terapist eşliğinde yapılandırılmış iletişim egzersizleri, tarafların birbirini duymasını kolaylaştırır "
            "ve tekrarlayan çatışma döngülerini kırmaya yardımcı olur.</p>"
        ),
        "author": "Dr. Ayşe Yılmaz",
        "category": "Psikoloji",
        "tags": "#ciftterapisi #iletisim #iliskiler #psikoloji",
        "seo_title": "Çift Terapisinde İletişimin Önemi | PsikoHukuk",
        "seo_description": "Çift terapisinde sağlıklı iletişim kurma yöntemleri ve uzman desteği.",
        "seo_keywords": "#ciftterapisi #iletisim #iliskipsikolojisi",
        "featured_image": "https://images.unsplash.com/photo-1516589178581-6cd7833ae3b2?w=800&h=450&fit=crop",
    },
    {
        "title": "Online Terapi: Evden Güvenli Destek",
        "slug": "online-terapi-evden-guvenli-destek",
        "excerpt": "Online terapi nasıl işler, kimler için uygundur ve nelere dikkat edilmeli?",
        "content": (
            "<p>Online terapi, video görüşme platformları üzerinden yürütülen profesyonel psikolojik destek sürecidir. "
            "Zaman ve mekân esnekliği sunması en büyük avantajlarından biridir.</p>"
            "<p>Gizlilik ilkelerine uygun platformlar, düzenli seans rutini ve güvenli bir ortam; online terapinin "
            "etkinliği için kritik unsurlardır.</p>"
        ),
        "author": "Dr. Mehmet Kaya",
        "category": "Psikoloji",
        "tags": "#onlineterapi #terapi #psikoloji #randevu",
        "seo_title": "Online Terapi Nedir? Evden Güvenli Psikolojik Destek",
        "seo_description": "Online terapi süreci, avantajları ve kimler için uygun olduğu hakkında rehber.",
        "seo_keywords": "#onlineterapi #psikolojikdestek #videoTerapi",
        "featured_image": "https://images.unsplash.com/photo-1604881991720-f8add664547e?w=800&h=450&fit=crop",
    },
    {
        "title": "Depresyon Belirtilerini Erken Fark Etmek",
        "slug": "depresyon-belirtilerini-erken-fark-etmek",
        "excerpt": "Depresyonun erken belirtileri ve ne zaman profesyonel destek alınmalı?",
        "content": (
            "<p>Depresyon; isteksizlik, uyku ve iştah değişiklikleri, yoğun yorgunluk ve umutsuzluk duygusu ile "
            "kendini gösterebilir. Belirtiler haftalarca sürüyorsa profesyonel değerlendirme önemlidir.</p>"
            "<p>Erken müdahale, iyileşme sürecini hızlandırır. Terapist ve gerektiğinde psikiyatrist desteği "
            "kişiye özel bir tedavi planı oluşturulmasını sağlar.</p>"
        ),
        "author": "Dr. Zeynep Demir",
        "category": "Psikoloji",
        "tags": "#depresyon #ruhsagligi #terapi #psikoloji",
        "seo_title": "Depresyon Belirtileri ve Erken Müdahale Rehberi",
        "seo_description": "Depresyon belirtilerini tanıma ve ne zaman destek almanız gerektiği.",
        "seo_keywords": "#depresyon #ruhsagligi #psikolojikdestek",
        "featured_image": "https://images.unsplash.com/photo-1499203531755-b5ee34a2a7a0?w=800&h=450&fit=crop",
    },
    {
        "title": "Panik Atakla Başa Çıkma Rehberi",
        "slug": "panik-atakla-basa-cikma-rehberi",
        "excerpt": "Panik atak anında uygulanabilecek pratik teknikler ve uzun vadeli destek.",
        "content": (
            "<p>Panik atak; hızlı kalp atışı, nefes darlığı ve yoğun korku hissi ile ani başlayabilir. "
            "4-7-8 nefes tekniği ve yerleştirme (grounding) egzersizleri akut dönemde rahatlatıcı olabilir.</p>"
            "<p>Tekrarlayan panik ataklar için bilişsel davranışçı terapi ve düzenli terapist desteği "
            "kalıcı iyileşmede etkilidir.</p>"
        ),
        "author": "Dr. Ayşe Yılmaz",
        "category": "Psikoloji",
        "tags": "#panikatak #anksiyete #terapi #nefes",
        "seo_title": "Panik Atakla Başa Çıkma: Pratik Teknikler",
        "seo_description": "Panik atak anında uygulanabilecek teknikler ve terapi desteği hakkında bilgi.",
        "seo_keywords": "#panikatak #anksiyete #grounding",
        "featured_image": "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=800&h=450&fit=crop",
    },
    {
        "title": "İş Yerinde Mobbing ve Psikolojik Destek",
        "slug": "is-yerinde-mobbing-ve-psikolojik-destek",
        "excerpt": "İş yerinde psikolojik taciz (mobbing) nedir ve nasıl destek alınır?",
        "content": (
            "<p>İş yerinde mobbing; sistematik aşağılama, dışlama veya psikolojik baskı biçiminde ortaya çıkabilir. "
            "Bu süreç kaygı, uykusuzluk ve özgüven kaybına yol açabilir.</p>"
            "<p>Erken psikolojik destek almak, duygusal dayanıklılığı güçlendirmek ve sağlıklı başa çıkma "
            "stratejileri geliştirmek açısından önemlidir.</p>"
        ),
        "author": "Dr. Mehmet Kaya",
        "category": "Psikoloji",
        "tags": "#mobbing #stres #ispsikolojisi #psikoloji",
        "seo_title": "İş Yerinde Mobbing ve Psikolojik Destek",
        "seo_description": "Mobbing nedir, etkileri nelerdir ve ne zaman psikolojik destek alınmalı?",
        "seo_keywords": "#mobbing #stres #psikolojiktaciz",
        "featured_image": "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=800&h=450&fit=crop",
    },
]


def build_extra_blog_posts():
    posts = []
    for index, data in enumerate(EXTRA_BLOG_POST_DATA):
        posts.append(
            BlogPost(
                title=data["title"],
                slug=data["slug"],
                excerpt=data["excerpt"],
                content=data["content"],
                author=data["author"],
                category=data["category"],
                tags=data["tags"],
                seo_title=data["seo_title"],
                seo_description=data["seo_description"],
                seo_keywords=data.get("seo_keywords", ""),
                featured_image=data.get("featured_image", ""),
                is_published=True,
                created_at=datetime.utcnow() - timedelta(days=index * 4),
            )
        )
    return posts


def ensure_extra_blog_posts():
    changed = False
    for index, data in enumerate(EXTRA_BLOG_POST_DATA):
        if BlogPost.query.filter_by(slug=data["slug"]).first():
            continue
        db.session.add(
            BlogPost(
                title=data["title"],
                slug=data["slug"],
                excerpt=data["excerpt"],
                content=data["content"],
                author=data["author"],
                category=data["category"],
                tags=data["tags"],
                seo_title=data["seo_title"],
                seo_description=data["seo_description"],
                seo_keywords=data.get("seo_keywords", ""),
                featured_image=data.get("featured_image", ""),
                is_published=True,
                created_at=datetime.utcnow() - timedelta(days=index * 4),
            )
        )
        changed = True
    return changed


def get_site_settings():
    return SiteSettings.get()


def normalize_session_type(value):
    session_type = (value or "yuz_yuze").strip().lower()
    if session_type not in {"online", "yuz_yuze"}:
        return "yuz_yuze"
    return session_type


def filter_therapists(city=None, q=None, session_type=None, specialties=None):
    query = Therapist.query.filter_by(is_active=True)
    if session_type == "online":
        query = query.filter_by(supports_online=True)
    elif city:
        query = query.filter_by(city=city)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            db.or_(
                Therapist.name.ilike(term),
                Therapist.title.ilike(term),
                Therapist.specialties.ilike(term),
            )
        )
    if specialties:
        for spec in specialties:
            spec = (spec or "").strip()
            if spec:
                query = query.filter(Therapist.specialties.ilike(f"%{spec}%"))
    return query.order_by(Therapist.sort_order).all()


def parse_specialty_args():
    values = request.args.getlist("specialty")
    if not values:
        raw = request.args.get("specialty", "").strip()
        if raw:
            values = [part.strip() for part in raw.split(",") if part.strip()]
    return [v for v in values if v in SPECIALTY_FILTERS]


def build_search_suggestions(q, limit=8):
    term = q.strip()
    if len(term) < 2:
        return []

    therapists = filter_therapists(q=term)
    suggestions = []
    seen = set()

    for therapist in therapists:
        suggestions.append(
            {
                "type": "therapist",
                "label": therapist.name,
                "meta": f"{therapist.title} · {therapist.city or 'İstanbul'}",
                "url": url_for("therapist_detail", slug=therapist.slug),
            }
        )
        seen.add(therapist.name.lower())

    for therapist in Therapist.query.filter_by(is_active=True).all():
        for specialty in [s.strip() for s in therapist.specialties.split(",") if s.strip()]:
            key = specialty.lower()
            if key in seen:
                continue
            if term.lower() in specialty.lower():
                suggestions.append(
                    {
                        "type": "specialty",
                        "label": specialty,
                        "meta": translate("therapist.specialty", get_lang()).replace(":", ""),
                        "url": None,
                    }
                )
                seen.add(key)
            if len(suggestions) >= limit:
                break
        if len(suggestions) >= limit:
            break

    return suggestions[:limit]


def seo_context(title=None, description=None, keywords=None, image=None, page_type="website"):
    settings = get_site_settings()
    site_name = settings.site_name or SITE_NAME
    page_title = title or site_name
    if title and site_name not in title:
        page_title = f"{title} — {site_name}"

    return {
        "seo_title": page_title,
        "seo_description": description or settings.site_description or SITE_DESCRIPTION,
        "seo_keywords": keywords or settings.site_keywords or SITE_KEYWORDS,
        "seo_image": image or settings.logo_url or "",
        "seo_type": page_type,
        "seo_url": request.url if request else "",
    }


def get_blog_sidebar_data():
    recent_posts = (
        BlogPost.query.filter_by(is_published=True).order_by(BlogPost.created_at.desc()).limit(5).all()
    )
    categories = (
        db.session.query(BlogPost.category, db.func.count(BlogPost.id))
        .filter_by(is_published=True)
        .group_by(BlogPost.category)
        .all()
    )
    all_tags = []
    for post in BlogPost.query.filter_by(is_published=True).all():
        all_tags.extend(post.tag_list())
    unique_tags = sorted(set(all_tags), key=str.lower)[:20]
    return {
        "sidebar_recent": recent_posts,
        "sidebar_categories": categories,
        "sidebar_tags": unique_tags,
    }


def seed_database():
    if User.query.first():
        return

    admin = User(
        username="admin",
        password_hash=generate_password_hash("admin123", method="pbkdf2:sha256"),
        role="admin",
        is_active=True,
    )
    db.session.add(admin)

    therapists = [
        Therapist(
            name="Dr. Ayşe Yılmaz",
            title="Klinik Psikolog",
            slug="ayse-yilmaz",
            bio="15 yıllık deneyimiyle bireysel terapi, kaygı bozuklukları ve travma sonrası destek alanlarında uzmanlaşmıştır.",
            specialties="Kaygı Bozuklukları, Travma, Bireysel Terapi",
            email="ayse@psikohukuk.com",
            phone="+90 532 000 0001",
            city="İstanbul",
            is_active=True,
            sort_order=1,
        ),
        Therapist(
            name="Uzm. Psk. Mehmet Kaya",
            title="Aile ve Çift Terapisti",
            slug="mehmet-kaya",
            bio="Çift ve aile dinamiklerinde 10 yılı aşkın deneyime sahip, EMDR sertifikalı uzman psikolog.",
            specialties="Çift Terapisi, Aile Danışmanlığı, EMDR",
            email="mehmet@psikohukuk.com",
            phone="+90 532 000 0002",
            city="Ankara",
            is_active=True,
            sort_order=2,
        ),
        Therapist(
            name="Dr. Zeynep Demir",
            title="Çocuk ve Ergen Psikoloğu",
            slug="zeynep-demir",
            bio="Çocuk ve ergenlerde davranış sorunları, DEHB ve okul uyumu konularında uzman.",
            specialties="Çocuk Psikolojisi, DEHB, Oyun Terapisi",
            email="zeynep@psikohukuk.com",
            phone="+90 532 000 0003",
            city="İzmir",
            is_active=True,
            sort_order=3,
        ),
    ]
    db.session.add_all(therapists)

    posts = [
        BlogPost(
            title="Kaygıyla Başa Çıkmanın 5 Etkili Yolu",
            slug="kaygiyla-basa-cikmanin-5-yolu",
            excerpt="Günlük hayatta kaygıyı yönetmek için uygulanabilir stratejiler.",
            content="<p>Kaygı, hayatın doğal bir parçasıdır. Ancak yoğunlaştığında günlük işlevselliğimizi etkileyebilir...</p><p>Nefes egzersizleri, mindfulness ve düzenli uyku kaygı yönetiminde temel taşlardır.</p>",
            author="Dr. Ayşe Yılmaz",
            category="Psikoloji",
            tags="#kaygi #terapi #psikoloji #mindfulness",
            seo_title="Kaygıyla Başa Çıkmanın 5 Etkili Yolu | PsikoHukuk",
            seo_description="Kaygı yönetimi için pratik psikoloji önerileri ve terapi desteği.",
            featured_image=BLOG_FEATURED_IMAGES["kaygiyla-basa-cikmanin-5-yolu"],
            is_published=True,
        ),
        BlogPost(
            title="Boşanma Sürecinde Duygusal Destek",
            slug="bosanma-surecinde-duygusal-destek",
            excerpt="Boşanma sürecinde duygusal dengeyi korumak ve terapi desteği almak.",
            content="<p>Boşanma süreci duygusal açıdan zorlu olabilir...</p><p>Yas, öfke ve belirsizlik duygularını yönetmek için profesyonel psikolojik destek almak önemlidir.</p>",
            author="Dr. Ayşe Yılmaz",
            category="Aile",
            tags="#bosanma #aile #terapi #duygusaldestek",
            seo_title="Boşanma Sürecinde Duygusal Destek",
            seo_description="Boşanma sürecinde duygusal denge, başa çıkma ve terapi desteği hakkında rehber.",
            featured_image=BLOG_FEATURED_IMAGES["bosanma-surecinde-duygusal-destek"],
            is_published=True,
        ),
        BlogPost(
            title="Çocuklarda Duygusal Gelişim",
            slug="cocuklarda-duygusal-gelisim",
            excerpt="Ebeveynler için çocuk duygusal gelişimi rehberi.",
            content="<p>Çocukların duygusal ihtiyaçlarını anlamak ve desteklemek, sağlıklı bir gelişim için kritiktir...</p>",
            author="Dr. Zeynep Demir",
            category="Çocuk",
            tags="#cocuk #gelisim #ebeveynlik #psikoloji",
            seo_title="Çocuklarda Duygusal Gelişim Rehberi",
            seo_description="Çocuk psikolojisi ve duygusal gelişim hakkında ebeveyn rehberi.",
            featured_image=BLOG_FEATURED_IMAGES["cocuklarda-duygusal-gelisim"],
            is_published=True,
        ),
    ]
    posts.extend(build_extra_blog_posts())
    db.session.add_all(posts)

    slides = [
        Slider(
            title="PsikoHukuk Danışmanlık Merkezi",
            subtitle="Ruh sağlığınız için profesyonel psikolojik destek.",
            image_url="https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?w=1200&h=340&fit=crop",
            button_text="Randevu Al",
            button_link="/randevu",
            sort_order=1,
        ),
        Slider(
            title="Uzman Kadro, Güvenilir Hizmet",
            subtitle="Deneyimli psikologlarımızla yanınızdayız.",
            image_url="https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=1200&h=340&fit=crop",
            button_text="Ekibimiz",
            button_link="/terapistler",
            sort_order=2,
        ),
        Slider(
            title="Huzurlu Bir Başlangıç",
            subtitle="Ruh sağlığınız için güvenli ve sakin bir ortamda destek alın.",
            image_url="https://images.unsplash.com/photo-1779838386666-6d110f33079b?w=1200&h=340&fit=crop",
            button_text="Randevu Al",
            button_link="/randevu",
            sort_order=3,
        ),
    ]
    db.session.add_all(slides)

    widgets = [
        Widget(
            widget_type="social",
            title="Bizi Takip Edin",
            content=json.dumps(
                {
                    "items": [
                        {"platform": "instagram", "url": "https://instagram.com", "label": "Instagram"},
                        {"platform": "facebook", "url": "https://facebook.com", "label": "Facebook"},
                        {"platform": "linkedin", "url": "https://linkedin.com", "label": "LinkedIn"},
                        {"platform": "youtube", "url": "https://youtube.com", "label": "YouTube"},
                    ]
                },
                ensure_ascii=False,
            ),
            is_active=True,
            sort_order=1,
        ),
        Widget(
            widget_type="stats",
            title="Rakamlarla Biz",
            content=json.dumps(
                {
                    "items": [
                        {"value": "15+", "label": "Uzman Psikolog", "color": "blue"},
                        {"value": "3000+", "label": "Randevu", "color": "purple"},
                        {"value": "20", "label": "Şehir", "color": "green"},
                        {"value": "4.9/5", "label": "Memnuniyet", "color": "orange"},
                    ]
                },
                ensure_ascii=False,
            ),
            is_active=True,
            sort_order=2,
        ),
        Widget(
            widget_type="testimonials",
            title="Danışanlarımız Ne Diyor?",
            content=json.dumps(
                {
                    "items": [
                        {"text": "Profesyonel psikolojik destek almak hayatımı kolaylaştırdı.", "author": "M.T."},
                        {"text": "Profesyonel ve güvenilir bir ekip. Kesinlikle tavsiye ederim.", "author": "S.K."},
                    ]
                },
                ensure_ascii=False,
            ),
            is_active=True,
            sort_order=3,
        ),
        Widget(
            widget_type="faq",
            title="Sık Sorulan Sorular",
            content=json.dumps(
                {
                    "items": [
                        {"q": "İlk seans nasıl geçer?", "a": "İlk seans tanışma ve ihtiyaç analizi odaklıdır, yaklaşık 50 dakika sürer."},
                        {"q": "Online terapi mümkün mü?", "a": "Evet, tüm terapistlerimiz online seans seçeneği sunmaktadır."},
                        {"q": "Seans ücreti ne kadar?", "a": "Seans ücretleri uzmana göre değişir; detaylar terapist profilinde yer alır."},
                    ]
                },
                ensure_ascii=False,
            ),
            is_active=True,
            sort_order=4,
        ),
        Widget(
            widget_type="cta",
            title="Hemen Randevu Alın",
            content=json.dumps(
                {"text": "Psikolojik destek için uygun saati takvimden seçin.", "button_text": "Randevu Takvimi", "button_link": "/randevu"},
                ensure_ascii=False,
            ),
            is_active=True,
            sort_order=5,
        ),
    ]
    db.session.add_all(widgets)
    db.session.commit()


def ensure_upgrade_data():
    changed = False

    if Slider.query.count() == 0:
        db.session.add_all([
            Slider(
                title="PsikoHukuk Danışmanlık Merkezi",
                subtitle="Ruh sağlığınız için profesyonel psikolojik destek.",
                image_url="https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?w=1200&h=340&fit=crop",
                button_text="Randevu Al",
                button_link="/randevu",
                sort_order=1,
            ),
            Slider(
                title="Uzman Kadro, Güvenilir Hizmet",
                subtitle="Deneyimli psikologlarımızla yanınızdayız.",
                image_url="https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=1200&h=340&fit=crop",
                button_text="Ekibimiz",
                button_link="/terapistler",
                sort_order=2,
            ),
            Slider(
                title="Huzurlu Bir Başlangıç",
                subtitle="Ruh sağlığınız için güvenli ve sakin bir ortamda destek alın.",
                image_url="https://images.unsplash.com/photo-1779838386666-6d110f33079b?w=1200&h=340&fit=crop",
                button_text="Randevu Al",
                button_link="/randevu",
                sort_order=3,
            ),
        ])
        changed = True

    if not Widget.query.filter_by(widget_type="social").first():
        db.session.add(
            Widget(
                widget_type="social",
                title="Bizi Takip Edin",
                content=json.dumps(
                    {
                        "items": [
                            {"platform": "instagram", "url": "https://instagram.com", "label": "Instagram"},
                            {"platform": "facebook", "url": "https://facebook.com", "label": "Facebook"},
                            {"platform": "linkedin", "url": "https://linkedin.com", "label": "LinkedIn"},
                            {"platform": "youtube", "url": "https://youtube.com", "label": "YouTube"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                is_active=True,
                sort_order=0,
            )
        )
        changed = True

    if changed:
        db.session.commit()

    stats_widget = Widget.query.filter_by(widget_type="stats").first()
    stats_content = json.dumps(
        {
            "items": [
                {"value": "15+", "label": "Uzman Psikolog", "color": "blue"},
                {"value": "3000+", "label": "Randevu", "color": "purple"},
                {"value": "20", "label": "Şehir", "color": "green"},
                {"value": "4.9/5", "label": "Memnuniyet", "color": "orange"},
            ]
        },
        ensure_ascii=False,
    )
    if stats_widget and stats_widget.content != stats_content:
        stats_widget.content = stats_content
        changed = True

    faq_content = json.dumps(
        {
            "items": [
                {
                    "q": "PsikoHukuk nedir ve nasıl randevu alabilirim?",
                    "a": "PsikoHukuk, psikolog ve psikiyatrist randevusu alabileceğiniz bir platformdur. Terapistler sayfasından uzman seçin veya randevu sayfasından şehir ve uzmanlık alanına göre arama yapın.",
                },
                {
                    "q": "Platforma nasıl üye olabilirim?",
                    "a": "Randevu oluşturmak için ad, e-posta ve telefon bilgilerinizi girmeniz yeterlidir. İlerleyen dönemde profil oluşturma özelliği eklenecektir.",
                },
                {
                    "q": "Profilimi nasıl oluşturabilirim?",
                    "a": "Terapist profillerini inceleyerek uzmanlık alanları, çalışma saatleri ve iletişim bilgilerine ulaşabilirsiniz. Randevu almak için profil sayfasındaki takvimi kullanın.",
                },
                {
                    "q": "Platformu kullanmak ücretli mi?",
                    "a": "Platform üzerinden randevu oluşturmak ücretsizdir. Seans ücretleri terapistinize göre değişir; detaylar profil sayfasında yer alır.",
                },
                {
                    "q": "Danışanlar nasıl randevu alabilir?",
                    "a": "Terapist seçin, takvimden müsait gün ve saati belirleyin, bilgilerinizi girin ve randevunuzu oluşturun. Online veya yüz yüze seans seçeneğini tercih edebilirsiniz.",
                },
            ]
        },
        ensure_ascii=False,
    )
    faq_widget = Widget.query.filter_by(widget_type="faq").first()
    if faq_widget:
        if faq_widget.content != faq_content:
            faq_widget.content = faq_content
            changed = True
        if faq_widget.title != "Sık Sorulan Sorular":
            faq_widget.title = "Sık Sorulan Sorular"
            changed = True

    ocean_slide_url = "https://images.unsplash.com/photo-1779838386666-6d110f33079b?w=1200&h=340&fit=crop"
    if not Slider.query.filter_by(image_url=ocean_slide_url).first():
        db.session.add(
            Slider(
                title="Huzurlu Bir Başlangıç",
                subtitle="Ruh sağlığınız için güvenli ve sakin bir ortamda destek alın.",
                image_url=ocean_slide_url,
                button_text="Randevu Al",
                button_link="/randevu",
                sort_order=3,
                is_active=True,
            )
        )
        changed = True

    settings = SiteSettings.get()
    if settings.logo_icon == "⚖️":
        settings.logo_icon = "🧠"
        changed = True
    if settings.site_tagline and ("hukuk" in settings.site_tagline.lower() or "avukat" in settings.site_tagline.lower()):
        settings.site_tagline = SITE_TAGLINE
        changed = True
    if settings.site_description and ("hukuk" in settings.site_description.lower() or "avukat" in settings.site_description.lower()):
        settings.site_description = SITE_DESCRIPTION
        changed = True
    if settings.site_keywords and ("#hukuk" in settings.site_keywords.lower() or "#avukat" in settings.site_keywords.lower()):
        settings.site_keywords = SITE_KEYWORDS
        changed = True

    for slide in Slider.query.all():
        text = f"{slide.subtitle or ''} {slide.title or ''}".lower()
        if "avukat" in text or "hukuk alanında" in text:
            if "uzman kadro" in (slide.title or "").lower():
                slide.subtitle = "Deneyimli psikologlarımızla yanınızdayız."
            else:
                slide.subtitle = "Ruh sağlığınız için profesyonel psikolojik destek."
            changed = True

    testimonials_widget = Widget.query.filter_by(widget_type="testimonials").first()
    if testimonials_widget and testimonials_widget.content and "hukuki" in testimonials_widget.content.lower():
        testimonials_widget.content = json.dumps(
            {
                "items": [
                    {"text": "Profesyonel psikolojik destek almak hayatımı kolaylaştırdı.", "author": "M.T."},
                    {"text": "Profesyonel ve güvenilir bir ekip. Kesinlikle tavsiye ederim.", "author": "S.K."},
                ]
            },
            ensure_ascii=False,
        )
        changed = True

    for post in BlogPost.query.filter(BlogPost.category == "Hukuk").all():
        post.is_published = False
        changed = True

    legacy_theme_colors = {
        "#2d6a6a", "#1f4f4f", "#c4846c", "#faf9f7",
        "#e2ab8d", "#fffbfa", "#e5a88d",
    }
    theme_defaults = {
        "primary_color": "#2563eb",
        "primary_dark": "#1d4ed8",
        "accent_color": "#06b6d4",
        "bg_color": "#ffffff",
    }
    for field, value in theme_defaults.items():
        current = getattr(settings, field, None)
        if not current or current in legacy_theme_colors:
            setattr(settings, field, value)
            changed = True
    city_defaults = ["İstanbul", "Ankara", "İzmir"]
    seed_cities = {
        "ayse-yilmaz": "İstanbul",
        "mehmet-kaya": "Ankara",
        "zeynep-demir": "İzmir",
    }
    for slug, city in seed_cities.items():
        therapist = Therapist.query.filter_by(slug=slug).first()
        if therapist and therapist.city != city:
            therapist.city = city
            changed = True
    for index, therapist in enumerate(Therapist.query.order_by(Therapist.id).all()):
        if not therapist.city:
            therapist.city = city_defaults[index % len(city_defaults)]
            changed = True
        if therapist.photo and therapist.photo not in ("default.jpg",) and not therapist.photo.startswith("http"):
            static_path = os.path.join(app.static_folder, therapist.photo)
            if not os.path.isfile(static_path):
                therapist.photo = "default.jpg"
                changed = True
        if not therapist.calendar_token:
            ensure_calendar_token(therapist)
            changed = True
    seed_langs = {
        "ayse-yilmaz": "tr,en",
        "mehmet-kaya": "tr,de",
        "zeynep-demir": "tr,en",
    }
    for slug, langs in seed_langs.items():
        therapist = Therapist.query.filter_by(slug=slug).first()
        if therapist and therapist.languages_spoken in (None, "", "tr"):
            therapist.languages_spoken = langs
            changed = True

    specialty_seeds = {
        "ayse-yilmaz": "Kaygı, Travma, DEHB, Bireysel Terapi",
        "mehmet-kaya": "Çift Terapisi, Aile Danışmanlığı, EMDR",
        "zeynep-demir": "Çocuk, Travma, Kaygı, Ergen",
    }
    for slug, specs in specialty_seeds.items():
        therapist = Therapist.query.filter_by(slug=slug).first()
        if therapist and therapist.specialties != specs:
            therapist.specialties = specs
            changed = True
    for test in PsychologicalTest.query.all():
        if not test.available_langs:
            test.available_langs = "tr,en,de"
            changed = True
    for widget in Widget.query.filter_by(widget_type="hero").all():
        if widget.is_active:
            widget.is_active = False
            changed = True
    if ensure_extra_blog_posts():
        changed = True
    if ensure_blog_featured_images():
        changed = True

    if SessionRecord.query.count() == 0:
        therapists = Therapist.query.filter_by(is_active=True).order_by(Therapist.id).all()
        demo = [
            (["Kaygı", "İş stresi"], "Antalya", "devam", "orta", "online", 50, 7),
            (["Depresif belirtiler"], "Konya", "devam", "yuksek", "yuz_yuze", 60, 3),
            (["Çift terapisi", "İlişki problemi"], "İstanbul", "beklemede", "dusuk", "yuz_yuze", 80, 14),
            (["Kaygı", "Panik atak"], "İstanbul", "devam", "orta", "online", 45, 5),
            (["DEHB", "Çocuk-Ergen"], "Ankara", "sonlandi", "dusuk", "yuz_yuze", 50, None),
            (["Travma", "OKB"], "İzmir", "devam", "yuksek", "yuz_yuze", 60, 2),
            (["Kaygı"], "Antalya", "gelmedi", "orta", "online", 50, 10),
            (["İş stresi", "Tükenmişlik"], "İstanbul", "sonlandi", "dusuk", "yuz_yuze", 50, None),
        ]
        if therapists:
            for index, (reasons, city, status, risk, s_type, duration, next_in) in enumerate(demo):
                t = therapists[index % len(therapists)]
                db.session.add(
                    SessionRecord(
                        therapist_id=t.id,
                        patient_name=f"Demo Danışan {index + 1}",
                        patient_email=f"demo{index + 1}@ornek.com",
                        city=city or t.city,
                        reasons=json_lib.dumps(reasons, ensure_ascii=False),
                        note="Örnek seans kaydı",
                        status=status,
                        risk_level=risk,
                        session_type=s_type,
                        duration_minutes=duration,
                        next_session_date=(date.today() + timedelta(days=next_in)) if next_in else None,
                        created_at=datetime.utcnow() - timedelta(days=index),
                    )
                )
            changed = True

    if changed:
        db.session.commit()


def apply_person_photo(person, file_field, subfolder):
    photo_file = request.files.get(file_field)
    photo_url = request.form.get("photo_url", "").strip()
    if photo_file and photo_file.filename:
        try:
            saved = save_person_photo(photo_file, subfolder)
            if saved:
                person.photo = saved
        except ValueError as exc:
            flash(str(exc), "error")
            return False
    elif photo_url:
        person.photo = photo_url
    return True


with app.app_context():
    migrate_schema()
    seed_database()
    ensure_upgrade_data()
    seed_psychological_tests(db, PsychologicalTest)
    upgrade_psychological_tests(db, PsychologicalTest)


@app.context_processor
def inject_globals():
    settings = get_site_settings()
    lang = get_lang()
    social_widget = Widget.query.filter_by(widget_type="social", is_active=True).first()
    user = get_current_user()
    test_count = PsychologicalTest.query.filter_by(is_active=True).count()

    def can(permission):
        if not user:
            return False
        from auth import user_can_access

        return user_can_access(user, permission, settings.subscription_plan)

    from subscription_plans import format_try, get_active_plan

    active_plan = get_active_plan(settings)

    return {
        "site_name": settings.site_name or SITE_NAME,
        "site_tagline": settings.site_tagline or SITE_TAGLINE,
        "site_description": settings.site_description or SITE_DESCRIPTION,
        "site_keywords": settings.site_keywords or SITE_KEYWORDS,
        "site_settings": settings,
        "social_widget": social_widget,
        "current_year": datetime.now().year,
        "current_lang": lang,
        "languages": SUPPORTED_LANGUAGES,
        "t": lambda key, **kwargs: translate(key, lang, **kwargs),
        "tr": lambda key, **kwargs: translate(key, lang, **kwargs),
        "current_user": user,
        "can": can,
        "active_plan": active_plan,
        "format_try": format_try,
        "static_v": STATIC_VERSION,
        "role_labels": ROLE_LABELS,
        "lang_flags": LANG_FLAGS,
        "country_flag": COUNTRY_FLAG,
        "test_count": test_count,
    }


@app.route("/dil/<lang>")
def set_language(lang):
    if lang in dict(SUPPORTED_LANGUAGES):
        session["lang"] = lang
    return redirect(request.referrer or url_for("home"))


@app.route("/theme.css")
def theme_css():
    settings = get_site_settings()
    css = f""":root {{
  --color-primary: {settings.primary_color};
  --color-primary-dark: {settings.primary_dark};
  --color-accent: {settings.accent_color};
  --color-bg: {settings.bg_color};
}}"""
    return Response(css, mimetype="text/css")


@app.route("/api/takvim/ical/<token>.ics")
def therapist_ical_feed(token):
    therapist = Therapist.query.filter_by(calendar_token=token, is_active=True).first_or_404()
    appointments = Appointment.query.filter_by(therapist_id=therapist.id).order_by(Appointment.appointment_date).all()
    settings = get_site_settings()
    ics = generate_therapist_ics(therapist, appointments, settings.site_name)
    return Response(ics, mimetype="text/calendar", headers={"Content-Disposition": f"inline; filename={therapist.slug}.ics"})


@app.route("/")
def home():
    lang = get_lang()
    slides = Slider.query.filter_by(is_active=True).order_by(Slider.sort_order).all()
    widgets = (
        Widget.query.filter_by(is_active=True)
        .filter(Widget.widget_type != "social")
        .order_by(Widget.sort_order)
        .all()
    )
    therapists = Therapist.query.filter_by(is_active=True).order_by(Therapist.sort_order).limit(3).all()
    posts = BlogPost.query.filter_by(is_published=True).order_by(BlogPost.created_at.desc()).limit(8).all()
    all_tests = PsychologicalTest.query.filter_by(is_active=True).order_by(PsychologicalTest.sort_order).all()
    tests = filter_tests_for_lang(all_tests, lang)
    ctx = seo_context(
        title=SITE_NAME,
        description=SITE_DESCRIPTION,
        keywords=SITE_KEYWORDS,
    )
    return render_template(
        "home.html",
        slides=slides,
        widgets=widgets,
        therapists=therapists,
        posts=posts,
        tests=tests,
        popular_cities=POPULAR_CITIES,
        specialty_filters=SPECIALTY_FILTERS,
        selected_specialties=[],
        info_slides=get_info_slides(lang),
        booking_steps=get_booking_steps(lang),
        all_therapists=Therapist.query.filter_by(is_active=True).order_by(Therapist.name).all(),
        **ctx,
    )


@app.route("/terapistler")
def therapists_list():
    lang = get_lang()
    session_type = normalize_session_type(request.args.get("session_type", "yuz_yuze"))
    city = request.args.get("city", "").strip()
    if session_type == "online":
        city = ""
    q = request.args.get("q", "").strip()
    specialties = parse_specialty_args()
    therapists = filter_therapists(
        city=city or None,
        q=q or None,
        session_type=session_type,
        specialties=specialties,
    )
    ctx = seo_context(
        title=translate("page.therapists_title", lang),
        description=translate("page.therapists_sub", lang),
        keywords="#psikolog #terapist #randevu #psikoloji " + SITE_KEYWORDS,
    )
    return render_template(
        "therapists.html",
        therapists=therapists,
        popular_cities=POPULAR_CITIES,
        selected_city=city,
        search_q=q,
        session_type=session_type,
        specialty_filters=SPECIALTY_FILTERS,
        selected_specialties=specialties,
        therapist_tip=get_therapist_tip(lang),
        **ctx,
    )


@app.route("/api/terapist-ara")
def api_therapist_search():
    q = request.args.get("q", "").strip()
    return jsonify(build_search_suggestions(q))


@app.route("/terapist/<slug>")
def therapist_detail(slug):
    therapist = Therapist.query.filter_by(slug=slug, is_active=True).first_or_404()
    ctx = seo_context(
        title=therapist.name,
        description=therapist.bio[:160],
        keywords=f"#{therapist.slug} #psikolog #terapi {therapist.specialties}",
    )
    return render_template("therapist_detail.html", therapist=therapist, work_hours=WORK_HOURS, **ctx)


@app.route("/randevu")
@app.route("/randevu/<slug>")
def appointment_page(slug=None):
    session_type = normalize_session_type(request.args.get("session_type", "yuz_yuze"))
    city = request.args.get("city", "").strip()
    if session_type == "online":
        city = ""
    q = request.args.get("q", "").strip()
    specialties = parse_specialty_args()
    therapists = filter_therapists(
        city=city or None,
        q=q or None,
        session_type=session_type,
        specialties=specialties,
    )
    selected = Therapist.query.filter_by(slug=slug, is_active=True).first() if slug else None
    ctx = seo_context(
        title="Randevu Takvimi",
        description="Terapist randevu takvimi — müsait gün ve saatleri görüntüleyin, online randevu alın.",
        keywords="#randevu #psikolog #takvim #online",
    )
    return render_template(
        "appointment.html",
        therapists=therapists,
        selected=selected,
        work_hours=WORK_HOURS,
        popular_cities=POPULAR_CITIES,
        selected_city=city,
        search_q=q,
        session_type=session_type,
        specialty_filters=SPECIALTY_FILTERS,
        selected_specialties=specialties,
        **ctx,
    )


@app.route("/api/randevu/musaitlik/<int:therapist_id>")
def api_availability(therapist_id):
    Therapist.query.get_or_404(therapist_id)
    year = request.args.get("year", type=int) or datetime.now().year
    month = request.args.get("month", type=int) or datetime.now().month
    if month < 1 or month > 12:
        abort(400)
    return jsonify(get_month_availability(therapist_id, year, month))


@app.route("/randevu/olustur", methods=["POST"])
def create_appointment():
    therapist_id = request.form.get("therapist_id", type=int)
    patient_name = request.form.get("patient_name", "").strip()
    patient_email = request.form.get("patient_email", "").strip()
    patient_phone = request.form.get("patient_phone", "").strip()
    appointment_date = request.form.get("appointment_date", "")
    appointment_time = request.form.get("appointment_time", "")
    session_type = request.form.get("session_type", "yuz_yuze")
    notes = request.form.get("notes", "").strip()

    if not all([therapist_id, patient_name, patient_email, patient_phone, appointment_date, appointment_time]):
        flash(t("flash.fill_required"), "error")
        return redirect(request.referrer or url_for("appointment_page"))

    therapist = Therapist.query.get_or_404(therapist_id)
    if session_type == "online" and not therapist.supports_online:
        flash(t("flash.online_unavailable"), "error")
        return redirect(url_for("appointment_page", slug=therapist.slug))
    try:
        appt_date = datetime.strptime(appointment_date, "%Y-%m-%d").date()
        appt_time = parse_time_slot(appointment_time)
    except ValueError:
        flash(t("flash.invalid_datetime"), "error")
        return redirect(request.referrer or url_for("appointment_page"))

    if appointment_time not in WORK_HOURS:
        flash(t("flash.invalid_hour"), "error")
        return redirect(request.referrer or url_for("appointment_page", slug=therapist.slug))

    if appt_date.weekday() in (5, 6):
        flash(t("flash.weekend"), "error")
        return redirect(request.referrer or url_for("appointment_page", slug=therapist.slug))

    if is_slot_blocked(therapist.id, appt_date, appt_time):
        flash(t("flash.slot_busy"), "error")
        return redirect(url_for("appointment_page", slug=therapist.slug))

    appointment = Appointment(
        therapist_id=therapist.id,
        patient_name=patient_name,
        patient_email=patient_email,
        patient_phone=patient_phone,
        appointment_date=appt_date,
        appointment_time=appt_time,
        session_type=session_type,
        notes=notes,
        status="beklemede",
    )
    db.session.add(appointment)
    db.session.flush()
    profile, _created = ensure_client_invite(patient_name, patient_email, patient_phone)
    db.session.commit()

    invite_url = None
    if profile and profile.invite_token:
        invite_url = url_for("client_set_password", token=profile.invite_token, _external=True)

    settings = get_site_settings()
    notify_appointment_created(settings, appointment, therapist, settings.site_name, invite_url=invite_url)

    flash(
        t(
            "flash.appointment_created",
            name=therapist.name,
            date=appointment_date,
            time=appointment_time,
        ),
        "success",
    )
    return redirect(url_for("appointment_page", slug=therapist.slug))


@app.route("/blog")
def blog_list():
    page = request.args.get("sayfa", 1, type=int)
    category = request.args.get("kategori", "").strip()
    per_page = 6

    query = BlogPost.query.filter_by(is_published=True)
    if category:
        query = query.filter_by(category=category)

    pagination = query.order_by(BlogPost.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    featured = BlogPost.query.filter_by(is_published=True).order_by(BlogPost.created_at.desc()).first()
    sidebar = get_blog_sidebar_data()

    ctx = seo_context(
        title="Blog",
        description="Psikoloji alanında güncel yazılar, rehberler ve uzman görüşleri.",
        keywords="#blog #psikoloji #terapi #yazilar #hashtag",
        page_type="website",
    )
    return render_template(
        "blog.html",
        posts=pagination.items,
        pagination=pagination,
        featured=featured,
        active_category=category,
        blog_categories=BLOG_CATEGORIES,
        **sidebar,
        **ctx,
    )


@app.route("/blog/etiket/<tag_slug>")
def blog_by_tag(tag_slug):
    page = request.args.get("sayfa", 1, type=int)
    per_page = 6
    all_posts = BlogPost.query.filter_by(is_published=True).order_by(BlogPost.created_at.desc()).all()
    filtered = [post for post in all_posts if tag_slug in [tags_to_slug(t) for t in post.tag_list()]]

    start = (page - 1) * per_page
    end = start + per_page
    posts = filtered[start:end]
    total_pages = max(1, (len(filtered) + per_page - 1) // per_page)
    sidebar = get_blog_sidebar_data()

    ctx = seo_context(
        title=f"#{tag_slug} Etiketi",
        description=f"#{tag_slug} etiketli blog yazıları — PsikoHukuk Danışmanlık Merkezi.",
        keywords=f"#{tag_slug} #blog #psikoloji #terapi",
    )
    return render_template(
        "blog.html",
        posts=posts,
        pagination=None,
        manual_page=page,
        manual_total_pages=total_pages,
        featured=None,
        active_tag=tag_slug,
        blog_categories=BLOG_CATEGORIES,
        **sidebar,
        **ctx,
    )


@app.route("/blog/<slug>")
def blog_detail(slug):
    post = BlogPost.query.filter_by(slug=slug, is_published=True).first_or_404()
    related = (
        BlogPost.query.filter(BlogPost.id != post.id, BlogPost.is_published.is_(True), BlogPost.category == post.category)
        .order_by(BlogPost.created_at.desc())
        .limit(3)
        .all()
    )
    sidebar = get_blog_sidebar_data()
    ctx = seo_context(
        title=post.seo_title or post.title,
        description=post.seo_description or post.excerpt,
        keywords=post.keyword_list() or post.tags or SITE_KEYWORDS,
        image=post.featured_image,
        page_type="article",
    )
    return render_template("blog_detail.html", post=post, related=related, **sidebar, **ctx)


@app.route("/hakkimizda")
def about():
    ctx = seo_context(
        title="Hakkımızda",
        description="PsikoHukuk Danışmanlık Merkezi hakkında — misyon, vizyon ve uzman kadromuz.",
        keywords="#hakkimizda #psikohukuk #danışmanlık",
    )
    return render_template("about.html", **ctx)


@app.route("/iletisim")
def contact():
    ctx = seo_context(
        title="İletişim",
        description="PsikoHukuk Danışmanlık Merkezi iletişim bilgileri ve mesaj formu.",
        keywords="#iletisim #istanbul #danışmanlık",
    )
    return render_template("contact.html", **ctx)


@app.route("/fiyatlandirma")
def pricing_page():
    from pricing_public import build_pricing_page_context

    lang = get_lang()
    ctx = seo_context(
        title=translate("pricing.title", lang),
        description=translate("pricing.subtitle", lang),
        keywords="#fiyatlandirma #klinik yazılım #psikoloji platform",
    )
    return render_template("pricing.html", **build_pricing_page_context(), **ctx)


@app.route("/testler")
def tests_list():
    lang = get_lang()
    all_tests = PsychologicalTest.query.filter_by(is_active=True).order_by(PsychologicalTest.sort_order).all()
    tests = filter_tests_for_lang(all_tests, lang)
    ctx = seo_context(
        title=translate("tests.title", lang),
        description=translate("tests.subtitle", lang),
        keywords="#psikolojiktest #ucretsiztest #kisiliktesti #kaygitesti #dehb #depresyon",
    )
    return render_template(
        "tests/list.html",
        tests=tests,
        test_groups=get_test_groups(lang),
        testimonials=TESTIMONIALS,
        **ctx,
    )


@app.route("/testler/<slug>")
def test_landing(slug):
    test = PsychologicalTest.query.filter_by(slug=slug, is_active=True).first_or_404()
    if not test.supports_lang(get_lang()):
        abort(404)
    ctx = seo_context(
        title=test.display_seo_title(),
        description=test.seo_description or test.hero_subtitle or test.description,
        keywords=test.seo_keywords or f"#{test.slug} #ucretsiztest",
    )
    return render_template(
        "tests/landing.html",
        test=test,
        testimonials=TESTIMONIALS,
        **ctx,
    )


@app.route("/testler/<slug>/coz")
def test_take(slug):
    test = PsychologicalTest.query.filter_by(slug=slug, is_active=True).first_or_404()
    if not test.supports_lang(get_lang()):
        abort(404)
    ctx = seo_context(
        title=f"{test.hero_title or test.title} — Sorular",
        description=test.description,
        keywords=test.seo_keywords or f"#{test.slug} #psikolojiktest",
    )
    return render_template("tests/take.html", test=test, **ctx)


@app.route("/testler/<slug>/sonuc", methods=["POST"])
def test_result(slug):
    test = PsychologicalTest.query.filter_by(slug=slug, is_active=True).first_or_404()
    answers = {key.replace("q_", ""): value for key, value in request.form.items() if key.startswith("q_")}
    if len(answers) < len(test.question_list()):
        flash("Lütfen tüm soruları yanıtlayın.", "error")
        return redirect(url_for("test_take", slug=slug))

    result = score_test(test, answers)
    recommended = get_recommended_therapists(test, result)

    current = get_current_user()
    email = ""
    name = ""
    user_id = None
    if current and current.role == "client":
        user_id = current.id
        email = current.client_profile.email if current.client_profile else current.username
        name = current.client_profile.full_name if current.client_profile else current.username
    try:
        stored = TestResult(
            test_id=test.id,
            user_id=user_id,
            patient_email=email,
            patient_name=name,
            score=float(result.get("score") or 0),
            level=str(result.get("level") or result.get("label") or ""),
            summary=str(result.get("summary") or ""),
            result_json=json_lib.dumps(result, ensure_ascii=False),
        )
        db.session.add(stored)
        db.session.commit()
    except Exception:
        db.session.rollback()

    ctx = seo_context(title=f"{test.title} — Sonuç", description=result.get("summary", ""))
    return render_template(
        "tests/result.html",
        test=test,
        result=result,
        recommended_therapists=recommended,
        **ctx,
    )


# ── Admin ──────────────────────────────────────────────────────────────────

@app.route("/admin/giris", methods=["GET", "POST"])
def admin_login():
    current = get_current_user()
    if current and current.role != "client":
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username, is_active=True).first()
        if user and user.role != "client" and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Hoş geldiniz!", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Kullanıcı adı veya şifre hatalı.", "error")

    return render_template("admin/login.html")


@app.route("/admin/cikis")
def admin_logout():
    logout_user()
    flash("Çıkış yapıldı.", "info")
    return redirect(url_for("admin_login"))


@app.route("/admin")
@permission_required("dashboard")
def admin_dashboard():
    user = get_current_user()
    appointment_query = Appointment.query
    if user.role == "therapist" and user.therapist_id:
        appointment_query = appointment_query.filter_by(therapist_id=user.therapist_id)

    stats = {
        "therapists": Therapist.query.count() if user.role == "admin" else None,
        "appointments": appointment_query.count(),
        "pending": appointment_query.filter_by(status="beklemede").count(),
        "posts": BlogPost.query.count() if user.role in ("admin", "editor") else None,
        "widgets": Widget.query.count() if user.role in ("admin", "editor") else None,
        "slides": Slider.query.count() if user.role in ("admin", "editor") else None,
    }
    chart_stats = appointment_chart_stats(appointment_query)
    recent_appointments = appointment_query.order_by(Appointment.created_at.desc()).limit(5).all()
    visitor_stats = get_visitor_stats() if user.role == "admin" else None
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        chart_stats=chart_stats,
        visitor_stats=visitor_stats,
        recent_appointments=recent_appointments,
        user=user,
    )


@app.route("/admin/terapistler")
@permission_required("therapists")
def admin_therapists():
    therapists = Therapist.query.order_by(Therapist.sort_order).all()
    return render_template("admin/therapists.html", therapists=therapists)


@app.route("/admin/terapist/ekle", methods=["GET", "POST"])
@permission_required("therapists")
def admin_therapist_add():
    if request.method == "POST":
        therapist = Therapist(
            name=request.form["name"],
            title=request.form["title"],
            slug=request.form["slug"],
            bio=request.form["bio"],
            specialties=request.form["specialties"],
            email=request.form["email"],
            phone=request.form["phone"],
            city=request.form.get("city", "İstanbul"),
            languages_spoken=parse_lang_codes(request.form),
            supports_online="supports_online" in request.form,
            ical_import_url=request.form.get("ical_import_url", ""),
            is_active="is_active" in request.form,
            sort_order=request.form.get("sort_order", 0, type=int),
        )
        if not apply_person_photo(therapist, "photo_file", "therapists"):
            return render_template("admin/therapist_form.html", therapist=None, popular_cities=POPULAR_CITIES)
        ensure_calendar_token(therapist)
        db.session.add(therapist)
        db.session.commit()
        flash("Terapist eklendi.", "success")
        return redirect(url_for("admin_therapists"))
    return render_template("admin/therapist_form.html", therapist=None, popular_cities=POPULAR_CITIES)


@app.route("/admin/terapist/<int:id>/duzenle", methods=["GET", "POST"])
@permission_required("therapists")
def admin_therapist_edit(id):
    therapist = Therapist.query.get_or_404(id)
    if request.method == "POST":
        therapist.name = request.form["name"]
        therapist.title = request.form["title"]
        therapist.slug = request.form["slug"]
        therapist.bio = request.form["bio"]
        therapist.specialties = request.form["specialties"]
        therapist.email = request.form["email"]
        therapist.phone = request.form["phone"]
        therapist.city = request.form.get("city", therapist.city or "İstanbul")
        therapist.languages_spoken = parse_lang_codes(request.form, default=therapist.languages_spoken or "tr")
        therapist.supports_online = "supports_online" in request.form
        therapist.ical_import_url = request.form.get("ical_import_url", "")
        therapist.is_active = "is_active" in request.form
        therapist.sort_order = request.form.get("sort_order", 0, type=int)
        if not apply_person_photo(therapist, "photo_file", "therapists"):
            return render_template("admin/therapist_form.html", therapist=therapist, popular_cities=POPULAR_CITIES)
        ensure_calendar_token(therapist)
        db.session.commit()
        flash("Terapist güncellendi.", "success")
        return redirect(url_for("admin_therapists"))
    return render_template("admin/therapist_form.html", therapist=therapist, popular_cities=POPULAR_CITIES)


@app.route("/admin/terapist/<int:id>/sil", methods=["POST"])
@permission_required("therapists")
def admin_therapist_delete(id):
    therapist = Therapist.query.get_or_404(id)
    db.session.delete(therapist)
    db.session.commit()
    flash("Terapist silindi.", "info")
    return redirect(url_for("admin_therapists"))


@app.route("/admin/slider")
@permission_required("sliders")
def admin_sliders():
    slides = Slider.query.order_by(Slider.sort_order).all()
    return render_template("admin/sliders.html", slides=slides)


@app.route("/admin/slider/ekle", methods=["GET", "POST"])
@permission_required("sliders")
def admin_slider_add():
    if request.method == "POST":
        slide = Slider(
            title=request.form["title"],
            subtitle=request.form.get("subtitle", ""),
            image_url=request.form.get("image_url", ""),
            button_text=request.form.get("button_text", ""),
            button_link=request.form.get("button_link", ""),
            is_active="is_active" in request.form,
            sort_order=request.form.get("sort_order", 0, type=int),
        )
        db.session.add(slide)
        db.session.commit()
        flash("Slider eklendi.", "success")
        return redirect(url_for("admin_sliders"))
    return render_template("admin/slider_form.html", slide=None)


@app.route("/admin/slider/<int:id>/duzenle", methods=["GET", "POST"])
@permission_required("sliders")
def admin_slider_edit(id):
    slide = Slider.query.get_or_404(id)
    if request.method == "POST":
        slide.title = request.form["title"]
        slide.subtitle = request.form.get("subtitle", "")
        slide.image_url = request.form.get("image_url", "")
        slide.button_text = request.form.get("button_text", "")
        slide.button_link = request.form.get("button_link", "")
        slide.is_active = "is_active" in request.form
        slide.sort_order = request.form.get("sort_order", 0, type=int)
        db.session.commit()
        flash("Slider güncellendi.", "success")
        return redirect(url_for("admin_sliders"))
    return render_template("admin/slider_form.html", slide=slide)


@app.route("/admin/slider/<int:id>/sil", methods=["POST"])
@permission_required("sliders")
def admin_slider_delete(id):
    slide = Slider.query.get_or_404(id)
    db.session.delete(slide)
    db.session.commit()
    flash("Slider silindi.", "info")
    return redirect(url_for("admin_sliders"))


@app.route("/admin/randevular")
@permission_required("appointments")
def admin_appointments():
    user = get_current_user()
    status_filter = request.args.get("status", "")
    therapist_filter = request.args.get("therapist_id", type=int)
    search = (request.args.get("q") or "").strip()
    date_from = (request.args.get("from") or "").strip()
    date_to = (request.args.get("to") or "").strip()
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = 25

    scope = Appointment.query
    if user.role == "therapist" and user.therapist_id:
        scope = scope.filter_by(therapist_id=user.therapist_id)
        therapist_filter = user.therapist_id
    elif therapist_filter:
        scope = scope.filter_by(therapist_id=therapist_filter)

    if search:
        like = f"%{search}%"
        scope = scope.filter(
            db.or_(
                Appointment.patient_name.ilike(like),
                Appointment.patient_email.ilike(like),
                Appointment.patient_phone.ilike(like),
            )
        )

    def _parse_date(value):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None

    parsed_from = _parse_date(date_from) if date_from else None
    parsed_to = _parse_date(date_to) if date_to else None
    if parsed_from:
        scope = scope.filter(Appointment.appointment_date >= parsed_from)
    if parsed_to:
        scope = scope.filter(Appointment.appointment_date <= parsed_to)

    status_counts = {
        key: scope.filter(Appointment.status == key).count()
        for key in Appointment.STATUS_LABELS
    }
    total_all = sum(status_counts.values())

    query = scope.filter_by(status=status_filter) if status_filter else scope
    total = query.count()
    pages = max((total + per_page - 1) // per_page, 1)
    page = min(page, pages)
    appointments = (
        query.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    emails = {(a.patient_email or "").lower() for a in appointments if a.patient_email}
    member_emails = set()
    if emails:
        member_emails = {
            (p.email or "").lower()
            for p in ClientProfile.query.filter(ClientProfile.email.in_(emails)).all()
        }

    therapists = Therapist.query.order_by(Therapist.name).all()
    return render_template(
        "admin/appointments.html",
        appointments=appointments,
        therapists=therapists,
        status_filter=status_filter,
        therapist_filter=therapist_filter,
        search=search,
        date_from=date_from,
        date_to=date_to,
        status_counts=status_counts,
        total_all=total_all,
        total=total,
        page=page,
        pages=pages,
        per_page=per_page,
        member_emails=member_emails,
        today=date.today(),
        status_labels=Appointment.STATUS_LABELS,
        is_therapist_view=user.role == "therapist",
    )


@app.route("/admin/randevu/<int:id>/durum", methods=["POST"])
@permission_required("appointments")
def admin_appointment_status(id):
    user = get_current_user()
    appointment = Appointment.query.get_or_404(id)
    if not therapist_appointment_scope(user, appointment):
        abort(403)
    new_status = request.form.get("status", appointment.status)
    if new_status == "onaylandi":
        conflict = (
            Appointment.query.filter(
                Appointment.id != appointment.id,
                Appointment.therapist_id == appointment.therapist_id,
                Appointment.appointment_date == appointment.appointment_date,
                Appointment.appointment_time == appointment.appointment_time,
                Appointment.status.in_(("onaylandi", "beklemede")),
            ).first()
        )
        if conflict:
            flash(t("flash.appointment_conflict"), "error")
            return redirect(url_for("admin_appointments"))
    old_status = appointment.status
    appointment.status = new_status
    log_audit(
        user,
        "status_change",
        "appointment",
        appointment.id,
        {"from": old_status, "to": new_status, "patient": appointment.patient_name},
    )
    db.session.commit()
    if old_status != "onaylandi" and new_status == "onaylandi":
        settings = get_site_settings()
        notify_appointment_confirmed(settings, appointment, appointment.therapist, settings.site_name)
    flash(t("flash.appointment_status"), "success")
    return redirect(url_for("admin_appointments"))


@app.route("/admin/randevu/<int:id>/sil", methods=["POST"])
@permission_required("appointments")
def admin_appointment_delete(id):
    user = get_current_user()
    appointment = Appointment.query.get_or_404(id)
    if not therapist_appointment_scope(user, appointment):
        abort(403)
    db.session.delete(appointment)
    db.session.commit()
    flash("Randevu silindi.", "info")
    return redirect(url_for("admin_appointments"))


@app.route("/admin/blog")
@permission_required("blog")
def admin_blog():
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    status_filter = (request.args.get("status") or "").strip()
    search = (request.args.get("q") or "").strip().lower()
    filtered = posts
    if status_filter == "published":
        filtered = [p for p in filtered if p.is_published]
    elif status_filter == "draft":
        filtered = [p for p in filtered if not p.is_published]
    if search:
        filtered = [
            p for p in filtered
            if search in (p.title or "").lower()
            or search in (p.author or "").lower()
            or search in (p.tags or "").lower()
            or search in (p.category or "").lower()
        ]
    return render_template(
        "admin/blog.html",
        posts=posts,
        filtered=filtered,
        status_filter=status_filter,
        search=request.args.get("q") or "",
    )


@app.route("/admin/blog/ekle", methods=["GET", "POST"])
@permission_required("blog")
def admin_blog_add():
    if request.method == "POST":
        post = BlogPost(
            title=request.form["title"],
            slug=request.form["slug"],
            excerpt=request.form["excerpt"],
            content=request.form["content"],
            author=request.form["author"],
            category=request.form.get("category", "Genel"),
            tags=request.form.get("tags", ""),
            seo_title=request.form.get("seo_title", ""),
            seo_description=request.form.get("seo_description", ""),
            seo_keywords=request.form.get("seo_keywords", ""),
            featured_image=request.form.get("featured_image", ""),
            is_published="is_published" in request.form,
        )
        db.session.add(post)
        db.session.commit()
        flash("Yazı eklendi.", "success")
        return redirect(url_for("admin_blog"))
    return render_template("admin/blog_form.html", post=None, blog_categories=BLOG_CATEGORIES)


@app.route("/admin/blog/<int:id>/duzenle", methods=["GET", "POST"])
@permission_required("blog")
def admin_blog_edit(id):
    post = BlogPost.query.get_or_404(id)
    if request.method == "POST":
        post.title = request.form["title"]
        post.slug = request.form["slug"]
        post.excerpt = request.form["excerpt"]
        post.content = request.form["content"]
        post.author = request.form["author"]
        post.category = request.form.get("category", "Genel")
        post.tags = request.form.get("tags", "")
        post.seo_title = request.form.get("seo_title", "")
        post.seo_description = request.form.get("seo_description", "")
        post.seo_keywords = request.form.get("seo_keywords", "")
        post.featured_image = request.form.get("featured_image", "")
        post.is_published = "is_published" in request.form
        db.session.commit()
        flash("Yazı güncellendi.", "success")
        return redirect(url_for("admin_blog"))
    return render_template("admin/blog_form.html", post=post, blog_categories=BLOG_CATEGORIES)


@app.route("/admin/blog/<int:id>/sil", methods=["POST"])
@permission_required("blog")
def admin_blog_delete(id):
    post = BlogPost.query.get_or_404(id)
    db.session.delete(post)
    db.session.commit()
    flash("Yazı silindi.", "info")
    return redirect(url_for("admin_blog"))


@app.route("/admin/widgetlar")
@permission_required("widgets")
def admin_widgets():
    widgets = Widget.query.order_by(Widget.sort_order).all()
    return render_template("admin/widgets.html", widgets=widgets, widget_types=WIDGET_TYPES)


@app.route("/admin/widget/ekle", methods=["GET", "POST"])
@permission_required("widgets")
def admin_widget_add():
    if request.method == "POST":
        widget = Widget(
            widget_type=request.form["widget_type"],
            title=request.form["title"],
            content=request.form["content"],
            is_active="is_active" in request.form,
            sort_order=request.form.get("sort_order", 0, type=int),
        )
        db.session.add(widget)
        db.session.commit()
        flash("Widget eklendi.", "success")
        return redirect(url_for("admin_widgets"))
    return render_template("admin/widget_form.html", widget=None, widget_types=WIDGET_TYPES)


@app.route("/admin/widget/<int:id>/duzenle", methods=["GET", "POST"])
@permission_required("widgets")
def admin_widget_edit(id):
    widget = Widget.query.get_or_404(id)
    if request.method == "POST":
        widget.widget_type = request.form["widget_type"]
        widget.title = request.form["title"]
        widget.content = request.form["content"]
        widget.is_active = "is_active" in request.form
        widget.sort_order = request.form.get("sort_order", 0, type=int)
        db.session.commit()
        flash("Widget güncellendi.", "success")
        return redirect(url_for("admin_widgets"))
    return render_template("admin/widget_form.html", widget=widget, widget_types=WIDGET_TYPES)


@app.route("/admin/widget/<int:id>/sil", methods=["POST"])
@permission_required("widgets")
def admin_widget_delete(id):
    widget = Widget.query.get_or_404(id)
    db.session.delete(widget)
    db.session.commit()
    flash("Widget silindi.", "info")
    return redirect(url_for("admin_widgets"))


@app.route("/admin/widget/<int:id>/toggle", methods=["POST"])
@permission_required("widgets")
def admin_widget_toggle(id):
    widget = Widget.query.get_or_404(id)
    widget.is_active = not widget.is_active
    db.session.commit()
    return redirect(url_for("admin_widgets"))


@app.route("/admin/abonelik", methods=["GET", "POST"])
@login_required
def admin_subscription():
    user = get_current_user()
    if user.role != "admin":
        flash("Abonelik paketini yalnızca klinik yöneticisi değiştirebilir.", "error")
        return redirect(url_for("admin_dashboard"))

    from subscription_plans import PLAN_IDS, PLANS, MODULE_LABELS, format_try, get_active_plan

    settings = get_site_settings()
    if request.method == "POST":
        plan_id = (request.form.get("plan_id") or "enterprise").strip().lower()
        if plan_id in PLAN_IDS:
            settings.subscription_plan = plan_id
            db.session.commit()
            flash(f"Abonelik paketi «{PLANS[plan_id]['label']}» olarak güncellendi.", "success")
        else:
            flash("Geçersiz paket seçimi.", "error")
        return redirect(url_for("admin_subscription"))

    plans = []
    for pid in PLAN_IDS:
        p = dict(PLANS[pid])
        p["setup_display"] = format_try(p["setup_price"])
        p["monthly_display"] = format_try(p["monthly_price"])
        p["modules_sorted"] = sorted(p["modules"], key=lambda m: MODULE_LABELS.get(m, m))
        plans.append(p)

    return render_template(
        "admin/subscription.html",
        plans=plans,
        current_plan_id=settings.subscription_plan or "enterprise",
        active_plan=get_active_plan(settings),
        module_labels=MODULE_LABELS,
    )


@app.route("/admin/ticari")
@login_required
def admin_commercial_profile():
    user = get_current_user()
    if user.role != "admin":
        flash("Bu sayfaya erişim yetkiniz yok.", "error")
        return redirect(url_for("admin_dashboard"))

    from commercial_profile import company_display

    return render_template("admin/commercial_profile.html", company=company_display())


@app.route("/admin/ticari/<doc>")
@login_required
def admin_commercial_doc(doc):
    user = get_current_user()
    if user.role != "admin":
        flash("Bu dokümana erişim yetkiniz yok.", "error")
        return redirect(url_for("admin_dashboard"))

    from commercial_docs import build_contract_context, build_quote_context

    overrides = {}
    if request.args.get("plan"):
        overrides["plan_id"] = request.args.get("plan")
    if request.args.get("musteri"):
        overrides["customer_name"] = request.args.get("musteri")

    quote_date = datetime.now().strftime("%d.%m.%Y")

    if doc == "teklif":
        ctx = build_quote_context(overrides)
        ctx["quote_date"] = quote_date
        return render_template("commercial/teklif.html", **ctx)

    if doc in ("sozlesme", "teklif-md"):
        ctx = build_contract_context(overrides)
        ctx["quote_date"] = quote_date
        body = render_template("commercial/sozlesme.md", **ctx)
        return Response(body, mimetype="text/plain; charset=utf-8")

    flash("Doküman bulunamadı.", "error")
    return redirect(url_for("admin_commercial_profile"))


@app.route("/admin/tema", methods=["GET", "POST"])
@permission_required("theme")
def admin_theme():
    settings = get_site_settings()
    if request.method == "POST":
        settings.logo_url = request.form.get("logo_url", "")
        settings.logo_icon = request.form.get("logo_icon", "⚖️")
        settings.site_name = request.form.get("site_name", settings.site_name)
        settings.site_tagline = request.form.get("site_tagline", "")
        settings.site_description = request.form.get("site_description", "")
        settings.site_keywords = request.form.get("site_keywords", "")
        settings.primary_color = request.form.get("primary_color", settings.primary_color)
        settings.primary_dark = request.form.get("primary_dark", settings.primary_dark)
        settings.accent_color = request.form.get("accent_color", settings.accent_color)
        settings.bg_color = request.form.get("bg_color", settings.bg_color)
        db.session.commit()
        flash("Tema ayarları kaydedildi.", "success")
        return redirect(url_for("admin_theme"))
    return render_template("admin/theme.html", settings=settings)


@app.route("/admin/eposta", methods=["GET", "POST"])
@permission_required("email")
def admin_email_settings():
    settings = get_site_settings()
    if request.method == "POST":
        settings.email_enabled = "email_enabled" in request.form
        settings.smtp_host = request.form.get("smtp_host", "")
        settings.smtp_port = request.form.get("smtp_port", 587, type=int)
        settings.smtp_user = request.form.get("smtp_user", "")
        settings.smtp_password = request.form.get("smtp_password", "")
        settings.smtp_from = request.form.get("smtp_from", "")
        settings.admin_email = request.form.get("admin_email", "")
        db.session.commit()
        flash("E-posta ayarları kaydedildi.", "success")
        return redirect(url_for("admin_email_settings"))
    return render_template("admin/email_settings.html", settings=settings)


@app.route("/admin/testler")
@permission_required("tests")
def admin_tests():
    tests = PsychologicalTest.query.order_by(PsychologicalTest.sort_order).all()
    return render_template("admin/tests.html", tests=tests)


@app.route("/admin/test/<int:id>/toggle", methods=["POST"])
@permission_required("tests")
def admin_test_toggle(id):
    test = PsychologicalTest.query.get_or_404(id)
    test.is_active = not test.is_active
    db.session.commit()
    flash("Test durumu güncellendi.", "success")
    return redirect(url_for("admin_tests"))


@app.route("/admin/test/<int:id>/duzenle", methods=["GET", "POST"])
@permission_required("tests")
def admin_test_edit(id):
    test = PsychologicalTest.query.get_or_404(id)
    if request.method == "POST":
        test.seo_title = request.form.get("seo_title", "")
        test.seo_description = request.form.get("seo_description", "")
        test.seo_keywords = request.form.get("seo_keywords", "")
        langs = request.form.getlist("available_langs")
        test.available_langs = ",".join(langs) if langs else "tr"
        db.session.commit()
        flash("Test ayarları güncellendi.", "success")
        return redirect(url_for("admin_tests"))
    return render_template("admin/test_form.html", test=test)


def _validate_user_form(user=None):
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "editor")
    therapist_id = request.form.get("therapist_id", type=int)
    is_active = "is_active" in request.form

    if not username:
        flash("Kullanıcı adı zorunludur.", "error")
        return None

    existing = User.query.filter_by(username=username).first()
    if existing and (not user or existing.id != user.id):
        flash("Bu kullanıcı adı zaten kullanılıyor.", "error")
        return None

    if role not in STAFF_ROLES:
        flash("Geçersiz rol seçildi.", "error")
        return None

    if role == "therapist":
        if not therapist_id:
            flash("Terapist rolü için bir terapist seçmelisiniz.", "error")
            return None
        therapist = Therapist.query.get(therapist_id)
        if not therapist:
            flash("Seçilen terapist bulunamadı.", "error")
            return None
        linked = User.query.filter_by(therapist_id=therapist_id, role="therapist").first()
        if linked and (not user or linked.id != user.id):
            flash("Bu terapist için zaten bir giriş hesabı var.", "error")
            return None
    else:
        therapist_id = None

    if not user and not password:
        flash("Yeni kullanıcı için şifre zorunludur.", "error")
        return None

    return {
        "username": username,
        "password": password,
        "role": role,
        "therapist_id": therapist_id,
        "is_active": is_active,
    }


@app.route("/admin/kullanicilar")
@permission_required("users")
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    tab = request.args.get("tab", "clients")
    if tab not in ("clients", "therapists", "staff"):
        tab = "clients"

    clients = [u for u in users if u.role == "client"]
    therapists = [u for u in users if u.role == "therapist"]
    staff = [u for u in users if u.role in ("admin", "editor")]

    return render_template(
        "admin/users.html",
        tab=tab,
        clients=clients,
        therapist_users=therapists,
        staff_users=staff,
        counts={
            "clients": len(clients),
            "therapists": len(therapists),
            "staff": len(staff),
        },
    )


@app.route("/admin/kullanici/ekle", methods=["GET", "POST"])
@permission_required("users")
def admin_user_add():
    therapists = Therapist.query.order_by(Therapist.name).all()
    if request.method == "POST":
        data = _validate_user_form()
        if not data:
            return render_template("admin/user_form.html", user=None, therapists=therapists, roles=STAFF_ROLES)

        user = User(
            username=data["username"],
            password_hash=generate_password_hash(data["password"], method="pbkdf2:sha256"),
            role=data["role"],
            therapist_id=data["therapist_id"],
            is_active=data["is_active"],
        )
        db.session.add(user)
        db.session.commit()
        flash("Kullanıcı eklendi.", "success")
        return redirect(url_for("admin_users", tab=_users_tab_for_role(user.role)))
    return render_template("admin/user_form.html", user=None, therapists=therapists, roles=STAFF_ROLES)


@app.route("/admin/kullanici/<int:id>/duzenle", methods=["GET", "POST"])
@permission_required("users")
def admin_user_edit(id):
    user = User.query.get_or_404(id)
    therapists = Therapist.query.order_by(Therapist.name).all()
    if request.method == "POST":
        data = _validate_user_form(user)
        if not data:
            return render_template("admin/user_form.html", user=user, therapists=therapists, roles=STAFF_ROLES)

        user.username = data["username"]
        user.role = data["role"]
        user.therapist_id = data["therapist_id"]
        user.is_active = data["is_active"]
        if data["password"]:
            user.password_hash = generate_password_hash(data["password"], method="pbkdf2:sha256")

        if user.id == get_current_user().id and not user.is_active:
            flash("Kendi hesabınızı devre dışı bırakamazsınız.", "error")
            return render_template("admin/user_form.html", user=user, therapists=therapists, roles=STAFF_ROLES)

        db.session.commit()
        flash("Kullanıcı güncellendi.", "success")
        return redirect(url_for("admin_users", tab=_users_tab_for_role(user.role)))
    return render_template("admin/user_form.html", user=user, therapists=therapists, roles=STAFF_ROLES)


@app.route("/admin/kullanici/<int:id>/sil", methods=["POST"])
@permission_required("users")
def admin_user_delete(id):
    user = User.query.get_or_404(id)
    current = get_current_user()
    tab = _users_tab_for_role(user.role)

    if user.id == current.id:
        flash("Kendi hesabınızı silemezsiniz.", "error")
        return redirect(url_for("admin_users", tab=tab))

    if user.role == "admin" and User.query.filter_by(role="admin", is_active=True).count() <= 1:
        flash("Son aktif admin hesabı silinemez.", "error")
        return redirect(url_for("admin_users", tab=tab))

    db.session.delete(user)
    db.session.commit()
    flash("Kullanıcı silindi.", "info")
    return redirect(url_for("admin_users", tab=tab))


def _users_tab_for_role(role):
    if role == "client":
        return "clients"
    if role == "therapist":
        return "therapists"
    return "staff"


register_extra_routes(app)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
