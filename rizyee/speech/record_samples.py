"""
RIZYEE Custom Wake-Word Voice Recorder
======================================
Records short audio clips of your voice saying "RIZYEE" to train
your custom openWakeWord .onnx model.

Usage:
    python -m rizyee.speech.record_samples
"""

import os
import time
import wave
import sounddevice as sd
import numpy as np

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
DATA_DIR = os.path.join(PROJECT_ROOT, "voice_samples")


def record_samples(num_samples: int = 20, duration: float = 2.0, sample_rate: int = 16000):
    """
    Record `num_samples` audio clips of your voice saying the wake word.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 60)
    print("RIZYEE CUSTOM WAKE-WORD VOICE RECORDER")
    print("=" * 60)
    print(f"You will record {num_samples} audio clips.")
    print(f"Each clip will be {duration} seconds long.")
    print("When you hear the beep/prompt, clearly say 'RIZYEE'.")
    print("Press Enter to start...")
    try:
        input()
    except EOFError:
        pass

    for i in range(1, num_samples + 1):
        print(f"\n[{i}/{num_samples}] Get ready...")
        time.sleep(1.0)
        print("🎤 RECORDING... Say 'RIZYEE' now!")

        # Record audio using sounddevice
        audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
        sd.wait()  # Wait until recording is finished

        # Save to WAV file
        filename = os.path.join(DATA_DIR, f"rizyee_sample_{i:02d}.wav")
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(audio.tobytes())

        print(f"✔ Saved: {filename}")
        time.sleep(0.8)

    print("\n" + "=" * 60)
    print(f"SUCCESS! Recorded {num_samples} voice samples.")
    print(f"Your voice binary data is saved in: {DATA_DIR}")
    print("Next step: Upload these .wav clips to the openWakeWord Colab notebook to train your .onnx model!")
    print("=" * 60)


if __name__ == "__main__":
    record_samples()
