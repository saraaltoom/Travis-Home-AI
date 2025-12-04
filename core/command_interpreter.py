from core.chat_with_ai import chat_with_ai
from core.analyze import analyze_command
from core.device_api import execute_device_action
from core.face_store import recognize, capture_and_add, get_owner_name
from core.calendar_manager import get_today_summary, get_upcoming_events, add_event
from core import calendar_google
from core.ai_interpreter import interpret_with_ai
from core.browser_helper import open_url, open_booking_search
from core.reminder_manager import add_reminder, add_relative_reminder


def handle_command(text, serial_bridge, speak, owner_name=None):
    if owner_name is None:
        owner_name = get_owner_name() or "Owner"
    parsed = analyze_command(text)
    kind = parsed.get("type")

    if kind == "device_control":
        data = {
            "action": parsed.get("action"),
            "device": parsed.get("device"),
            "level": parsed.get("level"),
        }
        execute_device_action(data, serial_bridge)
        return

    if kind == "add_face":
        speak("For security, owner please look at the camera.")
        user = recognize()
        if user != owner_name:
            speak("Access denied. Only the owner can add faces.")
            return
        speak("Who's joining? After the name, please bring the new person in front of the camera and look straight.")
        name = input("Enter the name of the new user: ")
        if not name:
            speak("No name provided.")
            return
        ok = capture_and_add(name)
        speak(f"{name} added successfully." if ok else "Failed to add face. Try again.")
        return

    if kind == "calendar_query":
        intent = parsed.get("intent")

        try:
            from core import calendar_google as cg
            if cg.is_available():
                if intent == "upcoming":
                    items = cg.upcoming(limit=5)
                    if not items:
                        speak("You have no upcoming events.")
                    else:
                        parts = []
                        import datetime
                        for ev in items:
                            title = ev.get("summary", "(No title)")
                            start = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date")
                            try:
                                dt = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
                                parts.append(f"{title} at {dt.strftime('%Y-%m-%d %I:%M %p')}")
                            except Exception:
                                parts.append(title)
                        speak("; ".join(parts))
                else:
                    speak(cg.today_summary())
                return
        except Exception:
            pass

        if intent == "upcoming":
            summary = get_upcoming_events()
        else:
            summary = get_today_summary()
        speak(summary)
        return

    if kind == "calendar_add":
        title = parsed.get("title") or "Untitled"
        dt = parsed.get("datetime") or ""
        from core import calendar_google
        if calendar_google.is_available():
            msg = calendar_google.add_event(title, dt)
            speak(msg)
        else:
            msg = add_event(title, dt)
            speak(msg)

        try:
            import datetime
            from core.reminder_manager import add_relative_reminder
            base_dt = datetime.datetime.strptime(dt, "%Y-%m-%d %H:%M")
            speak(add_relative_reminder(f"Reminder: {title}", base_dt, 30))
        except Exception:
            pass
        return

    if kind == "calendar_add_missing":
        title = parsed.get("title") or "Untitled"
        speak(f"What date and time for '{title}'? Say like 2025-11-10 14:30 or 'today 3 pm'.")

        from core.voice_assistant import listen
        answer = listen()
        if not answer:

            try:
                answer = input("Type date/time (e.g., 2025-11-10 14:30 or 'today 3 pm'): ").strip()
            except Exception:
                answer = ""
        if not answer:
            speak("I didn't catch the time. Please try again later.")
            return
        follow = analyze_command(f"add {title} on {answer}")
        if follow.get("type") == "calendar_add" and follow.get("datetime"):
            return handle_command(f"add {title} on {answer}", serial_bridge, speak)
        else:
            speak("Couldn't parse the time. Please say the exact date and time, like 2025-11-10 14:30.")
            return

    if kind == "open_booking":
        q = parsed.get("query") or ""
        bias = "saudia " if any(w in q for w in ["طياره", "طيران", "flight"]) else ""
        from core.browser_helper import open_booking_search
        opened = open_booking_search(bias + q)
        speak("Opening booking options in your browser." if opened else "I couldn't open the browser.")
        return

    if kind == "reminder":
        at = parsed.get("at")
        msg = parsed.get("message") or "Reminder"
        if at:
            from core.reminder_manager import add_reminder
            speak(add_reminder(msg, at))
            return



    low = (text or "").lower()
    cal_words = [
        "add", "schedule", "meeting", "appointment",
        "موعد", "أضف", "اضف", "إضافة", "ضيف", "جدول", "حط", "سجل",
    ]
    if any(w in low for w in cal_words):
        try:
            import re
            import dateparser
            dt_candidate = dateparser.parse(
                text,
                languages=["en", "ar"],
                settings={
                    "PREFER_DATES_FROM": "future",
                    "RETURN_AS_TIMEZONE_AWARE": False,
                },
            )
        except Exception:
            dt_candidate = None
        if dt_candidate is not None:

            stop = {
                "add","schedule","meeting","appointment","on","at","today","tomorrow",
                "موعد","أضف","اضف","إضافة","ضيف","جدول","حط","سجل","اليوم","غداً","غدا","بكرا","بكرة","باكر",
                "am","pm","صباح","مساء","عصر","ظهر","الصباح","المساء","العصر","الظهر",
            }
            tokens = re.findall(r"[\w\u0600-\u06FF]+", text)
            title_tokens = [tok for tok in tokens if tok.lower() not in stop and not tok.isdigit()]
            title = " ".join(title_tokens[:6]) or "appointment"

            from core import calendar_google
            dt_str = dt_candidate.strftime('%Y-%m-%d %H:%M')
            if calendar_google.is_available():
                speak(calendar_google.add_event(title, dt_str))
            else:
                speak(add_event(title, dt_str))

            try:
                import datetime
                from core.reminder_manager import add_relative_reminder
                base_dt = dt_candidate
                speak(add_relative_reminder(f"Reminder: {title}", base_dt, 30))
            except Exception:
                pass
            return


    ai_result = interpret_with_ai(text)


    serial_cmds = ai_result.get("serial") or []
    if serial_cmds and serial_bridge:
        for cmd in serial_cmds:
            if not cmd:
                continue
            s = str(cmd).strip()
            serial_bridge.send(s)


    cal = ai_result.get("calendar") or {}
    if isinstance(cal, dict) and (cal.get("action") == "add"):
        title = cal.get("title") or "Untitled"
        dt = cal.get("datetime") or ""
        if calendar_google.is_available():
            msg = calendar_google.add_event(title, dt)
            speak(msg)
        else:
            msg = add_event(title, dt)
            speak(msg)

        try:
            import datetime
            from core.reminder_manager import add_relative_reminder
            base_dt = datetime.datetime.strptime(dt, "%Y-%m-%d %H:%M")
            speak(add_relative_reminder(f"Reminder: {title}", base_dt, 30))
        except Exception:
            pass
        return


    url = ai_result.get("open_url")
    search = ai_result.get("open_search")
    if url and open_url(str(url)):
        speak("Opening in your browser.")
        return
    if search and open_booking_search(str(search)):
        speak("Opening booking options in your browser.")
        return


    rem = ai_result.get("reminder") or {}
    if isinstance(rem, dict):
        at = rem.get("at")
        msg = rem.get("message") or "Reminder"
        if at:
            speak(add_reminder(msg, at))
            return

        title = rem.get("for_title")
        minutes_before = rem.get("minutes_before")
        if title and minutes_before is not None:

            import datetime
            events = get_upcoming_events().split("; ")

            speak("Please tell me the exact time for the reminder, like 2025-11-10 09:30.")
            return



    ask = ai_result.get("ask")
    if ask:
        speak(str(ask))
        return

    speak_text = ai_result.get("speak")
    if speak_text:
        speak(speak_text)
    else:
        reply = chat_with_ai(parsed.get("prompt", text))
        speak(reply)


def execute_action(command, serial_bridge, speak):

    if not isinstance(command, str):
        speak("Invalid command format.")
        return
    c = command.lower()
    if "door" in c and "open" in c:
        serial_bridge.send("open door")
        return
    if "door" in c and "close" in c:
        serial_bridge.send("close door")
        return
    if "light" in c:
        if "high" in c:
            serial_bridge.send("light high")
            return
        if "medium" in c:
            serial_bridge.send("light medium")
            return
        if "off" in c:
            serial_bridge.send("light off")
            return
        if "low" in c:
            serial_bridge.send("light low")
            return
    speak("Sorry, I don't understand the action.")

