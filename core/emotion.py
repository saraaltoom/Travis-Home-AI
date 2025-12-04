import os
import cv2


def _map_emotion(label: str) -> str:
    l = (label or "").lower()
    if l in ("happy",):
        return "happy"
    if l in ("angry",):
        return "angry"
    if l in ("sad",):
        return "sad"
    if l in ("surprise",):
        return "excited"
    if l in ("fear",):
        return "tired"
    if l in ("disgust",):
        return "sad"
    return "neutral"


def _try_deepface(frame_bgr):
    try:
        from deepface import DeepFace
    except Exception as e:
        print(f"[Emotion] DeepFace not available: {e}")
        return None
    try:
        res = DeepFace.analyze(frame_bgr, actions=["emotion"], enforce_detection=False)

        if isinstance(res, list) and res:
            res = res[0]
        emo = (res or {}).get("dominant_emotion")
        scores = (res or {}).get("emotion") or {}
        if emo:
            return emo, float(scores.get(emo, 0.0))
    except Exception as e:
        print(f"[Emotion] DeepFace analyze failed: {e}")
    return None


def _try_fer(frame_bgr):
    try:
        from fer import FER
    except Exception as e:
        print(f"[Emotion] FER not available: {e}")
        return None
    try:
        detector = FER(mtcnn=False)
        result = detector.top_emotion(frame_bgr)
        return result
    except Exception as e:
        print(f"[Emotion] FER analyze failed: {e}")
        return None


def detect_emotion_from_face():
    frames_to_sample = int(os.environ.get("TRAVIS_EMOTION_FRAMES", "5"))

    cam = cv2.VideoCapture(0)
    try:

        try:
            cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        except Exception:
            pass

        votes = {}
        best = ("neutral", 0.0)
        for _ in range(max(1, frames_to_sample)):
            ok, frame = cam.read()
            if not ok:
                continue


            try:
                h, w = frame.shape[:2]
                scale = 480.0 / max(h, w)
                if scale < 1.0:
                    frame_bgr = cv2.resize(frame, (int(w * scale), int(h * scale)))
                else:
                    frame_bgr = frame
            except Exception:
                frame_bgr = frame


            got = _try_deepface(frame_bgr)
            if not got:
                got = _try_fer(frame_bgr)
            if not got:
                continue

            label, score = got
            mapped = _map_emotion(label)
            votes[mapped] = votes.get(mapped, 0) + float(score or 0.0)
            if (score or 0.0) > best[1]:
                best = (mapped, float(score or 0.0))

        if votes:

            final = max(votes.items(), key=lambda kv: kv[1])[0]
            print(f"[Emotion] Detected: {final} ({votes[final]:.2f} agg)")
            return final
        else:
            print("[Emotion] Could not detect emotion. Falling back to neutral.")
            return "neutral"
    finally:
        try:
            cam.release()
        except Exception:
            pass
