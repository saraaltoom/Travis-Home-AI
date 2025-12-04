import datetime
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CAL_PATH = os.path.join(DATA_DIR, "calendar.json")


def _ensure_store():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(CAL_PATH):
        with open(CAL_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)


def load_events():
    _ensure_store()
    with open(CAL_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    events = []
    for e in raw:
        try:
            dt = datetime.datetime.fromisoformat(e["datetime"])
            events.append({"title": e["title"], "datetime": dt})
        except Exception:
            continue
    return events


def save_events(events):
    _ensure_store()
    serializable = [{"title": e["title"], "datetime": e["datetime"].isoformat()} for e in events]
    with open(CAL_PATH, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)


def add_event(title, date_str):
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M")
    except ValueError:
        return "Invalid date format. Use YYYY-MM-DD HH:MM."
    events = load_events()
    events.append({"title": title, "datetime": dt})
    save_events(events)
    return f"Event '{title}' added for {dt.strftime('%Y-%m-%d %I:%M %p')}."


def get_upcoming_events(limit=5):
    now = datetime.datetime.now()
    events = [e for e in load_events() if e["datetime"] > now]
    events.sort(key=lambda e: e["datetime"])
    if not events:
        return "You have no upcoming events."
    events = events[:limit]
    return "; ".join([f"{e['title']} at {e['datetime'].strftime('%Y-%m-%d %I:%M %p')}" for e in events])


def get_today_events():
    now = datetime.datetime.now()
    start = datetime.datetime(now.year, now.month, now.day)
    end = start + datetime.timedelta(days=1)
    todays = [e for e in load_events() if start <= e["datetime"] < end]
    todays.sort(key=lambda e: e["datetime"])
    return todays


def get_today_summary():
    todays = get_today_events()
    if not todays:
        return "You have nothing scheduled for today."
    parts = [f"{e['title']} at {e['datetime'].strftime('%I:%M %p')}" for e in todays]
    return "Today: " + "; ".join(parts)
