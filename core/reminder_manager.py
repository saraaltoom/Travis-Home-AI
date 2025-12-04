import datetime
import json
import os
import threading
import time
from typing import Callable, List, Dict, Optional


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
REM_PATH = os.path.join(DATA_DIR, "reminders.json")

_lock = threading.Lock()
_scheduler_started = False
_speak: Callable[[str], None] | None = None


def _ensure_store():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(REM_PATH):
        with open(REM_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)


def load_reminders() -> List[Dict]:
    _ensure_store()
    try:
        with open(REM_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_reminders(items: List[Dict]):
    _ensure_store()
    with open(REM_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def add_reminder(message: str, when_str: str) -> str:
    """Add a reminder at a specific local time (YYYY-MM-DD HH:MM)."""
    try:
        dt = datetime.datetime.strptime(when_str, "%Y-%m-%d %H:%M")
    except ValueError:
        return "Invalid time. Use YYYY-MM-DD HH:MM"
    with _lock:
        items = load_reminders()
        items.append({"message": message or "Reminder", "datetime": dt.isoformat()})
        save_reminders(items)
    return f"Reminder set for {dt.strftime('%Y-%m-%d %I:%M %p')}"


def add_relative_reminder(message: str, base_dt: datetime.datetime, minutes_before: int) -> str:
    when = base_dt - datetime.timedelta(minutes=max(0, int(minutes_before)))
    return add_reminder(message, when.strftime("%Y-%m-%d %H:%M"))


def add_reminder_unique(uid: str, message: str, when_str: str) -> Optional[str]:
    """Add a reminder only if a given uid hasn't been scheduled yet.

    Stores uid in the reminder object for deduplication.
    Returns the confirmation message if added, or None if already present/invalid.
    """
    try:
        dt = datetime.datetime.strptime(when_str, "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    with _lock:
        items = load_reminders()
        for it in items:
            if it.get("uid") == uid:
                return None
        items.append({"uid": uid, "message": message or "Reminder", "datetime": dt.isoformat()})
        save_reminders(items)
    return f"Reminder set for {dt.strftime('%Y-%m-%d %I:%M %p')}"


def _tick():
    global _scheduler_started
    while _scheduler_started:
        try:
            now = datetime.datetime.now()
            due: List[Dict] = []
            with _lock:
                items = load_reminders()
                remaining: List[Dict] = []
                for it in items:
                    try:
                        dt = datetime.datetime.fromisoformat(it.get("datetime"))
                        if dt <= now:
                            due.append(it)
                        else:
                            remaining.append(it)
                    except Exception:
                        continue
                if due or (len(remaining) != len(items)):
                    save_reminders(remaining)

            if _speak is not None:
                for it in due:
                    msg = it.get("message") or "You have a reminder now."
                    try:
                        _speak(msg)
                    except Exception:
                        pass
        except Exception:
            pass
        time.sleep(30)


def start_scheduler(speak: Callable[[str], None]):
    global _scheduler_started, _speak
    if _scheduler_started:
        return
    _speak = speak
    _scheduler_started = True
    t = threading.Thread(target=_tick, name="reminder-scheduler", daemon=True)
    t.start()
