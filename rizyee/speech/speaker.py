"""
RIZYEE Speaker (Text-to-Speech)
================================
Makes RIZYEE speak out loud using pyttsx3.
pyttsx3 works completely offline — no internet needed!

Usage:
    from rizyee.speech.speaker import speak
    speak("Hello Shiva, I am RIZYEE!")
"""

import pyttsx3
from rizyee.utils.logger import get_logger

# Create a logger for this module
logger = get_logger("speech.speaker")

# ── Create the TTS engine (one global instance) ──
# We create it once and reuse it. Creating a new engine
# each time would be slow and waste memory.
_engine = None


def _get_engine() -> pyttsx3.Engine:
    """
    Get or create the TTS engine.

    Why a function instead of just a global variable?
    Because if pyttsx3 fails to initialize (e.g., missing
    audio drivers), we want to catch the error cleanly
    instead of crashing the whole app on import.
    """
    global _engine

    if _engine is None:
        logger.info("Initializing text-to-speech engine...")
        _engine = pyttsx3.init()

        # ── Configure the voice ──
        # Rate = words per minute. Default is ~200, which is fast.
        # 160 sounds natural and clear.
        _engine.setProperty("rate", 160)

        # Volume: 0.0 (silent) to 1.0 (max). 0.9 is comfortably loud.
        _engine.setProperty("volume", 0.9)

        # Try to pick a female voice (usually sounds clearer on Windows).
        # If only one voice is available, it uses the default.
        voices = _engine.getProperty("voices")
        if len(voices) > 1:
            # voices[1] is typically the female voice on Windows
            _engine.setProperty("voice", voices[1].id)
            logger.info(f"Voice set to: {voices[1].name}")
        else:
            logger.info(f"Voice set to: {voices[0].name}")

        logger.info("Text-to-speech engine ready!")

    return _engine


def speak(text: str) -> None:
    """
    Make RIZYEE say something out loud AND show it as text on screen.

    Voice + text together means you can always tell what RIZYEE said even
    if the audio was unclear, the room was loud, or the mic missed it.

    Args:
        text: The sentence to speak.

    Example:
        speak("Yes Shiva, I'm ready.")

    How it works:
        1. Print the text to the terminal (so you can read it)
        2. Get the TTS engine
        3. Queue the text and speak it
    """
    if not text or not text.strip():
        return  # Nothing to say

    logger.info(f'Speaking: "{text}"')

    # ── Show the reply as text on screen ──
    # A clear prefix (RIZYEE:) makes it stand out from the listening
    # prompt, so you can always read what RIZYEE just said.
    print(f"RIZYEE: {text}")

    engine = _get_engine()

    # say() queues the text, runAndWait() actually speaks it
    engine.say(text)
    engine.runAndWait()


def stop_speaking() -> None:
    """Stop the TTS engine if it's currently speaking."""
    if _engine is not None:
        _engine.stop()
        logger.info("Speech stopped.")
