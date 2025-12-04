
import face_recognition
import cv2
import os
import pickle
from typing import Dict, List, Any



FACES_DIR = "faces"
ENCODINGS_PATH = os.path.join(FACES_DIR, "encodings.pkl")
OWNER_NAME_PATH = os.path.join(FACES_DIR, "owner.txt")

def load_encodings():
    if not os.path.exists(ENCODINGS_PATH):
        return {}
    with open(ENCODINGS_PATH, "rb") as f:
        data = pickle.load(f)

    try:
        norm: Dict[str, List[Any]] = {}
        for name, enc in (data or {}).items():
            if enc is None:
                continue
            if isinstance(enc, list):
                norm[name] = enc
            else:
                norm[name] = [enc]
        return norm
    except Exception:
        return data

def save_encodings(data):
    os.makedirs(FACES_DIR, exist_ok=True)
    with open(ENCODINGS_PATH, "wb") as f:
        pickle.dump(data, f)


def get_owner_name():
    try:
        if os.path.exists(OWNER_NAME_PATH):
            with open(OWNER_NAME_PATH, "r", encoding="utf-8") as f:
                name = f.read().strip()
                return name or None
    except Exception:
        pass
    return None


def set_owner_name(name: str):
    os.makedirs(FACES_DIR, exist_ok=True)
    with open(OWNER_NAME_PATH, "w", encoding="utf-8") as f:
        f.write((name or "Owner").strip())

def recognize(max_tries: int = 6, tolerance: float = 0.58):
    data = load_encodings()
    if not data:
        print("[FaceStore] No stored faces.")
        return None

    cam = cv2.VideoCapture(0)
    try:
        for _ in range(max_tries):
            ret, frame = cam.read()
            if not ret:
                continue


            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            try:
                h, w = rgb.shape[:2]
                scale = 0.5 if max(h, w) > 720 else 1.0
                if scale < 1.0:
                    rgb_small = cv2.resize(rgb, (int(w * scale), int(h * scale)))
                else:
                    rgb_small = rgb
            except Exception:
                rgb_small = rgb
            face_locations = face_recognition.face_locations(rgb_small, model="hog")
            encodings = face_recognition.face_encodings(rgb_small, face_locations)

            for encoding in encodings:

                best_name = None
                best_dist = 1.0
                for name, stored_list in data.items():
                    encs = stored_list if isinstance(stored_list, list) else [stored_list]
                    try:
                        dists = face_recognition.face_distance(encs, encoding)
                        dist = float(min(dists)) if len(dists) else 1.0
                        if dist < best_dist:
                            best_dist = dist
                            best_name = name
                    except Exception:
                        continue
                if best_name is not None and best_dist <= tolerance:
                    print(f"[FaceStore] Recognized: {best_name} (dist={best_dist:.2f})")
                    return best_name
    finally:
        cam.release()

    print("[FaceStore] Face not recognized.")
    return None

def capture_and_add(name="owner", attempts: int = 15, max_samples: int = 5):
    cam = cv2.VideoCapture(0)
    try:
        samples: List[Any] = []
        for _ in range(attempts):
            ret, frame = cam.read()
            if not ret:
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            try:
                h, w = rgb.shape[:2]
                scale = 0.5 if max(h, w) > 720 else 1.0
                if scale < 1.0:
                    rgb_small = cv2.resize(rgb, (int(w * scale), int(h * scale)))
                else:
                    rgb_small = rgb
            except Exception:
                rgb_small = rgb

            face_locations = face_recognition.face_locations(rgb_small, model="hog")
            if not face_locations:
                continue
            encodings = face_recognition.face_encodings(rgb_small, face_locations)
            if not encodings:
                continue

            for enc in encodings:
                if len(samples) == 0:
                    samples.append(enc)
                else:
                    import numpy as np
                    dists = face_recognition.face_distance(samples, enc)
                    if float(min(dists)) > 0.35:
                        samples.append(enc)
                if len(samples) >= max_samples:
                    break
            if len(samples) >= max_samples:
                break
        if samples:
            data = load_encodings()
            data[name] = samples
            save_encodings(data)
            print(f"[FaceStore] Added face for: {name} with {len(samples)} samples.")
            return True
    finally:
        cam.release()
    print("[FaceStore] Failed to capture/encode face.")
    return False


def ensure_owner_enrolled(speak=print):
    """Ensure an owner face and name exist; if not, capture from camera.

    - Prompts for a display name (used for greetings), default 'Owner'.
    - Captures a single frame from the default camera and stores encoding.
    """
    owner_name = get_owner_name()
    enc = load_encodings()
    if owner_name and owner_name in enc:
        return owner_name


    try:
        speak("First-time setup: registering the owner's face. Please look at the camera.")
    except Exception:
        pass


    try:
        input_name = input("Enter your name (for greetings) [Owner]: ").strip()
    except Exception:
        input_name = ""
    if not input_name:
        input_name = "Owner"

    ok = capture_and_add(input_name)
    if ok:
        set_owner_name(input_name)
        return input_name
    else:

        set_owner_name(input_name)
        return input_name


def is_owner(name: str) -> bool:
    return bool(name and name == get_owner_name())
