import webbrowser
import urllib.parse
import os
import shutil
import subprocess


def _chrome_path() -> str | None:

    p = os.environ.get("TRAVIS_CHROME_PATH")
    if p and os.path.isfile(p):
        return p

    candidates = [
        r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c

    exe = shutil.which("chrome") or shutil.which("chrome.exe") or shutil.which("google-chrome")
    return exe


def open_url(url: str) -> bool:
    if not url:
        return False
    try:
        chrome = _chrome_path()
        if chrome:
            subprocess.Popen([chrome, url])
            return True

        webbrowser.open(url)
        return True
    except Exception:
        return False


def open_booking_search(query: str) -> bool:
    """Open a booking-oriented Google search for the given query."""
    if not query:
        return False
    q = urllib.parse.quote_plus(f"book {query}")
    url = f"https://www.google.com/search?q={q}"
    return open_url(url)
