LEVEL_MATCH_TAGS = {
    "risk": ["Bireysel Terapi", "Kaygı", "Travma"],
    "moderate": ["Bireysel Terapi", "Kişisel Gelişim"],
    "low": ["Kişisel Gelişim", "Bireysel Terapi"],
    "info": ["Kişisel Gelişim", "Bireysel Terapi"],
}


def _normalize(text):
    return text.lower().replace("ı", "i").replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ö", "o").replace("ç", "c")


def _score_therapist(therapist, tags):
    specialties = _normalize(therapist.specialties or "")
    title = _normalize(therapist.title or "")
    score = 0
    matched = []
    for tag in tags:
        normalized = _normalize(tag)
        if normalized in specialties or normalized in title:
            score += 3
            matched.append(tag)
            continue
        for part in normalized.split():
            if len(part) > 3 and part in specialties:
                score += 1
                matched.append(tag)
                break
    return score, matched


def get_recommended_therapists(test, result, limit=3):
    from models import Therapist

    tags = set(test.match_tag_list())
    level = result.get("level", "info")
    for tag in result.get("match_tags", []):
        tags.add(tag)
    for tag in LEVEL_MATCH_TAGS.get(level, []):
        tags.add(tag)

    therapists = Therapist.query.filter_by(is_active=True).order_by(Therapist.sort_order).all()
    ranked = []
    for therapist in therapists:
        score, matched = _score_therapist(therapist, tags)
        if score > 0:
            ranked.append((score, therapist, matched))

    ranked.sort(key=lambda item: (-item[0], item[1].sort_order, item[1].name))
    return [
        {"therapist": therapist, "matched_tags": matched, "score": score}
        for score, therapist, matched in ranked[:limit]
    ]
