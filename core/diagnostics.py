"""
Quick diagnostics for Travis Project.

Usage:
  python -m core.diagnostics [--serial COM4] [--no-camera] [--no-audio]
"""

import argparse
import sys
import os


def check_imports():
    mods = [
        "core.voice_assistant",
        "core.command_interpreter",
        "core.face_store",
        "core.emotion",
        "core.device_api",
        "core.chat_with_ai",
        "core.analyze",
        "core.ollama_api",
        "core.reminder_manager",
        "core.browser_helper",
        "core.ai_interpreter",
    ]
    for m in mods:
        __import__(m)
    print("[OK] Imports")


def check_tts():
    from core.voice_assistant import speak
    speak("Diagnostics: text to speech is working.")
    print("[OK] TTS")


def check_vosk():
    try:
        import vosk
        import sounddevice
        base = os.path.dirname(os.path.dirname(__file__))
        model_path = os.path.join(base, 'models', 'vosk-model-small-en-us-0.15')
        if not os.path.isdir(model_path):
            print("[WARN] Vosk model not found; speech input may fallback to keyboard.")
        else:
            print("[OK] Vosk & model present")
    except Exception as e:
        print(f"[WARN] Vosk not available: {e}")


def check_serial(port: str):
    from core.hardware.serial_bridge import SerialBridge
    sb = SerialBridge(port)
    if not sb.is_connected():
        print(f"[FAIL] Serial not connected on {port}")
        return

    tests = [
        "light on top",
        "light on bottom",
        "light off top",
        "light off bottom",
    ]
    for t in tests:
        sb.send(t)
        ack = sb.readline(timeout_s=1.5)
        print(f"[Serial] {t} -> {ack or '(no ack)'}")
    print("[OK] Serial basic test finished")


def check_ollama():
    from core.ollama_api import ask_ollama
    resp = ask_ollama("Say 'pong' only.")
    print("[OK] Ollama resp:", (resp or "").strip()[:80])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--serial", default=None, help="Serial port to test, e.g. COM4")
    ap.add_argument("--no-camera", action="store_true")
    ap.add_argument("--no-audio", action="store_true")
    args = ap.parse_args()

    try:
        check_imports()
        if not args.no_audio:
            check_tts()
            check_vosk()
        if args.serial:
            check_serial(args.serial)
        check_ollama()
        print("Diagnostics completed.")
    except Exception as e:
        print("Diagnostics error:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
