"""
RIZYEE Listener (Speech-to-Text)
=================================
Uses Vosk + SoundDevice to listen through your microphone
and convert spoken words into text — completely offline!

Usage:
    from rizyee.speech.listener import Listener

    listener = Listener()
    text = listener.listen()   # Blocks until you say something
    print(f"You said: {text}")
"""

import os
import json
import queue

import numpy as np
import sounddevice as sd
from vosk import Model, KaldiRecognizer

from rizyee.utils.logger import get_logger

logger = get_logger("speech.listener")

# ── Find the Vosk model ──
# RIZYEE prefers the more accurate "lgraph" model (vosk-model-en-us-0.22-lgraph,
# ~450 MB). If that isn't downloaded yet, it falls back to the small model
# (vosk-model-small-en-us-0.15, ~40 MB) so the app still runs while you
# download the better one. Either way, no code change needed.
# This file is at: rizyee/speech/listener.py  →  project root is ../../
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
_MODELS_DIR = os.path.join(PROJECT_ROOT, "models")

# Best → worst order. We pick the first one that exists on disk.
_CANDIDATE_MODELS = [
    "vosk-model-en-us-0.22-lgraph",   # ~450 MB, more accurate (preferred)
    "vosk-model-en-us-0.22",          # ~1.8 GB, most accurate
    "vosk-model-small-en-us-0.15",    # ~40 MB, basic fallback
]


def _find_model_path() -> str:
    """Return the path of the best available Vosk model, or '' if none."""
    for name in _CANDIDATE_MODELS:
        path = os.path.join(_MODELS_DIR, name)
        if os.path.isdir(path):
            return path
    return ""


# Resolved once at import time so the app starts on whatever is installed.
MODEL_PATH = _find_model_path()
# The model folder name (e.g. "vosk-model-en-us-0.22-lgraph"), for logging.
MODEL_NAME = os.path.basename(MODEL_PATH) if MODEL_PATH else ""


class Listener:
    """
    Listens to the microphone and converts speech to text.

    How it works (simplified):
        1. Opens your microphone using SoundDevice
        2. Feeds audio chunks to Vosk (the speech-to-text AI)
        3. Vosk figures out what words you said
        4. Returns the text as a Python string

    Attributes:
        model:      The Vosk AI model (loaded from disk)
        recognizer: The Vosk recognizer that processes audio
        audio_queue: A queue that holds audio chunks from the mic
    """

    def __init__(self):
        """
        Set up the listener.

        Steps:
            1. Check that the Vosk model exists
            2. Load the model into memory
            3. Create a recognizer with 16kHz sample rate
            4. Create a queue to hold audio data
        """
        # ── Check model exists ──
        # MODEL_PATH is "" if none of the candidate models are on disk.
        if not MODEL_PATH:
            logger.error("No Vosk speech model found in the models/ folder.")
            logger.error("Run this first:  python -m rizyee.utils.download_model")
            raise FileNotFoundError(
                "No Vosk model found. Run: python -m rizyee.utils.download_model"
            )

        # ── Load the model ──
        logger.info(f"Loading speech recognition model: {MODEL_NAME}")
        self.model = Model(MODEL_PATH)

        # ── Create recognizer ──
        # 16000 = sample rate (16kHz) — standard for speech recognition
        # Higher = better quality but more processing power needed
        self.sample_rate = 16000
        self.recognizer = KaldiRecognizer(self.model, self.sample_rate)

        # ── Audio queue ──
        # The microphone callback puts audio data here,
        # and listen() reads from here. This prevents data loss
        # because the mic and recognizer run at different speeds.
        self.audio_queue = queue.Queue()

        logger.info("Listener ready! Microphone will be used for input.")

    def _audio_callback(self, indata, frames, time, status):
        """
        Called automatically whenever the microphone captures audio.

        This is a "callback" — SoundDevice calls this function
        every few milliseconds with a new chunk of audio data.
        We just put the data into our queue for later processing.

        Args:
            indata: Raw audio bytes from the microphone
            frames: Number of audio frames in this chunk
            time:   Timestamp info (we don't use this)
            status: Error status (we log if there's a problem)
        """
        if status:
            logger.warning(f"Audio status: {status}")

        # Amplify quiet/soft voices (1.5x boost) so Vosk catches low speech easily
        import array
        try:
            samples = array.array("h", indata)
            amplified = array.array("h", [
                max(-32768, min(32767, int(s * 1.5))) for s in samples
            ])
            self.audio_queue.put(amplified.tobytes())
        except Exception:
            self.audio_queue.put(bytes(indata))

    def listen(self, timeout: float = 10.0) -> str:
        """
        Listen through the microphone and return what was said.

        Args:
            timeout: Max seconds to listen before giving up.
                     Default is 10 seconds.

        Returns:
            The recognized text as a string (lowercase).
            Returns "" if nothing was understood.

        How it works:
            1. Opens the microphone stream
            2. Reads audio chunks from the queue
            3. Feeds them to the Vosk recognizer
            4. When Vosk detects a complete sentence, returns it
            5. If timeout is reached, returns whatever was heard
        """
        # Clear any old audio data from the queue
        while not self.audio_queue.empty():
            self.audio_queue.get()

        # ── Fresh recognizer for this call ──
        # Vosk's recognizer keeps partial state between calls. If we
        # reuse the same one, audio from the last command can bleed
        # into this one and garble the result. Creating a fresh
        # recognizer each call is cheap and avoids that.
        self.recognizer = KaldiRecognizer(self.model, self.sample_rate)

        logger.info("Listening... (speak now)")

        recognized_text = ""

        # ── Open microphone ──
        # RawInputStream = raw audio bytes (not NumPy arrays)
        # channels=1 = mono (one mic, not stereo)
        # dtype="int16" = 16-bit audio (CD quality for speech)
        # blocksize=8000 = process 0.5 seconds of audio at a time
        with sd.RawInputStream(
            samplerate=self.sample_rate,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=self._audio_callback,
        ):
            # ── Process audio until timeout ──
            import time as time_module

            start_time = time_module.time()

            while True:
                elapsed = time_module.time() - start_time
                if elapsed > timeout:
                    logger.info("Listening timed out.")
                    break

                try:
                    # Get audio data from the queue
                    # timeout=0.5 means: wait up to 0.5 sec for data
                    data = self.audio_queue.get(timeout=0.5)
                except queue.Empty:
                    # No audio data received — mic might be muted
                    continue

                # ── Feed audio to Vosk ──
                # AcceptWaveform returns True when it detects
                # a complete sentence/phrase
                if self.recognizer.AcceptWaveform(data):
                    # Complete sentence detected!
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "").strip()

                    if text:
                        recognized_text = text
                        logger.info(f'Heard: "{text}"')
                        break  # Got a sentence, stop listening

            # ── Check for partial results ──
            # If we timed out, check if Vosk partially heard something
            if not recognized_text:
                partial = json.loads(self.recognizer.FinalResult())
                text = partial.get("text", "").strip()
                if text:
                    recognized_text = text
                    logger.info(f'Heard (partial): "{text}"')

        return recognized_text

    def listen_continuous(self):
        """
        Generator that continuously listens and yields text.

        Usage:
            for text in listener.listen_continuous():
                print(f"You said: {text}")

        This is a Python generator — it keeps running forever
        and yields text each time you say something.
        """
        logger.info("Continuous listening started. Say something!")
        while True:
            text = self.listen(timeout=5.0)
            if text:
                yield text
