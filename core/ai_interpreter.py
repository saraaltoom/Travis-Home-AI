import json
from typing import Dict, Any, List

from core.ollama_api import ask_ollama


SYSTEM_INSTRUCTIONS = (
    "You are Travis' command parser. Understand English and Arabic.\n"
    "Input: a user's natural-language request.\n"
    "Output: STRICT JSON with optional keys: \n"
    "- speak: short English sentence to speak back.\n"
    "- serial: array of strings to send over serial to Arduino (each ends with a newline on host).\n"
    "- calendar: object for scheduling tasks, e.g. {\"action\": \"add\", \"title\": \"...\", \"datetime\": \"YYYY-MM-DD HH:MM\"}.\n"
    "- open_url: absolute URL to open in browser; or open_search: plain text to search for booking.\n"
    "- reminder: object like {\"message\": \"...\", \"at\": \"YYYY-MM-DD HH:MM\"} or {\"for_title\": \"...\", \"minutes_before\": 30}.\n"
    "- ask: if information is missing, include a clarifying question instead of guessing.\n"
    "Rules:\n"
    "- Do not add markdown, code fences, or commentary. JSON only.\n"
    "- If the request is a device action, map it to clear serial strings understood by Arduino.\n"
    "- Prefer commands like: 'open door', 'close door', 'light on top', 'light off bottom', 'light on bottom'.\n"
    "- If user mentions new hardware/commands, pass through a reasonable serial string matching the wording.\n"
    "- For calendar additions, convert any relative time (e.g., 'tomorrow 3 pm') into local time in 'YYYY-MM-DD HH:MM' 24-hour format.\n"
    "- If no action is needed, return only {\"speak\": \"...\"}.\n"
)


def _build_prompt(user_text: str) -> str:
    examples = [
        (
            "open the door",
            {"speak": "Opening the door.", "serial": ["open door"]},
        ),
        ("turn on the light", {"speak": "Turning on lights.", "serial": ["light on top", "light on bottom"]}),
        ("turn off the light", {"speak": "Turning lights off.", "serial": ["light off top", "light off bottom"]}),
        ("turn off the top light", {"speak": "Turning off the top light.", "serial": ["light off top"]}),
        ("turn on the bottom light", {"speak": "Turning on the bottom light.", "serial": ["light on bottom"]}),
        (
            "switch off the light",
            {"speak": "Turning lights off.", "serial": ["light off top", "light off bottom"]},
        ),
        (
            "close the door",
            {"speak": "Closing the door.", "serial": ["close door"]},
        ),
        (
            "what time is it?",
            {"speak": "Let me check the time for you."},
        ),
        (
            "add a dentist appointment tomorrow at 15:00",
            {"speak": "Added to your calendar.", "calendar": {"action": "add", "title": "Dentist appointment", "datetime": "2025-05-20 15:00"}},
        ),
        ("add an appointment to my schedule", {"ask": "What date and time? Please say YYYY-MM-DD HH:MM or 'today 3 pm'."}),
        (
            "remind me at 9:30 to call mom",
            {"speak": "Okay, I'll remind you.", "reminder": {"message": "Call mom", "at": "2025-05-20 09:30"}},
        ),
        (
            "open booking page for Pizza Hut in Riyadh",
            {"speak": "Opening booking search.", "open_search": "Pizza Hut Riyadh"},
        ),
        ("أضف موعد لجدولي اليوم الساعة 3 مساء", {"calendar": {"action": "add", "title": "موعد", "datetime": "2025-05-20 15:00"}, "speak": "تمت الإضافة."}),
        ("اطفئ الاضاءة العلوية", {"serial": ["light off top"], "speak": "حسنًا، أطفأت الإضاءة العلوية."}),
        ("شغّل الإضاءة السفلية", {"serial": ["light on bottom"], "speak": "تم تشغيل الإضاءة السفلية."}),
    ]

    parts = [SYSTEM_INSTRUCTIONS, "Examples:"]
    for u, j in examples:
        parts.append(f"User: {u}")
        parts.append(f"JSON: {json.dumps(j, ensure_ascii=False)}")
    parts.append("User: " + user_text)
    parts.append("JSON:")
    return "\n".join(parts)


def _coerce_result(text: str) -> Dict[str, Any]:
    if not text:
        return {}

    try:
        return json.loads(text)
    except Exception:
        pass


    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = text[start:end + 1]
        try:
            return json.loads(snippet)
        except Exception:
            pass
    return {}


def interpret_with_ai(user_text: str) -> Dict[str, Any]:
    prompt = _build_prompt(user_text)
    raw = ask_ollama(prompt)
    return _coerce_result(raw)
