"""
RIZYEE — Main Entry Point
===========================
Run with:  python -m rizyee

This is the starting point of the entire assistant.
Milestone 3: RIZYEE can now LISTEN, SPEAK, and ACT on commands!
Milestone 4: RIZYEE can now REMEMBER facts and set REMINDERS.
Milestone 5: RIZYEE can now ANSWER questions via a local AI (Ollama).

Flow:
    1. Print welcome banner
    2. Speak greeting
    3. Wait for wake word "rizyee"
    4. Listen for a command
    5. Parse the command into (action, target)
    6. Execute the action (open app, remember, answer a question, ...)
    7. Go back to step 3 (or shut down on "goodbye")
"""

import sys
from rizyee.utils.logger import get_logger
from rizyee.speech.speaker import speak
from rizyee.speech.listener import Listener
from rizyee.speech.wakeword import WakeWordDetector
from rizyee.brain.commander import parse_command
from rizyee.actions.executor import execute
from rizyee.memory.store import MemoryStore
from rizyee.memory.checker import ReminderChecker
from rizyee.brain.chat import Chat

# Create a logger for the main module
logger = get_logger("main")

# ── Wake word ──
# RIZYEE only responds after hearing this word.
# "rizyee" is a made-up word, so Vosk (which only knows real
# dictionary words) often mishears it as a similar-sounding real
# word. We accept a few common mishearings as the wake word too.
# Watch the logs — if RIZYEE keeps mishearing your name a certain
# way, add that word to WAKE_ALIASES.
WAKE_WORD = "rizyee"
WAKE_ALIASES = {"rizyee", "rosie", "rees", "reece", "reese", "dizzy"}


def is_wake_word(text: str) -> bool:
    """
    Check whether the spoken text is a wake-word attempt.

    Why aliases: Vosk only outputs real dictionary words, so a
    made-up name like "rizyee" comes back as whatever real word
    sounds closest. We match against a small set of likely
    mishearings.

    Why the length cap: when you say the wake word, you usually
    say it alone or with a filler like "hey". If Vosk transcribes
    a long sentence, it's probably not a wake attempt — even if
    it happens to contain an alias word.

    Args:
        text: What Vosk recognized (may be empty).

    Returns:
        True if this looks like the user saying the wake word.
    """
    if not text:
        return False
    words = text.lower().split()
    # A wake attempt is short — just the name, maybe with "hey".
    if len(words) > 3:
        return False
    return any(word in WAKE_ALIASES for word in words)


def print_banner() -> None:
    """Print a cool ASCII banner when RIZYEE starts."""
    banner = r"""
    ╔══════════════════════════════════════════╗
    ║                                          ║
    ║      ██████  ██ ███████ ██    ██ ███████ ║
    ║      ██   ██ ██    ██    ██  ██  ██      ║
    ║      ██████  ██   ██      ████   █████   ║
    ║      ██   ██ ██  ██        ██    ██      ║
    ║      ██   ██ ██ ███████    ██    ███████ ║
    ║                                          ║
    ║     Personal AI Voice Assistant v0.3     ║
    ║            Built by Shiva                ║
    ╚══════════════════════════════════════════╝
    """
    print(banner)


def command_loop(listener: Listener, store: MemoryStore, chat: Chat) -> None:
    """
    The main loop — RIZYEE listens, understands, and acts.

    Milestone 3: RIZYEE now parses commands and executes them
    instead of just repeating what you said.
    Milestone 4: RIZYEE can remember facts and set reminders.
    Milestone 5: RIZYEE can answer questions via a local AI (Ollama).
    Milestone 6: RIZYEE opens websites and asks before risky actions.

    How it works:
        1. Continuously listen (5-second windows) for the wake word
        2. If heard → say "Yes Shiva." and listen for a command
        3. Parse the command into (action, target)
        4. Execute the action (open app/site, remember, answer, ...)
        5. If the action was "goodbye", stop the loop and shut down
        6. Otherwise, go back to waiting for the wake word

    Args:
        listener: The Listener object that handles the microphone.
        store:    The MemoryStore for facts and reminders (Milestone 4).
        chat:     The Chat client for AI answers (Milestone 5).
    """
    logger.info(f'Waiting for wake word: "{WAKE_WORD}"')
    logger.info("Say 'RIZYEE' to activate, or Ctrl+C to exit.\n")

    # Initialize openWakeWord neural network detector
    detector = WakeWordDetector()
    use_onnx = detector.is_available()
    if use_onnx:
        logger.info("Using custom openWakeWord neural network (models/rizyee.onnx)")
        print("⚡ Mode: Ultra-fast openWakeWord AI enabled (Trained on your voice)")
    else:
        logger.info("Custom ONNX model not found, falling back to Vosk wake word.")

    # ── Permission callback for risky actions ──
    # When a risky action (like closing an app) needs your OK, the
    # executor calls this. It speaks the question, listens for your
    # answer, and returns True only if you said yes.
    YES_WORDS = {"yes", "yeah", "yep", "sure", "okay", "ok", "go ahead",
                 "do it", "please", "confirm", "affirmative"}
    NO_WORDS = {"no", "nope", "stop", "cancel", "don't", "dont", "wait"}

    def ask_permission(question: str) -> bool:
        """Speak a yes/no question and listen for the answer."""
        speak(question)
        answer = listener.listen(timeout=6.0)
        if not answer:
            speak("I didn't hear an answer, so I'll leave it.")
            return False
        words = set(answer.lower().split())
        if words & NO_WORDS:
            return False
        if words & YES_WORDS:
            return True
        # Unclear answer → treat as no for safety.
        speak(f"I heard {answer}, so I'll leave it for now.")
        return False

    def handle_command(command: str) -> bool:
        """Parse and execute one command. Returns False to shut down."""
        if not command:
            speak("I didn't catch that. Please try again.")
            return True
        logger.info(f'Command received: "{command}"')
        print(f"You said: {command}")  # show what was heard, as text
        action, target = parse_command(command)
        return execute(
            action, target, speak,
            store=store, chat=chat, ask_permission=ask_permission,
        )

    while True:
        # ── Step 1 & 2: Listen for the wake word ──
        if use_onnx:
            detected = detector.wait_for_wake(threshold=0.5, timeout=None)
            if not detected:
                continue
        else:
            print("🎤 Listening for 'RIZYEE'...           ", end="\r", flush=True)
            text = listener.listen(timeout=5.0)
            if not text:
                continue
            print(f"\n[Heard: '{text}']")
            if not is_wake_word(text):
                logger.info(f'Heard "{text}" — not the wake word, ignoring.')
                continue

        # ── Step 3: Wake word detected! ──
        logger.info("Wake word detected.")
        print("\n✨ Wake word detected! Say your command...        ")
        speak("Yes Shiva.")

        # ── Step 4: Listen for the actual command ──
        print("🎤 Listening for command...             ", end="\r", flush=True)
        command = listener.listen(timeout=8.0)
        if command:
            print(f"\n[Heard Command: '{command}']")

        # ── Step 5 & 6: Parse and execute ──
        should_keep_running = handle_command(command)

        if not should_keep_running:
            break  # User said goodbye → exit the loop

        logger.info("Ready for next command.\n")


def manual_command_loop(listener: Listener, store: MemoryStore,
                         chat: Chat) -> None:
    """
    Reliable manual mode — press Enter, then speak your command.

    This is the recommended way to use RIZYEE. It does NOT need a wake
    word, so it works 100% of the time regardless of how Vosk mishears
    the made-up name "rizyee". You press Enter when you're ready to
    talk, say your command, and RIZYEE responds by voice and text.

    Why this exists: offline speech recognition (Vosk) only knows real
    dictionary words, so it can't reliably transcribe a made-up wake
    word. Manual mode skips that problem entirely — you decide when to
    speak by pressing Enter, and recognition only needs to handle real
    command words like "open youtube", which it does well.

    Args:
        listener: The Listener object that handles the microphone.
        store:    The MemoryStore for facts and reminders.
        chat:     The Chat client for AI answers.
    """
    print("=" * 55)
    print("RIZYEE MANUAL MODE")
    print("Press Enter to speak, then say your command.")
    print("Type 'quit' and press Enter to exit.")
    print("=" * 55)
    print()

    YES_WORDS = {"yes", "yeah", "yep", "sure", "okay", "ok", "go ahead",
                 "do it", "please", "confirm", "affirmative"}
    NO_WORDS = {"no", "nope", "stop", "cancel", "don't", "dont", "wait"}

    def ask_permission(question: str) -> bool:
        """Speak a yes/no question and listen for the answer."""
        speak(question)
        answer = listener.listen(timeout=6.0)
        if not answer:
            speak("I didn't hear an answer, so I'll leave it.")
            return False
        words = set(answer.lower().split())
        if words & NO_WORDS:
            return False
        if words & YES_WORDS:
            return True
        speak(f"I heard {answer}, so I'll leave it for now.")
        return False

    def handle_command(command: str) -> bool:
        """Parse and execute one command. Returns False to shut down."""
        if not command:
            speak("I didn't catch that. Please try again.")
            return True
        logger.info(f'Command received: "{command}"')
        print(f"You said: {command}")
        action, target = parse_command(command)
        return execute(
            action, target, speak,
            store=store, chat=chat, ask_permission=ask_permission,
        )

    while True:
        try:
            # Wait for user input or press Enter to speak.
            prompt = input("Type command or press Enter to speak (or 'quit') > ")
        except EOFError:
            break

        cleaned_prompt = prompt.strip()
        print(f"DEBUG: cleaned_prompt = '{cleaned_prompt}'")
        if cleaned_prompt.lower() in ("quit", "exit", "stop", "q"):
            speak("Goodbye, Shiva.")
            break

        if cleaned_prompt:
            # User typed a text command directly!
            command = cleaned_prompt
            print(f"[Typed Command: '{command}']")
        else:
            # User pressed Enter without typing -> listen on microphone.
            print("Listening... speak now.")
            command = listener.listen(timeout=10.0)

        # ── Parse and execute ──
        should_keep_running = handle_command(command)
        if not should_keep_running:
            break
        print()


def main() -> None:
    """
    Start RIZYEE.

    Steps:
        1. Show the welcome banner
        2. Initialize the speech listener (microphone + Vosk)
        3. Open the memory store (SQLite facts + reminders)
        4. Start the reminder checker (background thread)
        5. Set up the AI chat client (Ollama, optional)
        6. Speak the greeting
        7. Enter the command loop
        8. On exit, stop the checker and close the store
    """
    print_banner()

    logger.info("Starting RIZYEE...")

    # ── Initialize the listener (microphone + Vosk) ──
    try:
        listener = Listener()
    except FileNotFoundError:
        logger.error("")
        logger.error("═══ MISSING SPEECH MODEL ═══")
        logger.error("Run this command first:")
        logger.error("  python -m rizyee.utils.download_model")
        logger.error("════════════════════════════")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to start listener: {e}")
        logger.error("Make sure your microphone is connected!")
        sys.exit(1)

    # ── Initialize memory (SQLite facts + reminders) ──
    # Milestone 4. Memory is optional: if the database can't open,
    # RIZYEE keeps running without remember/recall/remind support.
    store = None
    checker = None
    try:
        store = MemoryStore()
        checker = ReminderChecker(store, speak)
        checker.start()
    except Exception as e:
        logger.warning(f"Memory unavailable (continuing without it): {e}")
        store = None
        checker = None

    # ── Initialize AI chat (Ollama) ──
    # Milestone 5. The Chat client always constructs fine — it only
    # contacts Ollama when ask() is called. If Ollama isn't installed,
    # ask() returns None and RIZYEE falls back to a canned message.
    # So this never blocks startup.
    chat = None
    try:
        chat = Chat()
    except Exception as e:
        logger.warning(f"Chat unavailable (continuing without AI): {e}")
        chat = None

    # ── Greet the user ──
    speak("RIZYEE is online.")
    speak("Yes Shiva, I'm ready.")

    # ── Pick the command loop ──
    # Hands-free wake mode is now the default. You can pass --manual
    # if you ever want to use the press-Enter manual mode.
    manual_mode = "--manual" in sys.argv

    # ── Start listening ──
    try:
        if manual_mode:
            manual_command_loop(listener, store, chat)
        else:
            command_loop(listener, store, chat)
    finally:
        # ── Clean shutdown: stop the checker and close the DB ──
        # finally: runs even if the loop raised an exception, so we
        # never leave the background thread or the DB file open.
        if checker is not None:
            checker.stop()
        if store is not None:
            store.close()


# This block runs when you execute: python -m rizyee.main
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # User pressed Ctrl+C → exit cleanly
        print("\n")
        logger.info("RIZYEE shutting down. Goodbye, Shiva!")
        speak("Goodbye, Shiva.")
        sys.exit(0)
    except Exception as e:
        # Something went wrong → show the error
        logger.error(f"RIZYEE crashed: {e}")
        logger.error("Please share this error so we can fix it!")
        sys.exit(1)
