import os
import requests


def ask_ollama(prompt: str) -> str:
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", "mistral")
    payload = {
        "model": model,
        "prompt": prompt or "",
        "stream": False,
        "keep_alive": os.environ.get("OLLAMA_KEEP_ALIVE", "1h"),
        "options": {
            "num_ctx": int(os.environ.get("OLLAMA_NUM_CTX", "4096")),
            "temperature": float(os.environ.get("OLLAMA_TEMPERATURE", "0.2")),
        },
    }
    try:
        response = requests.post(f"{host}/api/generate", json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "Sorry, I didn't get that.")
    except Exception:
        return "I couldn't connect to my brain. Try restarting Ollama."
