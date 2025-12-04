

import sounddevice as sd
import vosk
import queue
import json

q = queue.Queue()

model = vosk.Model("models/vosk-model-small-en-us-0.15")

def callback(indata, frames, time, status):
    if status:
        print(status)
    q.put(bytes(indata))

def listen_for_wake_word():
    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                           channels=1, callback=callback):
        rec = vosk.KaldiRecognizer(model, 16000)

        print("Waiting for wake word...")
        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "")
                if "travis" in text.lower():
                    print("Wake word detected!")
                    return
