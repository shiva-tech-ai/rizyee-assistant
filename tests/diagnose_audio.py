"""
RIZYEE audio diagnostic.
Checks the microphone → Vosk pipeline step by step so we can see
exactly where hearing breaks down.

Run with:  python -m tests.diagnose_audio
"""

import time
import json
import queue

import sounddevice as sd
from vosk import Model, KaldiRecognizer

from rizyee.speech.listener import MODEL_PATH, MODEL_NAME


def main():
    print("=" * 55)
    print("RIZYEE AUDIO DIAGNOSTIC")
    print("=" * 55)

    # ── Step 1: list audio devices ──
    print("\n[1] Audio devices on this machine:")
    devices = sd.query_devices()
    input_devices = []
    if isinstance(devices, dict):
        devices = [devices]
    try:
        default_input = sd.query_devices(kind="input")
        print(f"    Default input device: {default_input['name']}")
    except Exception as e:
        print(f"    Could not find a default input device: {e}")

    idx = 0
    for d in devices:
        if d.get("max_input_channels", 0) > 0:
            print(f"    #{idx}: {d['name']}  (in:{d['max_input_channels']}, "
                  f"default rate:{d['default_samplerate']})")
            input_devices.append(idx)
        idx += 1

    if not input_devices:
        print("\n!! No microphone/input devices found.")
        print("   Windows: Settings > Privacy > Microphone — make sure")
        print("   'Allow apps to access your microphone' is ON.")
        return

    # ── Step 2: load the model ──
    print(f"\n[2] Loading Vosk model: {MODEL_NAME or MODEL_PATH}")
    if not MODEL_PATH:
        print("!! No model found. Run: python -m rizyee.utils.download_model")
        return
    model = Model(MODEL_PATH)
    sample_rate = 16000
    recognizer = KaldiRecognizer(model, sample_rate)
    print("    Model loaded.")

    # ── Step 3: record 6 seconds and measure audio levels ──
    print("\n[3] Recording 6 seconds to check mic levels...")
    print("    >>> SPEAK NOW — say anything (e.g. 'hello rizyee') <<<")
    audio_queue = queue.Queue()

    def callback(indata, frames, t, status):
        if status:
            print(f"    [audio status] {status}")
        audio_queue.put(bytes(indata))

    chunks = []
    max_level = 0
    try:
        with sd.RawInputStream(samplerate=sample_rate, blocksize=8000,
                               dtype="int16", channels=1,
                               callback=callback):
            start = time.time()
            while time.time() - start < 6.0:
                try:
                    data = audio_queue.get(timeout=0.5)
                    chunks.append(data)
                    # measure peak volume in this chunk
                    import array
                    samples = array.array("h", data)
                    if samples:
                        peak = max(abs(s) for s in samples)
                        max_level = max(max_level, peak)
                except queue.Empty:
                    pass
    except Exception as e:
        print(f"!! Could not open the microphone: {e}")
        print("   This usually means another app is using the mic, or")
        print("   Windows microphone privacy is blocking access.")
        return

    # ── Step 4: report levels ──
    print(f"\n[4] Mic level check:")
    print(f"    Peak audio level captured: {max_level} (out of 32767)")
    if max_level < 100:
        print("    !! VERY QUIET — almost no sound captured.")
        print("       Check: mic not muted, close to your mouth,")
        print("       Windows mic boost / input volume turned up.")
    elif max_level < 1000:
        print("    - Quiet but audible. Speak louder or move closer.")
    else:
        print("    + Good levels — mic is clearly picking up your voice.")

    # ── Step 5: run recognition on what was captured ──
    print("\n[5] Running speech recognition on what was captured...")
    if not chunks:
        print("!! No audio was captured at all.")
        return

    full_text = ""
    for data in chunks:
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            t = result.get("text", "").strip()
            if t:
                full_text += " " + t
    # Final partial result
    partial = json.loads(recognizer.FinalResult())
    t = partial.get("text", "").strip()
    if t:
        full_text += " " + t

    full_text = full_text.strip()
    print(f"\n    Recognized text: '{full_text}'")
    if full_text:
        print("    + SUCCESS — RIZYEE heard you.")
    else:
        print("    - No words recognized from the audio.")
        print("      If levels were good, the model may need clearer speech")
        print("      or a quieter room. If levels were low, fix the mic first.")

    print("\n" + "=" * 55)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 55)


if __name__ == "__main__":
    main()
