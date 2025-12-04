

from core.face_store import recognize, capture_and_add, load_encodings, get_owner_name, ensure_owner_enrolled
from core.voice_assistant import speak

OWNER = get_owner_name() or "Owner"

def main():

    ensure_owner_enrolled(speak)
    encodings = load_encodings()

    if not encodings:
        print("[AddFace] No faces registered yet. Registering you as the Owner.")
        speak("No faces registered yet. Registering you as the Owner.")
        success = capture_and_add(OWNER)
        if success:
            print(f"[AddFace] {OWNER} has been added as Owner.")
            speak(f"{OWNER}, you have been registered as the Owner.")
        else:
            print("[AddFace] Failed to register Owner.")
            speak("Failed to register Owner.")
        return

    print("[AddFace] Please look at the camera for verification.")
    speak("Look at the camera for verification.")
    user = recognize()

    if user != OWNER:
        speak("Access denied. Only the owner can add faces.")
        print("[AddFace] Unauthorized access by:", user)
        return

    speak("Who's joining?")
    name = input("Enter the name of the new user: ")
    success = capture_and_add(name)

    if success:
        speak(f"{name} added successfully.")
        print(f"{name} added successfully.")
    else:
        speak("Failed to add face. Try again.")
        print("Failed to add face. Try again.")

if __name__ == "__main__":
    main()
