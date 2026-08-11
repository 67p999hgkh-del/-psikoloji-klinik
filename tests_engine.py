DIMENSION_LABELS = {
    "extraversion": "Dışadönüklük",
    "agreeableness": "Uyumluluk",
    "conscientiousness": "Sorumluluk",
    "neuroticism": "Duygusal Denge",
    "openness": "Deneyime Açıklık",
}


def score_test(test, answers):
    scoring_type = test.scoring_type
    scorers = {
        "bigfive": score_bigfive,
        "asrs": score_asrs,
        "hyperactivity": score_hyperactivity,
        "anxiety": score_anxiety,
        "depression": score_depression,
        "stress": score_stress,
        "self_esteem": score_self_esteem,
        "sleep": score_sleep,
        "burnout": score_burnout,
    }
    scorer = scorers.get(scoring_type)
    if not scorer:
        return {"title": "Sonuç", "summary": "Değerlendirme tamamlandı.", "details": [], "level": "info", "match_tags": []}
    return scorer(test, answers)


def _get_answer(answers, question_id):
    raw = answers.get(question_id, "")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _likert_total(test, answers, reverse_ids=None):
    reverse_ids = reverse_ids or set()
    total = 0
    count = 0
    for question in test.question_list():
        value = _get_answer(answers, question["id"])
        if value is None:
            continue
        if question.get("reverse") or question["id"] in reverse_ids:
            max_val = max(opt["value"] for opt in question["options"])
            value = max_val - value
        total += value
        count += 1
    return total, count


def score_bigfive(test, answers):
    dimensions = {key: [] for key in DIMENSION_LABELS}
    for question in test.question_list():
        value = _get_answer(answers, question["id"])
        if value is None:
            continue
        if question.get("reverse"):
            value = 8 - value
        dimensions[question["dimension"]].append(value)

    details = []
    high_neuroticism = False
    for key, label in DIMENSION_LABELS.items():
        values = dimensions[key]
        if not values:
            continue
        avg = sum(values) / len(values)
        if key == "neuroticism" and avg >= 5:
            high_neuroticism = True
        if avg >= 5.5:
            level, text = "yüksek", f"{label} düzeyiniz yüksek görünmektedir."
        elif avg >= 4:
            level, text = "orta", f"{label} düzeyiniz orta bandında."
        else:
            level, text = "düşük", f"{label} düzeyiniz düşük bandında."
        details.append({"label": label, "score": round(avg, 1), "max": 7, "level": level, "text": text})

    match_tags = ["Kişisel Gelişim", "Bireysel Terapi"]
    if high_neuroticism:
        match_tags.extend(["Kaygı", "Anksiyete"])

    return {
        "title": "Kişilik Profili Özeti",
        "summary": "Beş faktör kişilik modeline göre eğilimleriniz aşağıda özetlenmiştir.",
        "details": details,
        "level": "info",
        "match_tags": match_tags,
        "recommendation": "Kişilik testleri eğilimleri gösterir; kesin etiketler değildir. Detaylı değerlendirme için uzman desteği alabilirsiniz.",
    }


def score_asrs(test, answers):
    high_count = 0
    total = 0
    details = []
    for question in test.question_list():
        value = _get_answer(answers, question["id"])
        if value is None:
            continue
        total += value
        flagged = value >= 3
        if flagged:
            high_count += 1
        details.append({"label": question["text"][:60] + "...", "score": value, "max": 4, "level": "yüksek" if flagged else "düşük"})

    max_score = len(test.question_list()) * 4
    if high_count >= 4:
        level = "risk"
        summary = f"ASRS Part A kriterlerine göre dikkat eksikliği belirtileri belirgin olabilir ({high_count}/6 madde eşik üstü)."
        recommendation = "Bu sonuç tanı koymaz. DEHB değerlendirmesi için bir psikiyatrist veya klinik psikolog ile görüşmeniz önerilir."
        match_tags = ["DEHB", "Dikkat", "Bireysel Terapi"]
    elif high_count >= 2:
        level = "moderate"
        summary = f"Bazı dikkat eksikliği belirtileri görülmektedir ({high_count}/6 madde eşik üstü)."
        recommendation = "Belirtiler günlük işlevselliğinizi etkiliyorsa profesyonel destek almayı düşünebilirsiniz."
        match_tags = ["Dikkat", "Bireysel Terapi"]
    else:
        level = "low"
        summary = "Dikkat eksikliği belirtileri düşük düzeyde görünmektedir."
        recommendation = "Sonuçlar bilgilendirme amaçlıdır; endişeleriniz devam ediyorsa uzman görüşü alın."
        match_tags = ["Kişisel Gelişim"]

    return {
        "title": "Dikkat Dağınıklığı Sonucu",
        "summary": summary,
        "score": total,
        "max_score": max_score,
        "high_items": high_count,
        "details": details,
        "level": level,
        "match_tags": match_tags,
        "recommendation": recommendation,
    }


def score_hyperactivity(test, answers):
    total = 0
    count = 0
    high_items = 0
    for question in test.question_list():
        value = _get_answer(answers, question["id"])
        if value is None:
            continue
        count += 1
        total += value
        if value >= 3:
            high_items += 1

    avg = total / count if count else 0
    if avg >= 2.5 or high_items >= 6:
        level = "risk"
        summary = "Hiperaktivite-impulsivite belirtileri belirgin düzeyde görülebilir."
        recommendation = "SNAP-IV temelli tarama sonucudur; tanı için kapsamlı klinik değerlendirme gerekir."
        match_tags = ["DEHB", "Hiperaktivite", "Bireysel Terapi"]
    elif avg >= 1.5 or high_items >= 3:
        level = "moderate"
        summary = "Orta düzeyde hiperaktivite/impulsivite belirtileri görülmektedir."
        recommendation = "Belirtiler yaşam kalitenizi etkiliyorsa terapist veya psikiyatrist desteği düşünülebilir."
        match_tags = ["DEHB", "Bireysel Terapi"]
    else:
        level = "low"
        summary = "Hiperaktivite belirtileri düşük düzeyde görünmektedir."
        recommendation = "Sonuç bilgilendirme amaçlıdır."
        match_tags = ["Kişisel Gelişim"]

    return {
        "title": "Hiperaktivite Sonucu",
        "summary": summary,
        "score": round(avg, 2),
        "max_score": 4,
        "high_items": high_items,
        "level": level,
        "match_tags": match_tags,
        "recommendation": recommendation,
    }


def score_anxiety(test, answers):
    total, count = _likert_total(test, answers)
    if count >= 7:
        if total >= 15:
            level, summary = "risk", "Kaygı belirtileri belirgin düzeyde görülebilir (GAD-7 yüksek bandı)."
            match_tags = ["Kaygı", "Anksiyete", "Bireysel Terapi"]
        elif total >= 10:
            level, summary = "moderate", "Orta düzeyde kaygı belirtileri görülmektedir."
            match_tags = ["Kaygı", "Anksiyete"]
        elif total >= 5:
            level, summary = "moderate", "Hafif kaygı belirtileri görülebilir."
            match_tags = ["Kaygı", "Bireysel Terapi"]
        else:
            level, summary = "low", "Kaygı belirtileri düşük düzeyde görünmektedir."
            match_tags = ["Kişisel Gelişim"]
    else:
        level, summary = "info", "Değerlendirme tamamlandı."
        match_tags = ["Kaygı"]

    return {
        "title": "Kaygı Testi Sonucu",
        "summary": summary,
        "score": total,
        "max_score": 21,
        "level": level,
        "match_tags": match_tags,
        "recommendation": "GAD-7 temelli tarama sonucudur; tanı koymaz. Belirtiler devam ediyorsa uzman desteği alın.",
    }


def score_depression(test, answers):
    total, count = _likert_total(test, answers)
    suicidal = _get_answer(answers, "p9") or 0
    recommendation = "PHQ-9 temelli tarama sonucudur; tanı koymaz."
    if suicidal >= 2:
        level = "risk"
        summary = "Depresyon belirtileri belirgin olabilir; öz-zarar düşünceleri bildirilmiştir."
        recommendation = "Lütfen acilen bir ruh sağlığı uzmanına veya 182 (ALO 182) hattına başvurun."
        match_tags = ["Depresyon", "Bireysel Terapi", "Travma"]
    elif total >= 15:
        level = "risk"
        summary = "Depresyon belirtileri belirgin düzeyde görülebilir (PHQ-9 orta-şiddetli band)."
        recommendation = "Klinik psikolog veya psikiyatrist değerlendirmesi önerilir."
        match_tags = ["Depresyon", "Bireysel Terapi"]
    elif total >= 10:
        level = "moderate"
        summary = "Orta düzeyde depresyon belirtileri görülmektedir."
        recommendation = "Belirtiler günlük yaşamınızı etkiliyorsa profesyonel destek düşünün."
        match_tags = ["Depresyon", "Kaygı"]
    elif total >= 5:
        level = "moderate"
        summary = "Hafif depresyon belirtileri görülebilir."
        match_tags = ["Depresyon", "Bireysel Terapi"]
    else:
        level = "low"
        summary = "Depresyon belirtileri düşük düzeyde görünmektedir."
        match_tags = ["Kişisel Gelişim"]

    return {
        "title": "Depresyon Tarama Sonucu",
        "summary": summary,
        "score": total,
        "max_score": 27,
        "level": level,
        "match_tags": match_tags,
        "recommendation": recommendation,
    }


def score_stress(test, answers):
    total = 0
    count = 0
    for question in test.question_list():
        value = _get_answer(answers, question["id"])
        if value is None:
            continue
        if question.get("reverse"):
            value = 4 - value
        total += value
        count += 1

    if total >= 14:
        level, summary = "risk", "Algılanan stres düzeyiniz yüksek görünmektedir."
        match_tags = ["Stres", "Tükenmişlik", "Bireysel Terapi"]
    elif total >= 9:
        level, summary = "moderate", "Orta düzeyde stres yaşıyor olabilirsiniz."
        match_tags = ["Stres", "Kaygı"]
    else:
        level, summary = "low", "Stres düzeyiniz düşük-orta bandında görünmektedir."
        match_tags = ["Kişisel Gelişim"]

    return {
        "title": "Stres Testi Sonucu",
        "summary": summary,
        "score": total,
        "max_score": 20,
        "level": level,
        "match_tags": match_tags,
        "recommendation": "Stres yönetimi teknikleri ve gerektiğinde terapist desteği faydalı olabilir.",
    }


def score_self_esteem(test, answers):
    total = 0
    count = 0
    for question in test.question_list():
        value = _get_answer(answers, question["id"])
        if value is None:
            continue
        if question.get("reverse"):
            value = 8 - value
        total += value
        count += 1

    avg = total / count if count else 0
    if avg <= 3.5:
        level, summary = "risk", "Özgüven ve öz-değer algınız düşük bandında görünmektedir."
        match_tags = ["Özgüven", "Kişisel Gelişim", "Bireysel Terapi"]
    elif avg <= 5:
        level, summary = "moderate", "Özgüven düzeyiniz orta bandında; gelişim alanları olabilir."
        match_tags = ["Kişisel Gelişim", "Bireysel Terapi"]
    else:
        level, summary = "low", "Özgüven düzeyiniz sağlıklı banda yakın görünmektedir."
        match_tags = ["Kişisel Gelişim"]

    return {
        "title": "Özgüven Testi Sonucu",
        "summary": summary,
        "score": round(avg, 1),
        "max_score": 7,
        "level": level,
        "match_tags": match_tags,
        "recommendation": "Özgüven çalışmaları bireysel terapi ile desteklenebilir.",
    }


def score_sleep(test, answers):
    total, count = _likert_total(test, answers)
    if total >= 15:
        level, summary = "risk", "Uyku kalitesi belirgin düzeyde olumsuz görünmektedir."
        match_tags = ["Uyku", "Kaygı", "Stres"]
    elif total >= 10:
        level, summary = "moderate", "Uyku sorunları orta düzeyde görülebilir."
        match_tags = ["Uyku", "Bireysel Terapi"]
    else:
        level, summary = "low", "Uyku kalitesi genel olarak iyi banda yakın görünmektedir."
        match_tags = ["Kişisel Gelişim"]

    return {
        "title": "Uyku Kalitesi Sonucu",
        "summary": summary,
        "score": total,
        "max_score": 20,
        "level": level,
        "match_tags": match_tags,
        "recommendation": "Uyku hijyeni ve gerektiğinde uzman desteği uyku kalitesini iyileştirebilir.",
    }


def score_burnout(test, answers):
    total, count = _likert_total(test, answers)
    avg = total / count if count else 0
    if avg >= 2.8 or total >= 16:
        level, summary = "risk", "Tükenmişlik belirtileri belirgin düzeyde görülebilir."
        match_tags = ["Tükenmişlik", "Stres", "Bireysel Terapi"]
    elif avg >= 1.8 or total >= 10:
        level, summary = "moderate", "Orta düzeyde tükenmişlik belirtileri görülmektedir."
        match_tags = ["Tükenmişlik", "Stres"]
    else:
        level, summary = "low", "Tükenmişlik belirtileri düşük düzeyde görünmektedir."
        match_tags = ["Kişisel Gelişim"]

    return {
        "title": "Tükenmişlik Testi Sonucu",
        "summary": summary,
        "score": round(avg, 2),
        "max_score": 4,
        "level": level,
        "match_tags": match_tags,
        "recommendation": "İş-yaşam dengesi ve profesyonel destek tükenmişlikle başa çıkmada yardımcı olabilir.",
    }
