from i18n import translate

LANG_FLAGS = {"tr": "🇹🇷", "en": "🇬🇧", "de": "🇩🇪"}
COUNTRY_FLAG = "🇹🇷"

POPULAR_CITIES = [
    "İstanbul", "Ankara", "İzmir", "Bursa", "Antalya", "Adana", "Konya",
    "Gaziantep", "Mersin", "Kocaeli", "Eskişehir", "Samsun", "Trabzon",
    "Kayseri", "Diyarbakır", "Muğla", "Balıkesir", "Tekirdağ", "Denizli", "Şanlıurfa",
]

STAT_COLORS = ["blue", "purple", "green", "orange"]


def get_test_groups(lang="tr"):
    return [
        {"id": "all", "label": translate("tests.group.all", lang), "icon": "▦"},
        {"id": "mood", "label": translate("tests.group.mood", lang)},
        {"id": "anxiety", "label": translate("tests.group.anxiety", lang)},
        {"id": "relationships", "label": translate("tests.group.relationships", lang)},
        {"id": "personality", "label": translate("tests.group.personality", lang)},
        {"id": "focus", "label": translate("tests.group.focus", lang)},
        {"id": "clinical", "label": translate("tests.group.clinical", lang)},
    ]


def get_info_slides(lang="tr"):
    return [
        {"title": translate("content.info.1.title", lang), "text": translate("content.info.1.text", lang)},
        {"title": translate("content.info.2.title", lang), "text": translate("content.info.2.text", lang)},
        {"title": translate("content.info.3.title", lang), "text": translate("content.info.3.text", lang)},
        {"title": translate("content.info.4.title", lang), "text": translate("content.info.4.text", lang)},
        {"title": translate("content.info.5.title", lang), "text": translate("content.info.5.text", lang)},
    ]


def get_booking_steps(lang="tr"):
    return [
        {
            "icon": "🔍",
            "title": translate("content.step.1.title", lang),
            "text": translate("content.step.1.text", lang),
            "color": "#2563eb",
        },
        {
            "icon": "📅",
            "title": translate("content.step.2.title", lang),
            "text": translate("content.step.2.text", lang),
            "color": "#7c3aed",
        },
        {
            "icon": "💬",
            "title": translate("content.step.3.title", lang),
            "text": translate("content.step.3.text", lang),
            "color": "#0891b2",
        },
    ]


def get_therapist_tip(lang="tr"):
    return {
        "title": translate("therapist.tip.title", lang),
        "text": translate("therapist.tip.text", lang),
    }


def get_stats_items(lang="tr"):
    return [
        {"value": "15+", "label": translate("stats.years", lang), "color": "blue"},
        {"value": "3000+", "label": translate("stats.clients", lang), "color": "purple"},
        {"value": "20", "label": translate("stats.cities", lang), "color": "green"},
        {"value": "98%", "label": translate("stats.satisfaction", lang), "color": "orange"},
    ]
