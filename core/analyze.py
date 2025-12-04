def analyze_command(text: str):
    """
    Lightweight heuristic parser supporting English and Arabic keywords.

    Returns dict with keys:
    - type: 'device_control' | 'add_face' | 'calendar_query' | 'ai_query'
    - For device_control: {action, device, level(optional)}
    - For calendar_query: {intent: 'today'|'upcoming'}
    - For ai_query: {prompt}
    """
    if not text:
        return {"type": "ai_query", "prompt": ""}

    raw = text.strip()

    digits_map = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    raw_norm = raw.translate(digits_map)
    t = raw_norm.lower()


    add_face_keywords_en = ["add", "register", "enroll", "new"]
    add_face_keywords_ar = ["اضف", "أضف", "سجل", "سجّل", "اضافة", "إضافة"]
    if ("face" in t and any(k in t for k in add_face_keywords_en)) or any(k in t for k in add_face_keywords_ar):
        if "وجه" in t or "بصمة" in t or "face" in t:
            return {"type": "add_face"}


    ar_device_intents = {
        "افتح الباب": ("door", "open", None),
        "افتح باب": ("door", "open", None),
        "قفل الباب": ("door", "close", None),
        "اغلق الباب": ("door", "close", None),
        "اغلق باب": ("door", "close", None),
        "اقفل الباب": ("door", "close", None),
        "شغل النور": ("light", "turn_on", None),
        "شغّل النور": ("light", "turn_on", None),
        "ولع النور": ("light", "turn_on", None),
        "طفي النور": ("light", "turn_off", None),
        "اطفئ النور": ("light", "turn_off", None),
        "أطفئ النور": ("light", "turn_off", None),
        "نور عالي": ("light", "turn_on", "high"),
        "نور متوسط": ("light", "turn_on", "medium"),
        "نور منخفض": ("light", "turn_on", "low"),
        "اضف وجه جديد": ("add_face", None, None),
        "أضف وجه جديد": ("add_face", None, None),
        "اضافة وجه جديد": ("add_face", None, None),
        "سجل وجه": ("add_face", None, None),
        "سجّل وجه": ("add_face", None, None),
        "اضف بصمة وجه": ("add_face", None, None),
        "أضف بصمة وجه": ("add_face", None, None),
    }


    for phrase, triple in ar_device_intents.items():
        if phrase in raw:
            if triple[0] == "add_face":
                return {"type": "add_face"}
            device, action, level = triple
            return {"type": "device_control", "device": device, "action": action, "level": level}


    if any(w in t for w in [
        "open door", "open the door",
        "close door", "close the door",
        "turn on light", "turn on the light", "switch on light", "switch on the light", "lights on",
        "turn off light", "turn off the light", "switch off light", "switch off the light", "lights off",
        "light high", "light medium", "light low"
    ]):
        action = None
        device = None
        level = None

        if "door" in t:
            device = "door"
            action = "open" if "open" in t else ("close" if "close" in t else None)
        elif "light" in t or "lights" in t:
            device = "light"
            if "turn on" in t or "switch on" in t or "lights on" in t:
                action = "turn_on"
            if "turn off" in t or "switch off" in t or "lights off" in t or "off" in t:
                action = "turn_off"
            if "high" in t:
                level = "high"
            elif "medium" in t:
                level = "medium"
            elif "low" in t:
                level = "low"

        return {"type": "device_control", "action": action, "device": device, "level": level}


    if any(w in t for w in ["add face", "add new face", "register face"]):
        return {"type": "add_face"}


    if ("top light" in t or "upper light" in t or "bottom light" in t or "lower light" in t
        or any(w in t for w in ["العلوي", "علوي", "علوية", "علويه", "فوق"])
        or any(w in t for w in ["السفلي", "سفلي", "سفلية", "سفليه", "تحت"])):
        is_top = any(w in t for w in ["top", "upper", "العلوي", "علوي", "علوية", "علويه", "فوق"])
        device = "light_top" if is_top else "light_bottom"
        off_words = ["off", "turn off", "switch off", "اطفي", "أطفئ", "اطفئ", "طف", "طفي", "طفّي", "إيقاف"]
        action = "turn_off" if any(w in t for w in off_words) else "turn_on"
        level = None
        if any(w in t for w in ["high", "عالي", "مرتفع", "فل"]):
            level = "high"
        elif any(w in t for w in ["low", "منخفض", "خفيف"]):
            level = "low"
        return {"type": "device_control", "device": device, "action": action, "level": level}


    if any(w in t for w in ["schedule", "calendar", "event", "جدولي", "مواعيدي", "موعد", "اليوم", "بكرا", "بكرة", "باكر", "tomorrow", "today"]):
        intent = None
        if any(w in t for w in ["today", "اليوم"]):
            intent = "today"
        elif any(w in t for w in ["upcoming", "next", "القادمة", "الجاي"]):
            intent = "upcoming"
        if not intent:
            intent = "today"
        return {"type": "calendar_query", "intent": intent}



    import re, datetime
    if any(w in t for w in ["add", "schedule", "meeting", "appointment", "موعد", "أضف", "اضف", "إضافة", "ضيف", "جدول", "حط", "سجل"]):

        try:
            import dateparser
            dt_candidate = dateparser.parse(
                raw_norm,
                languages=["en", "ar"],
                settings={
                    "PREFER_DATES_FROM": "future",
                    "RELATIVE_BASE": None,
                    "RETURN_AS_TIMEZONE_AWARE": False,
                },
            )
        except Exception:
            dt_candidate = None


        m_date = re.search(r"(\d{4}-\d{2}-\d{2})", t)
        m_time = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", t)
        title = "appointment"

        words = [w for w in raw_norm.split() if w.lower() not in ("add","schedule","meeting","appointment","on","at","today","tomorrow","اليوم","غداً","غدا","بكرا","بكرة","باكر","الساعة")]
        if words:
            title = " ".join(words[:6])
        if dt_candidate:


            try:
                return {"type": "calendar_add", "title": title, "datetime": dt_candidate.strftime('%Y-%m-%d %H:%M')}
            except Exception:
                pass
        day = None
        if any(w in t for w in ["اليوم", "today"]):
            day = datetime.datetime.now().date()
        elif any(w in t for w in ["غداً", "غدا", "tomorrow", "بكرا", "بكرة", "باكر"]):
            day = (datetime.datetime.now() + datetime.timedelta(days=1)).date()
        elif m_date:
            try:
                day = datetime.date.fromisoformat(m_date.group(1))
            except Exception:
                day = None
        if m_time:
            hh = int(m_time.group(1))
            mm = int(m_time.group(2) or 0)
            ap = (m_time.group(3) or '').lower()

            if not ap:
                if any(w in t for w in ["مساء", "المساء", "ليل", "ليلاً", "ليلًا", "بعد الظهر", "عصر", "العصر", "ظهر", "الظهر"]):
                    ap = 'pm'
                if any(w in t for w in ["صباح", "الصباح", "صباحاً", "الصبح", "فجراً", "فجرا", "الفجر"]):
                    ap = 'am'
            if ap == 'pm' and hh < 12:
                hh += 12
            if ap == 'am' and hh == 12:
                hh = 0
            if day is None:
                day = datetime.datetime.now().date()
            when = datetime.datetime(day.year, day.month, day.day, hh % 24, mm % 60)
            return {"type": "calendar_add", "title": title, "datetime": when.strftime('%Y-%m-%d %H:%M')}

        bare_hour = re.search(r"\b(\d{1,2})\b", t)
        if bare_hour and ("today" in t or "اليوم" in t or "tomorrow" in t or "غدا" in t or "غداً" in t or "بكرا" in t or "بكرة" in t or "باكر" in t):
            hh = int(bare_hour.group(1)) % 24

            if any(w in t for w in ["مساء", "المساء", "ليل", "ليلاً", "ليلًا", "عصر", "العصر", "ظهر", "الظهر", "pm"]):
                if hh < 12:
                    hh += 12
            if any(w in t for w in ["صباح", "الصباح", "صباحاً", "الصبح", "فجر", "الفجر", "am"]):
                if hh == 12:
                    hh = 0
            day = datetime.datetime.now().date() if any(w in t for w in ["today", "اليوم"]) else (datetime.datetime.now() + datetime.timedelta(days=1)).date()
            when = datetime.datetime(day.year, day.month, day.day, hh % 24, 0)
            return {"type": "calendar_add", "title": title, "datetime": when.strftime('%Y-%m-%d %H:%M')}

        return {"type": "calendar_add_missing", "title": title}


    if any(w in t for w in ["book", "booking", "reserve", "reservation", "احجز", "احجزي", "حجز", "طيران", "طياره", "رحلة"]):

        return {"type": "open_booking", "query": raw}


    import re, datetime
    if any(w in t for w in ["remind", "ذك", "ذكرني", "ذكّرني", "ذكري"]):
        m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", t)
        if m:
            hh = int(m.group(1))
            mm = int(m.group(2) or 0)
            ampm = (m.group(3) or '').lower()
            if ampm == 'pm' and hh < 12:
                hh += 12
            if ampm == 'am' and hh == 12:
                hh = 0
            now = datetime.datetime.now()
            at = datetime.datetime(now.year, now.month, now.day, hh % 24, mm % 60)
            return {"type": "reminder", "at": at.strftime('%Y-%m-%d %H:%M'), "message": raw}


    return {"type": "ai_query", "prompt": raw}
