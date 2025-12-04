import datetime
import requests
import urllib.parse
from core.ollama_api import ask_ollama


def _is_arabic(text: str) -> bool:
    return any('\u0600' <= ch <= '\u06FF' for ch in text or '')


def _wiki_summary(prompt: str) -> str | None:
    try:
        q = (prompt or "").strip()
        if not q:
            return None

        langs = ["ar", "en"] if _is_arabic(q) else ["en", "ar"]
        for lang in langs:
            title = urllib.parse.quote(q)
            url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
            r = requests.get(url, timeout=8)
            if r.status_code == 200:
                data = r.json()
                extract = data.get("extract")
                if extract:
                    return extract

            r = requests.get(
                f"https://{lang}.wikipedia.org/w/api.php",
                params={
                    "action": "opensearch",
                    "search": q,
                    "limit": 1,
                    "namespace": 0,
                    "format": "json",
                },
                timeout=8,
            )
            if r.status_code == 200:
                data = r.json()
                if len(data) >= 2 and data[1]:
                    best = data[1][0]
                    if best:
                        title = urllib.parse.quote(best)
                        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
                        r2 = requests.get(url, timeout=8)
                        if r2.status_code == 200:
                            extract = r2.json().get("extract")
                            if extract:
                                return extract
    except Exception:
        return None
    return None


def _duckduckgo_instant_answer(prompt: str) -> str | None:
    try:
        q = (prompt or "").strip()
        if not q:
            return None
        url = "https://api.duckduckgo.com/"
        r = requests.get(
            url,
            params={"q": q, "format": "json", "no_redirect": 1, "no_html": 1},
            timeout=8,
        )
        if r.status_code == 200:
            data = r.json()
            txt = data.get("AbstractText")
            if txt:
                return txt
            topics = data.get("RelatedTopics") or []
            for t in topics:
                if isinstance(t, dict) and t.get("Text"):
                    return t.get("Text")
    except Exception:
        return None
    return None


def chat_with_ai(prompt: str) -> str:
    p = (prompt or "").strip().lower()


    if any(k in p for k in ["time", "what time", "current time", "now"]):
        now = datetime.datetime.now().strftime("%I:%M %p")
        return f"The time is {now}."


    if any(k in p for k in ["weather", "forecast", "temperature"]):
        return "Today's weather is warm with some clouds."


    resp = ask_ollama(prompt)
    if resp and "I couldn't connect to my brain" not in resp:
        return resp

    wiki = _wiki_summary(prompt)
    if wiki:
        return wiki

    ddg = _duckduckgo_instant_answer(prompt)
    if ddg:
        return ddg

    return (
        "I couldn't reach my knowledge sources right now. "
        "If you enable Ollama or internet access, I can give richer answers."
    )
