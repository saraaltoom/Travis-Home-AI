import threading
import time
import datetime
from typing import Optional


def _to_local_naive(dt_str: str) -> Optional[datetime.datetime]:
    try:

        if dt_str.endswith('Z'):
            dt = datetime.datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        else:
            dt = datetime.datetime.fromisoformat(dt_str)
        if dt.tzinfo:

            return dt.astimezone().replace(tzinfo=None)
        return dt
    except Exception:
        return None


def start_google_calendar_sync(speak, minutes_before: int = 30, poll_seconds: int = 300):
    """Background sync: poll Google Calendar and create local reminders for upcoming events.

    - Creates a reminder minutes_before each event, and optionally at start time.
    - Deduplicates via reminder uid: gcal:{event_id}:{offset}
    - Requires calendar_google.is_available() to be True.
    """
    try:
        from core import calendar_google as cg
        from core.reminder_manager import add_reminder_unique
    except Exception:
        return

    if not getattr(cg, 'is_available', lambda: False)():
        return

    def _runner():
        while True:
            try:
                events = cg.upcoming(limit=15) or []
                now = datetime.datetime.now()
                for ev in events:
                    eid = ev.get('id') or ev.get('iCalUID') or None
                    title = ev.get('summary', '(No title)')
                    start = ev.get('start', {}).get('dateTime') or ev.get('start', {}).get('date')
                    if not start:
                        continue
                    dt = _to_local_naive(start)
                    if not dt:
                        continue

                    if dt <= now:
                        continue

                    before = dt - datetime.timedelta(minutes=minutes_before)
                    if before > now:
                        uid = f"gcal:{eid}:minus{minutes_before}" if eid else f"gcal:unknown:{dt.timestamp():.0f}:m{minutes_before}"
                        msg = f"In {minutes_before} minutes: {title} at {dt.strftime('%I:%M %p')}"
                        add_reminder_unique(uid, msg, before.strftime('%Y-%m-%d %H:%M'))

                    uid2 = f"gcal:{eid}:start" if eid else f"gcal:unknown:{dt.timestamp():.0f}:start"
                    msg2 = f"Event starting now: {title}"
                    add_reminder_unique(uid2, msg2, dt.strftime('%Y-%m-%d %H:%M'))
            except Exception:
                pass
            time.sleep(max(60, int(poll_seconds)))

    t = threading.Thread(target=_runner, name='gcal-sync', daemon=True)
    t.start()

