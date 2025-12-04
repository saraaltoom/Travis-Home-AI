import os
from core.voice_assistant import speak, listen
from core.emotion import detect_emotion_from_face
from core.face_store import recognize, ensure_owner_enrolled, get_owner_name
from core.hardware.serial_bridge import SerialBridge
from core.command_interpreter import handle_command
from core.calendar_manager import get_today_summary
from core import calendar_google
from core.reminder_manager import start_scheduler
from core.calendar_sync import start_google_calendar_sync


def normalize_emotion(e: str) -> str:
    e = (e or "").lower()
    mapping = {
        "happy": "happy",
        "angry": "angry",
        "sad": "sad",
        "neutral": "neutral",
        "surprise": "excited",
        "fear": "tired",
        "disgust": "sad",
    }
    return mapping.get(e, "neutral")


def emotion_to_serial_command(emotion: str) -> str:
    ne = normalize_emotion(emotion)


    if ne in ("happy", "excited",):
        return "emotion happy"
    if ne in ("angry", "disgust"):
        return "emotion sad"
    if ne in ("sad",):
        return "emotion sad"

    return "emotion neutral"


def main():

    owner_name = ensure_owner_enrolled(speak)


    speak("Scanning face...")
    user = recognize()
    emotion = detect_emotion_from_face()


    serial = SerialBridge(os.environ.get("TRAVIS_SERIAL_PORT", "COM4"))
    if serial.is_connected():

        serial.send(emotion_to_serial_command(emotion))


    if not user:
        speak("Access denied. Unknown face. Security locked.")
        return


    try:
        if serial.is_connected():
            serial.send("open door")
    except Exception:
        pass


    display_name = user or ""
    emo = normalize_emotion(emotion)
    english_emo = {
        "happy": "happy",
        "sad": "sad",
        "angry": "angry",
        "neutral": "neutral",
        "tired": "tired",
        "excited": "excited",
    }.get(emo, "neutral")
    if display_name:
        speak(f"Hello, {display_name}. You seem {english_emo} today.")
    else:
        speak(f"Hello. You seem {english_emo} today.")

    if english_emo not in ("happy", "sad", "neutral"):
        speak(f"Detected emotion: {english_emo}. I'll adjust lights accordingly.")

    if user == owner_name:

        if calendar_google.is_available():
            speak(calendar_google.today_summary())
        else:
            summary = get_today_summary()
            speak(summary)


    start_scheduler(speak)

    try:
        from core import calendar_google as cg
        if cg.is_available():
            start_google_calendar_sync(speak, minutes_before=30, poll_seconds=300)
    except Exception:
        pass

    speak("I'm ready. Awaiting your commands.")


    while True:
        text = listen()
        if not text:
            speak("Please say something.")
            continue
        if text.strip().lower() in ("quit", "exit"):
            speak("Goodbye.")
            break
        handle_command(text, serial, speak, owner_name=owner_name)


if __name__ == "__main__":
    main()
