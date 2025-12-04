import os
import traceback
import pyttsx3
import time
import json
import asyncio


def _select_english_voice(engine):
    try:
        voices = engine.getProperty('voices') or []

        for v in voices:
            name = (getattr(v, 'name', '') or '').lower()
            lang = ''.join(getattr(v, 'languages', []) or []).lower()
            vid = (getattr(v, 'id', '') or '').lower()
            if 'zira' in name or 'en-us' in lang or 'en_us' in vid or 'english' in name:
                engine.setProperty('voice', v.id)
                return

        if voices:
            engine.setProperty('voice', voices[0].id)
    except Exception:
        pass


def _play_chime():
    try:
        base_dir = os.path.dirname(__file__)

        wav_path = os.environ.get("TRAVIS_CHIME")
        if not wav_path or not os.path.isfile(wav_path):
            return
        try:
            from playsound import playsound
            playsound(wav_path, block=False)
            return
        except Exception:
            pass
        try:
            import winsound
            winsound.PlaySound(wav_path, winsound.SND_ASYNC | winsound.SND_FILENAME)
        except Exception:
            pass
    except Exception:
        pass


def speak(text):
    if not text:
        return
    print(f"[Travis says]: {text}")


    engine_pref = (os.environ.get('TRAVIS_TTS_ENGINE', 'auto') or 'auto').lower()
    voice_hint = os.environ.get('TRAVIS_TTS_VOICE') or os.environ.get('TRAVIS_TTS_VOICE_HINT') or ''
    base_dir = os.path.dirname(__file__)

    if engine_pref in ('auto', 'edge', 'edge-tts', 'edge_tts'):
        try:
            import edge_tts

            async def gen(tts_text: str, voice_name: str, out_path: str):
                communicate = edge_tts.Communicate(tts_text, voice=voice_name)
                with open(out_path, 'wb') as f:
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            f.write(chunk["data"])

            voice_name = voice_hint or 'en-US-JennyNeural'
            out_path = os.path.join(base_dir, '_edge_tts.mp3')
            try:
                asyncio.run(gen(str(text), voice_name, out_path))
            except RuntimeError:

                loop = asyncio.new_event_loop()
                loop.run_until_complete(gen(str(text), voice_name, out_path))
                loop.close()

            _play_chime()
            try:
                from playsound import playsound
                playsound(out_path)
                return
            except Exception:
                pass
        except Exception:

            pass


    try:
        _play_chime()
        engine = pyttsx3.init()
        engine.setProperty('rate', 165)
        engine.setProperty('volume', 1.0)

        hint = voice_hint.lower()
        if hint:
            try:
                for v in engine.getProperty('voices') or []:
                    name = (getattr(v, 'name', '') or '').lower()
                    vid = (getattr(v, 'id', '') or '').lower()
                    if hint in name or hint in vid:
                        engine.setProperty('voice', v.id)
                        break
            except Exception:
                pass
        else:
            _select_english_voice(engine)
        engine.say(str(text))
        engine.runAndWait()
        return
    except Exception:
        pass


    try:
        base_dir = os.path.dirname(__file__)
        tts_path = os.path.join(base_dir, "_tts.wav")
        engine = pyttsx3.init()
        engine.setProperty('rate', 165)
        engine.setProperty('volume', 1.0)
        _select_english_voice(engine)
        engine.save_to_file(str(text), tts_path)
        engine.runAndWait()

        try:
            from playsound import playsound
            playsound(tts_path)
            return
        except Exception:
            pass

        try:
            import winsound
            winsound.PlaySound(tts_path, winsound.SND_FILENAME)
            return
        except Exception:
            pass
    except Exception:
        print("[Voice Error]: synthesis failed")
        traceback.print_exc()


def listen(timeout_seconds: int = 8) -> str:
    """Listen from microphone using Vosk if available; fallback to keyboard input.

    Returns the recognized text (lowercased as produced by Vosk), or empty string.
    """

    try:
        import sounddevice as sd
        import vosk
        import queue


        base_dir = os.path.dirname(os.path.dirname(__file__))
        model_path = os.path.join(base_dir, 'models', 'vosk-model-small-en-us-0.15')
        if not os.path.isdir(model_path):
            raise RuntimeError('Vosk model not found')

        model = vosk.Model(model_path)
        q: "queue.Queue[bytes]" = queue.Queue()

        def callback(indata, frames, time_info, status):
            if status:
                print(status)
            q.put(bytes(indata))


        samplerates = [16000, 44100, 48000]
        stream = None
        rec = None
        for sr in samplerates:
            try:
                stream = sd.RawInputStream(samplerate=sr, blocksize=sr // 2, dtype='int16',
                                           channels=1, callback=callback)
                rec = vosk.KaldiRecognizer(model, sr)
                break
            except Exception:
                stream = None
                rec = None
                continue
        if stream is None or rec is None:
            raise RuntimeError('No audio input device or unsupported sample rate')

        print('Listening... speak your command')
        text = ''
        t0 = time.time()
        with stream:
            while time.time() - t0 < timeout_seconds:
                data = q.get()
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = (result.get('text') or '').strip()
                    if text:
                        break

            if not text:
                final = json.loads(rec.FinalResult()).get('text', '')
                text = (final or '').strip()
        return text
    except Exception:

        try:
            return input("You: ")
        except Exception:
            return ""
