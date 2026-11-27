"""
RIZYEE Action Executor
======================
Takes a parsed command (action + target) and actually does it.

This is Milestone 3 — RIZYEE can now ACT, not just listen and repeat.
Before this, RIZYEE only echoed back what you said. Now it can:

    "what time is it"        → speaks the current time
    "what's the date"        → speaks today's date
    "open notepad"           → launches Notepad
    "close chrome"          → shuts Chrome down
    "search youtube cats"   → opens YouTube in your browser
    "search for python tips" → opens Google in your browser
    "volume up / down"      → changes the system volume
    "mute"                  → mutes the speakers
    "who are you"           → introduces itself
    "goodbye"               → shuts RIZYEE down

Usage:
    from rizyee.actions.executor import execute
    should_keep_running = execute("open_app", "notepad", speak)
    # Returns True if RIZYEE should stay on, False to shut down.

Design choice — why no new pip packages:
    Everything here uses modules built into Python (datetime, webbrowser,
    subprocess, ctypes). RIZYEE is a zero-budget project, so we avoid
    adding dependencies when Windows already gives us what we need.
"""

import os
import webbrowser
import subprocess
from datetime import datetime, timedelta
from urllib.parse import quote  # turns spaces into %20 for URLs

from rizyee.utils.logger import get_logger
from rizyee.actions.creator import create_project, create_document, create_presentation

logger = get_logger("actions.executor")


# ── App name → launch command ──
# Windows "start" can open apps that are on PATH, registered as
# UWP apps, or known by the Start menu. We keep a small mapping for
# common apps so vague names like "calculator" still work, then fall
# back to passing the name straight to "start".
APP_COMMANDS = {
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "paint": "mspaint",
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "browser": "msedge",
    "explorer": "explorer",
    "file explorer": "explorer",
    "command prompt": "cmd",
    "cmd": "cmd",
    "terminal": "wt",
    "vs code": "code",
    "visual studio code": "code",
    "code": "code",
    "spotify": "spotify",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "settings": "start ms-settings:",
    "task manager": "taskmgr",
}

# ── App name → process name (for closing) ──
# "taskkill /im" needs the .exe name. We map friendly names to the
# real process name so "close chrome" kills chrome.exe.
APP_PROCESSES = {
    "notepad": "notepad.exe",
    "calculator": "ApplicationFrameHost.exe",  # Calculator is a UWP app
    "calc": "ApplicationFrameHost.exe",
    "paint": "mspaint.exe",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "vs code": "Code.exe",
    "visual studio code": "Code.exe",
    "code": "Code.exe",
    "spotify": "Spotify.exe",
    "word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
    "powerpoint": "POWERPNT.EXE",
    "task manager": "Taskmgr.exe",
}


def execute(action: str, target, speak, store=None, chat=None,
            ask_permission=None) -> bool:
    """
    Run a parsed command.

    Args:
        action: The action name from parse_command (e.g. "open_app").
        target: Extra info (app name, search query) or None.
        speak:  The speak() function from rizyee.speech.speaker.
                We pass it in instead of importing it directly so the
                executor stays easy to test without the TTS engine.
        store:  Optional MemoryStore instance. Needed for the memory
                and reminder actions (Milestone 4). Older actions
                ignore it, so the default None keeps them working.
        chat:   Optional Chat instance (Ollama). Needed for AI answers
                (Milestone 5). If None or Ollama isn't running, AI
                questions fall back to a friendly canned message.
        ask_permission: Optional callback for risky actions. When given
                (by main.py, which has the mic), the close-app handler
                speaks "Should I close chrome?" and listens for your
                yes/no before actually closing anything. If None
                (e.g. in tests), risky actions are skipped for safety.

    Returns:
        True  → RIZYEE should keep running (go back to waiting).
        False → RIZYEE should shut down (only for the "goodbye" action).
    """
    logger.info(f"Executing: action={action}, target={target!r}")

    # ── MEMORY: REMEMBER A FACT ──
    # target is a (key, value) tuple from the parser.
    if action == "remember":
        if store is None:
            speak("I can't remember things right now — memory is off.")
            return True
        key, value = target
        store.save_fact(key, value)
        speak(f"Okay, I'll remember that your {key} is {value}.")
        return True

    # ── MEMORY: RECALL A FACT ──
    # target is the key to look up.
    if action == "recall":
        if store is None:
            speak("I can't recall things right now — memory is off.")
            return True
        value = store.get_fact(target)
        if value is not None:
            speak(f"Your {target} is {value}.")
        else:
            speak(f"I don't know your {target}. You can tell me by saying "
                  f"remember that my {target} is something.")
        return True

    # ── MEMORY: RECALL EVERYTHING ──
    if action == "recall_all":
        if store is None:
            speak("Memory is off right now.")
            return True
        facts = store.list_facts()
        if not facts:
            speak("I don't have anything remembered yet.")
        else:
            speak(f"I remember {len(facts)} things.")
            for key, value in facts:
                speak(f"Your {key} is {value}.")
        return True

    # ── MEMORY: FORGET A FACT ──
    if action == "forget":
        if store is None:
            speak("Memory is off right now.")
            return True
        if store.forget_fact(target):
            speak(f"I've forgotten your {target}.")
        else:
            speak(f"I didn't have anything saved for {target}.")
        return True

    # ── REMEMBER TO (no time = ask) ──
    # "remember to drink water" with no time → treat as a near-term
    # nudge. We schedule it for 1 minute from now so RIZYEE confirms
    # the reminder loop works even without a clear time.
    if action == "remember_to":
        if store is None:
            speak("I can't set reminders right now — memory is off.")
            return True
        when = (datetime.now() + timedelta(minutes=1)).isoformat(timespec="minutes")
        store.add_reminder(target, when)
        speak(f"Okay, I'll remind you to {target} shortly.")
        return True

    # ── REMINDER: SET A REMINDER ──
    # target is a (what, when_iso) tuple from the parser.
    if action == "remind":
        if store is None:
            speak("I can't set reminders right now — memory is off.")
            return True
        what, when_iso = target
        if not when_iso:
            # No time understood — tell the user how to phrase it.
            speak(f"I want to remind you to {what}, but I didn't catch "
                  f"when. Try saying remind me to {what} at 4 pm, "
                  f"or in 30 minutes.")
            return True
        store.add_reminder(what, when_iso)
        # Say it back in a friendly way.
        try:
            t = datetime.fromisoformat(when_iso)
            friendly = t.strftime("%I:%M %p").lstrip("0")
            speak(f"Got it. I'll remind you to {what} at {friendly}.")
        except Exception:
            speak(f"Got it. I'll remind you to {what}.")
        return True

    # ── GOODBYE ──
    if action == "goodbye":
        speak("Goodbye, Shiva. See you soon.")
        return False  # tells main.py to stop the loop

    # ── TELL TIME ──
    if action == "tell_time":
        now = datetime.now()
        # %I = 12-hour clock, %M = minutes, %p = AM/PM
        time_str = now.strftime("%I:%M %p")
        # .lstrip("0") turns "09:05" into "9:05" — nicer to say
        time_str = time_str.lstrip("0")
        speak(f"The time is {time_str}.")
        return True

    # ── TELL DATE ──
    if action == "tell_date":
        now = datetime.now()
        # %A = full weekday, %B = full month name, %d = day, %Y = year
        date_str = now.strftime("%A, %B %d, %Y")
        speak(f"Today is {date_str}.")
        return True

    # ── CREATE PROJECT ──
    if action == "create_project":
        folder = create_project(target)
        speak(f"Created project {folder} with starter files.")
        return True

    # ── CREATE FILE ──
    if action == "create_file":
        filename = create_document(target)
        speak(f"Created file {filename}.")
        return True

    # ── CREATE PRESENTATION ──
    if action == "create_presentation":
        topic_name = create_presentation(target)
        speak(f"I have created and opened your presentation on {topic_name}.")
        return True

    # ── YOUTUBE SEARCH ──
    if action == "youtube_search":
        if not target:
            speak("What should I search for on YouTube?")
            return True
        url = f"https://www.youtube.com/results?search_query={quote(target)}"
        webbrowser.open(url)
        speak(f"Searching YouTube for {target}.")
        return True

    # ── WEB / GOOGLE SEARCH ──
    if action == "web_search":
        if not target:
            speak("What should I search for?")
            return True
        url = f"https://www.google.com/search?q={quote(target)}"
        webbrowser.open(url)
        speak(f"Searching Google for {target}.")
        return True

    # ── CHATGPT SEARCH / PROMPT ──
    if action == "chatgpt_search":
        if not target:
            webbrowser.open("https://chat.openai.com")
            speak("Opening ChatGPT.")
            return True
        url = f"https://chat.openai.com/?q={quote(target)}"
        webbrowser.open(url)
        speak(f"Opening ChatGPT with your prompt.")
        return True

    # ── OPEN A WEBSITE (Milestone 6) ──
    # "open youtube" / "open google" / "open gmail" / "open github"
    # → opens the site's homepage in your default browser.
    SITES = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "gmail": "https://mail.google.com",
        "github": "https://github.com",
        "reddit": "https://www.reddit.com",
        "wikipedia": "https://www.wikipedia.org",
        "amazon": "https://www.amazon.com",
        "netflix": "https://www.netflix.com",
        "spotify web": "https://open.spotify.com",
        "maps": "https://maps.google.com",
        "google maps": "https://maps.google.com",
        "weather": "https://weather.com",
        "chat gpt": "https://chat.openai.com",
        "whatsapp web": "https://web.whatsapp.com",
    }
    if action == "open_site":
        site_name = (target or "").strip()
        url = SITES.get(site_name)
        if not url:
            # Unknown site — build a best-guess URL from the name.
            url = f"https://www.{site_name.replace(' ', '')}.com"
        try:
            webbrowser.open(url)
            speak(f"Opening {site_name}.")
        except Exception as e:
            logger.error(f"Failed to open {site_name}: {e}")
            speak(f"I couldn't open {site_name}.")
        return True

    # ── OPEN APPLICATION ──
    if action == "open_app":
        if not target:
            speak("Which app should I open?")
            return True
        command = APP_COMMANDS.get(target, target)
        try:
            # "start" opens the app and lets RIZYEE keep running right
            # away — we don't wait for the app to close.
            # start "" → the empty title (needed if the path has spaces)
            subprocess.Popen(f'start "" {command}', shell=True)
            speak(f"Opening {target}.")
        except Exception as e:
            logger.error(f"Failed to open {target}: {e}")
            speak(f"I couldn't open {target}.")
        return True

    # ── CLOSE APPLICATION ──
    # Closing an app is a risky action (it can lose your unsaved work),
    # so RIZYEE asks for confirmation first. The ask_permission callback
    # (wired in main.py, which has the mic) speaks the question and
    # listens for your yes/no. Returns True only if you said yes.
    if action == "close_app":
        if not target:
            speak("Which app should I close?")
            return True
        # Ask before closing. If we can't ask (no mic in tests), skip
        # the close for safety rather than doing it blindly.
        if ask_permission is not None:
            confirmed = ask_permission(f"Should I close {target}?")
            if not confirmed:
                speak("Okay, I won't close it.")
                return True
        else:
            speak("I'd need you to confirm before I close an app.")
            return True
        process = APP_PROCESSES.get(target, f"{target}.exe")
        try:
            # /im = image name (the .exe), /f = force close
            result = subprocess.run(
                f"taskkill /im {process} /f",
                shell=True,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                speak(f"Closing {target}.")
            else:
                # taskkill prints why it failed (e.g. process not running)
                logger.warning(f"taskkill said: {result.stderr.strip()}")
                speak(f"{target} isn't running.")
        except Exception as e:
            logger.error(f"Failed to close {target}: {e}")
            speak(f"I couldn't close {target}.")
        return True

    # ── VOLUME CONTROL ──
    # We send the media/volume keys the same way your keyboard does.
    # This works on Windows without installing any extra package.
    if action in ("volume_up", "volume_down", "mute"):
        _press_volume_key(action)
        if action == "mute":
            speak("Muted.")
        elif action == "volume_up":
            speak("Volume up.")
        else:
            speak("Volume down.")
        return True

    # ── INTRODUCE ──
    if action == "introduce":
        speak(
            "I am RIZYEE, your personal voice assistant. "
            "I can open and close apps, search the web and YouTube, "
            "tell you the time and date, remember things, set reminders, "
            "and answer questions. "
            "Just say my name, then tell me what you need."
        )
        return True

    # ── ASK THE AI (Milestone 5) ──
    # Questions the parser routed here get a real answer from Ollama.
    # If Ollama isn't available, we fall back gracefully.
    if action == "ask_ai":
        answer = _ask_chat(chat, target, speak)
        if answer is None:
            speak(
                "I'd love to answer that, but my AI brain isn't running. "
                "Install Ollama and pull a model, then ask me again."
            )
        return True

    # ── UNKNOWN COMMAND ──
    # Nothing matched a known command. Before giving up, try the AI —
    # the user may have asked a question the parser didn't flag as one.
    # If the AI is unavailable, give a clear fallback that hints at what
    # works, so they're never left guessing whether RIZYEE heard them.
    if action == "unknown":
        # Try the AI as a last resort.
        answer = _ask_chat(chat, target, speak)
        if answer is not None:
            return True
        speak(
            "I heard you say something, but I'm not sure what to do. "
            "You can ask me to open an app, search YouTube, "
            "tell the time, set a reminder, or ask me a question."
        )
        return True

    # Should never reach here, but if a new action is added to the
    # parser before its handler exists, we fail safely.
    logger.warning(f"No handler for action: {action}")
    speak("I don't know how to do that yet.")
    return True


# ── Chat helper ──────────────────────────────────────────────
def _ask_chat(chat, question, speak):
    """
    Ask the AI a question and speak the answer.

    Returns the answer string if the AI responded, or None if it
    wasn't available (so the caller can fall back). Centralizing this
    keeps the ask_ai and unknown handlers consistent and avoids
    repeating the None-check + fallback logic in two places.
    """
    if chat is None or not question:
        return None
    try:
        answer = chat.ask(question)
    except Exception as e:
        logger.error(f"Chat raised: {e}")
        return None
    if answer:
        speak(answer)
    return answer


# ── Volume key helper ──
def _press_volume_key(action: str) -> None:
    """
    Send a volume media key using the Windows API.

    Why ctypes: Windows has built-in virtual key codes for volume
    (VK_VOLUME_UP, VK_VOLUME_DOWN, VK_VOLUME_MUTE). We trigger them
    with user32.keybd_event — the same call your keyboard driver uses.
    No pip package required.

    Args:
        action: One of "volume_up", "volume_down", "mute".
    """
    import ctypes

    # Virtual key codes (from the Windows API docs)
    VK_VOLUME_MUTE = 0xAD
    VK_VOLUME_UP = 0xAF
    VK_VOLUME_DOWN = 0xAE

    key_map = {
        "mute": VK_VOLUME_MUTE,
        "volume_up": VK_VOLUME_UP,
        "volume_down": VK_VOLUME_DOWN,
    }

    vk = key_map[action]
    # keybd_event is the old Windows API for simulating a key press.
    # 0 = key down, 2 (KEYEVENTF_KEYUP) = key up. We press and release.
    ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
    ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
