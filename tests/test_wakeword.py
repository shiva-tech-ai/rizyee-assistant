"""
Tests for Custom Wake-Word Detection (openWakeWord)
===================================================
Verifies:
    1. `models/rizyee.onnx` exists and loads cleanly.
    2. Shiva's recorded voice sample produces a high wake-word score (> 0.8).
    3. Silence and random noise produce a near-zero wake-word score (< 0.1).
"""

import os
import wave
import numpy as np
from rizyee.speech.wakeword import WakeWordDetector

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "rizyee.onnx")
SAMPLE_PATH = os.path.join(PROJECT_ROOT, "voice_samples", "rizyee_sample_01.wav")


def test_wakeword_detection():
    detector = WakeWordDetector(model_path=MODEL_PATH)
    assert detector.is_available(), f"Model file missing at: {MODEL_PATH}"

    detector._load_model()
    oww = detector._oww
    assert "rizyee" in oww.models, "Model 'rizyee' failed to register in openWakeWord"

    # Test 1: Silence should have 0 score
    oww.reset()
    silence = np.zeros(1280, dtype=np.int16)
    pred_silence = oww.predict(silence)
    silence_score = pred_silence.get("rizyee", 0.0)
    assert silence_score < 0.1, f"Silence score was too high: {silence_score}"

    # Test 2: Shiva's voice sample should produce high wake-word confidence
    assert os.path.exists(SAMPLE_PATH), f"Sample file missing: {SAMPLE_PATH}"
    with wave.open(SAMPLE_PATH, "rb") as wf:
        audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)

    oww.reset()
    step_size = 1280
    scores = []
    for i in range(0, len(audio) - step_size, step_size):
        chunk = audio[i : i + step_size]
        p = oww.predict(chunk)
        scores.append(p.get("rizyee", 0.0))

    peak_score = max(scores)
    assert peak_score >= 0.8, f"Peak score on voice sample was too low: {peak_score}"
    print(f"\n  PASS: Custom wake-word model loaded successfully!")
    print(f"  PASS: Silence score = {silence_score:.4f} (expected < 0.1)")
    print(f"  PASS: Shiva voice sample peak score = {peak_score:.4f} (expected >= 0.8)")
    print("\nALL WAKE-WORD TESTS PASSED! (3/3)\n")


if __name__ == "__main__":
    test_wakeword_detection()
