"""
Optional Google Calendar integration.

Requires:
  pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

Files:
  data/credentials.json  -> OAuth client (Desktop) from Google Cloud Console
  data/token.json        -> Generated on first auth

Functions gracefully no-op if libraries or credentials are missing.
"""

import os
import datetime
from typing import List, Dict, Optional


def _svc():
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
    except Exception:
        return None

    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    base = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    cred_path = os.path.join(base, "credentials.json")
    token_path = os.path.join(base, "token.json")
    if not os.path.exists(cred_path):
        return None

    creds = None
    try:
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, "w") as token:
                token.write(creds.to_json())
        service = build("calendar", "v3", credentials=creds)
        return service
    except Exception:
        return None


def is_available() -> bool:
    return _svc() is not None


def add_event(title: str, when_str: str) -> str:
    svc = _svc()
    if not svc:
        return "Google Calendar not configured."
    try:
        dt = datetime.datetime.strptime(when_str, "%Y-%m-%d %H:%M")
    except ValueError:
        return "Invalid date format. Use YYYY-MM-DD HH:MM."
    start = dt.isoformat()
    end = (dt + datetime.timedelta(hours=1)).isoformat()
    event = {
        "summary": title or "Untitled",
        "start": {"dateTime": start},
        "end": {"dateTime": end},
    }
    try:
        svc.events().insert(calendarId="primary", body=event).execute()
        return f"Event '{title}' added to Google Calendar at {dt.strftime('%Y-%m-%d %I:%M %p')}."
    except Exception:
        return "Failed to add event to Google Calendar."


def upcoming(limit: int = 5) -> List[Dict]:
    svc = _svc()
    if not svc:
        return []
    now = datetime.datetime.utcnow().isoformat() + "Z"
    try:
        events_result = (
            svc.events()
            .list(calendarId="primary", timeMin=now, maxResults=limit, singleEvents=True, orderBy="startTime")
            .execute()
        )
        return events_result.get("items", [])
    except Exception:
        return []


def today_summary() -> str:
    svc = _svc()
    if not svc:
        return ""
    now = datetime.datetime.now()
    start = datetime.datetime(now.year, now.month, now.day)
    end = start + datetime.timedelta(days=1)
    try:
        events_result = (
            svc.events()
            .list(
                calendarId="primary",
                timeMin=start.isoformat() + "Z",
                timeMax=end.isoformat() + "Z",
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        items = events_result.get("items", [])
        if not items:
            return "You have nothing scheduled for today."
        parts = []
        for it in items:
            title = it.get("summary", "(No title)")
            start_time = it.get("start", {}).get("dateTime") or it.get("start", {}).get("date")
            try:
                dt = datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                parts.append(f"{title} at {dt.strftime('%I:%M %p')}")
            except Exception:
                parts.append(title)
        return "Today: " + "; ".join(parts)
    except Exception:
        return "You have nothing scheduled for today."

