"""
RIZYEE Commander (Command Parser)
===================================
Takes what you said (text) and figures out what action to perform.

Example:
    "open chrome"      → action: OPEN_APP,    target: "chrome"
    "what time is it"  → action: TELL_TIME,   target: None
    "search youtube python tutorial" → action: YOUTUBE, target: "python tutorial"

How it works:
    We use simple keyword matching — no AI needed for basic commands.
    Each command has trigger words. If your sentence contains
    those words, RIZYEE knows what to do.

Usage:
    from rizyee.brain.commander import parse_command
    action, target = parse_command("open notepad")
    # action = "open_app", target = "notepad"
"""

from rizyee.utils.logger import get_logger

logger = get_logger("brain.commander")


def parse_command(text: str) -> tuple:
    """
    Parse a voice command and return (action, target).

    Args:
        text: What the user said (lowercase string from Vosk).

    Returns:
        A tuple of (action_name, target_or_None).
        action_name is a string like "open_app", "tell_time", etc.
        target is extra info (like the app name or search query).

    How it works:
        Goes through commands in priority order.
        First match wins — so "open youtube" triggers OPEN_APP,
        not YOUTUBE_SEARCH.
    """
    text = text.lower().strip()
    logger.info(f'Parsing command: "{text}"')

    # ── CHATGPT PPT / PROMPT (Highest Priority) ──
    if "chatgpt" in text or "openai" in text:
        prompt = text
        # If user wants a PPT/presentation via ChatGPT, craft the ultimate VBA prompt
        if any(w in text for w in ["ppt", "presentation", "slides"]):
            topic = text
            for kw in ["open chatgpt and make a ppt on", "chatgpt build a ppt on", "ask chatgpt to create a ppt about", "chatgpt", "openai"]:
                if kw in topic:
                    topic = topic.split(kw, 1)[1]
            for stop_word in ["with", "and", "download", "using"]:
                if stop_word in topic:
                    topic = topic.split(stop_word, 1)[0]
            topic = topic.strip() or "Computer Networks"
            prompt = f"Create a 12-slide PowerPoint presentation on {topic}. Write the complete Microsoft PowerPoint VBA macro code to generate these slides automatically when run in PowerPoint (Alt + F11 -> Insert Module -> Paste -> F5). Include titles, bullet points, and clean formatting."
        else:
            for kw in ["open chatgpt and", "ask chatgpt to", "chatgpt", "openai", "ask chatgpt"]:
                if kw in prompt:
                    prompt = prompt.split(kw, 1)[1]
            prompt = prompt.strip() or "Create a professional presentation outline"

        logger.info(f"Action: CHATGPT_SEARCH, prompt: {prompt}")
        return ("chatgpt_search", prompt)

    # ── CREATE PRESENTATION / PPT ──
    # "open chatgpt and make a ppt on computer networks with 12 slides", "make a presentation on python"
    if any(phrase in text for phrase in ["presentation", "ppt", "slides"]):
        if any(w in text for w in ["create", "make", "generate", "new", "on", "topic", "about"]):
            topic = text
            for kw in ["open chatgpt and make a ppt", "create presentation", "make presentation", "generate presentation", "create a ppt", "make a ppt", "create ppt", "make ppt", "generate ppt", "create slides", "make slides"]:
                if kw in topic:
                    topic = topic.split(kw, 1)[1]

            # Cut off extra phrases like "with 12 slides", "and download it", etc.
            for stop_word in ["with", "and", "download", "in gamma", "using"]:
                if stop_word in topic:
                    topic = topic.split(stop_word, 1)[0]

            for filler in ["on topic of", "topic of", "about", "on", "for", "named", "called", "a", "the"]:
                if topic.startswith(filler + " "):
                    topic = topic[len(filler):].strip()

            topic = topic.strip() or "Computer Networks"
            logger.info(f"Action: CREATE_PRESENTATION, topic: {topic}")
            return ("create_presentation", topic)

    # ── MEMORY: REMEMBER A FACT ──
    # "remember that my wifi password is mango123"
    # "remember my name is shiva"
    # NOTE: this must run BEFORE the goodbye check, because phrases
    # like "remember to turn off the oven" contain "turn off".
    if text.startswith("remember"):
        # Two patterns:
        #   "remember that X is Y"  → key=X, value=Y
        #   "remember X is Y"       → key=X, value=Y
        #   "remember my X is Y"    → key=X, value=Y
        rest = text[len("remember"):].strip()
        # Strip leading filler words.
        for filler in ("that", "my", "the", "to", "i", "the"):
            if rest.startswith(filler + " "):
                rest = rest[len(filler):].strip()
        if " is " in rest:
            key, value = rest.split(" is ", 1)
            key = key.strip()
            value = value.strip()
            if key and value:
                logger.info(f"Action: REMEMBER, key: {key}, value: {value}")
                return ("remember", (key, value))
        # "remember to ..." → treat as a reminder instead of a fact.
        # "remember to drink water" → reminder "drink water" soon.
        if text.startswith("remember to") or text.startswith("remember to"):
            what = text.replace("remember", "", 1).strip()
            what = what[len("to"):].strip() if what.startswith("to") else what
            logger.info(f"Action: REMEMBER_TO, what: {what}")
            return ("remember_to", what)
        # Couldn't parse it — fall through to unknown.
        logger.info(f"Action: REMEMBER (unparseable): '{text}'")

    # ── MEMORY: RECALL A FACT ──
    # "what is my wifi password", "whats my name", "do you know my name"
    # NOTE: only "my" phrases recall a personal fact. "what is the X"
    # is a general-knowledge question → that goes to the AI later, not
    # here. Otherwise "what is the capital of france" would wrongly
    # look up a stored fact instead of answering from the AI.
    # NOTE: Vosk outputs no apostrophes ("whats", not "what's"), so we
    # match the apostrophe-less "whats my" form too.
    recall_phrases = ("what is my ", "whats my ", "what s my ",
                      "do you know my ")
    if any(phrase in text for phrase in recall_phrases):
        for phrase in recall_phrases:
            if phrase in text:
                key = text.split(phrase, 1)[1].strip()
                # Strip trailing question mark / filler.
                key = key.rstrip("?").strip()
                for filler in ("please",):
                    if key.endswith(filler):
                        key = key[: -len(filler)].strip()
                if key:
                    logger.info(f"Action: RECALL, key: {key}")
                    return ("recall", key)
    # "what do you remember" / "what do you know" → list everything
    if "what do you remember" in text or "what do you know" in text:
        logger.info("Action: RECALL_ALL")
        return ("recall_all", None)

    # ── MEMORY: FORGET A FACT ──
    # "forget my wifi password", "forget that"
    if text.startswith("forget"):
        rest = text[len("forget"):].strip()
        for filler in ("that", "my", "the"):
            if rest.startswith(filler + " "):
                rest = rest[len(filler):].strip()
        if rest:
            logger.info(f"Action: FORGET, key: {rest}")
            return ("forget", rest)

    # ── REMINDER: SET A REMINDER ──
    # "remind me to drink water at 4 pm"
    # "remind me to call mom in 30 minutes"
    # "set a reminder to submit homework at 5 30"
    if "remind" in text or ("reminder" in text and "set" in text):
        # Extract the action (what) and the time phrase (when).
        what, when = _parse_reminder(text)
        if what:
            logger.info(f"Action: REMIND, what: {what}, when: {when}")
            return ("remind", (what, when))

    # ── GOODBYE / EXIT ──
    # "stop", "exit", "quit", "goodbye", "bye", "shut down"
    goodbye_words = ["stop", "exit", "quit", "goodbye", "bye bye",
                     "shut down", "shutdown", "turn off"]
    for word in goodbye_words:
        if word in text:
            logger.info("Action: GOODBYE")
            return ("goodbye", None)

    # ── TELL TIME ──
    # "what time", "tell me the time", "current time", "time please"
    if "time" in text and any(w in text for w in ["what", "tell", "current"]):
        logger.info("Action: TELL_TIME")
        return ("tell_time", None)

    # ── TELL DATE ──
    # "what date", "today's date", "what day"
    if any(w in text for w in ["date", "day", "today"]):
        logger.info("Action: TELL_DATE")
        return ("tell_date", None)

    # ── CREATE PROJECTS / FILES ──
    # "create project calculator", "make a project named website", "create file notes.txt"
    create_words = ["create project", "make project", "create a project", "make a project", "new project"]
    for cw in create_words:
        if text.startswith(cw) or cw in text:
            # Extract project name after the keyword
            parts = text.split(cw, 1)
            proj_name = parts[1].strip() if len(parts) > 1 else ""
            for filler in ["named", "called", "for", "a", "the"]:
                if proj_name.startswith(filler + " "):
                    proj_name = proj_name[len(filler):].strip()
            logger.info(f"Action: CREATE_PROJECT, target: {proj_name}")
            return ("create_project", proj_name)

    file_words = ["create file", "make file", "new file", "create a file"]
    for fw in file_words:
        if text.startswith(fw) or fw in text:
            parts = text.split(fw, 1)
            file_name = parts[1].strip() if len(parts) > 1 else "document.txt"
            for filler in ["named", "called", "for", "a", "the"]:
                if file_name.startswith(filler + " "):
                    file_name = file_name[len(filler):].strip()
            logger.info(f"Action: CREATE_FILE, target: {file_name}")
            return ("create_file", file_name)

    # ── OPEN A WEBSITE (Milestone 6) ──
    # "open youtube" / "open google" / "open gmail" → open the homepage.
    # This MUST run before the YouTube-search and Google-search blocks,
    # otherwise "open google" gets swallowed as a web search.
    # We match only known site names; everything else falls through to
    # OPEN_APP below (so "open notepad" still launches the app).
    # ── CHATGPT PROMPT / SEARCH ──
    # "ask chatgpt to create a ppt about llms", "chatgpt build a presentation on python"
    if "chatgpt" in text or "openai" in text:
        prompt = text
        for kw in ["ask chatgpt to", "chatgpt", "openai", "ask chatgpt"]:
            if kw in prompt:
                prompt = prompt.split(kw, 1)[1]
        prompt = prompt.strip() or "Create a professional presentation outline"
        logger.info(f"Action: CHATGPT_SEARCH, prompt: {prompt}")
        return ("chatgpt_search", prompt)

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
        "whatsapp": "https://web.whatsapp.com",
        "whatsapp web": "https://web.whatsapp.com",
        "slides": "https://slides.google.com",
        "google slides": "https://slides.google.com",
        "canva": "https://www.canva.com",
        "gamma": "https://gamma.app",
        "powerpoint": "https://www.office.com/launch/powerpoint",
    }
    # ── OPEN APPLICATION OR SITE ──
    # "open chrome", "launch notepad", "open instagram", "start calculator"
    open_words = ["open", "launch", "start", "run", "go to", "visit"]
    KNOWN_APPS = {"notepad", "calculator", "calc", "paint", "mspaint", "chrome", "google chrome", "edge", "msedge", "explorer", "file explorer", "cmd", "command prompt", "terminal", "wt", "vs code", "visual studio code", "code", "spotify", "word", "excel", "powerpoint", "settings", "task manager"}

    for word in open_words:
        if text.startswith(word):
            target_name = text[len(word):].strip()
            for filler in ["my", "the", "a"]:
                if target_name.startswith(filler + " "):
                    target_name = target_name[len(filler):].strip()

            if target_name:
                # If it's in known sites or looks like a website domain (or not a known app), open as site
                if target_name in SITES or target_name not in KNOWN_APPS:
                    # If it's a known site or any random word like instagram/facebook, open site
                    if target_name in SITES or " " not in target_name:
                        logger.info(f"Action: OPEN_SITE, target: {target_name}")
                        return ("open_site", target_name)

                logger.info(f"Action: OPEN_APP, app: {target_name}")
                return ("open_app", target_name)

    # ── CLOSE APPLICATION ──
    # "close chrome", "kill notepad", "exit calculator"
    close_words = ["close", "kill", "end"]
    for word in close_words:
        if text.startswith(word):
            app_name = text.replace(word, "").strip()
            if app_name:
                logger.info(f"Action: CLOSE_APP, app: {app_name}")
                return ("close_app", app_name)

    # ── VOLUME CONTROL ──
    if "volume up" in text or "louder" in text:
        logger.info("Action: VOLUME_UP")
        return ("volume_up", None)

    if "volume down" in text or "quieter" in text or "softer" in text:
        logger.info("Action: VOLUME_DOWN")
        return ("volume_down", None)

    if "mute" in text:
        logger.info("Action: MUTE")
        return ("mute", None)

    # ── WHO ARE YOU ──
    if any(w in text for w in ["who are you", "your name", "introduce"]):
        logger.info("Action: INTRODUCE")
        return ("introduce", None)

    # ── ASK THE AI (Milestone 5) ──
    # "ask what is python" / "tell me about python" / "what is the capital
    # of france" → route to the local Ollama model for a real answer.
    # "ask ..." explicitly sends the rest to the AI. Questions starting
    # with "what is/are", "why", "how", "who", "when", "where", "explain",
    # "tell me about", "define" also go to the AI, since they're not
    # system commands. These are checked AFTER all real commands above,
    # so "what time is it" still hits TELL_TIME, not the AI.
    if text.startswith("ask "):
        question = text[len("ask "):].strip()
        if question:
            logger.info(f"Action: ASK_AI (ask), question: {question}")
            return ("ask_ai", question)
    if any(text.startswith(p) for p in (
        "what is ", "what's ", "what are ", "what can ", "what do ",
        "why ", "how ", "who ", "when ", "where ", "explain ", "define ",
        "tell me about ", "tell me ",
    )):
        logger.info(f"Action: ASK_AI (question), text: {text}")
        return ("ask_ai", text)

    # ── UNKNOWN COMMAND ──
    # If nothing matched, we don't know what to do
    logger.info(f"Action: UNKNOWN — could not parse: '{text}'")
    return ("unknown", text)


# ── Reminder text parsing ──────────────────────────────────────
# Voice input is messy. "remind me to drink water at 4 pm" could come
# back from Vosk as "remind me to drink water at 4 p m" or "...for pm".
# These helpers turn that messy text into a clean (what, when_iso) pair.
# when_iso is an ISO-format string the store can compare, or "" if no
# time was understood (in which case main.py will ask the user again).

import re
from datetime import datetime, timedelta


def _parse_reminder(text: str):
    """
    Pull the action and the time out of a reminder phrase.

    Args:
        text: The full spoken command, lowercased, e.g.
              "remind me to drink water at 4 pm"

    Returns:
        (what, when_iso) where:
            what     = the thing to be reminded of ("drink water")
            when_iso = ISO time string ("2026-11-04T16:00:00") or ""
                       if no time was understood.
    """
    # Strip the leading "remind me to " / "remind me " / "set a reminder to ".
    what = text
    for prefix in ("remind me to ", "remind me ", "set a reminder to ",
                   "set reminder to ", "remind to "):
        if what.startswith(prefix):
            what = what[len(prefix):]
            break

    # ── Try "in X minutes/hours" ──
    # "remind me to drink water in 30 minutes"
    m = re.search(r"in (\d+)\s*(minute|minutes|hour|hours|hr|hrs|min)\b", what)
    if m:
        amount = int(m.group(1))
        unit = m.group(2)
        # Remove the time phrase from the action text.
        what = (what[:m.start()] + what[m.end():]).strip()
        if unit.startswith("hour") or unit in ("hr", "hrs"):
            delta = timedelta(hours=amount)
        else:
            delta = timedelta(minutes=amount)
        when = datetime.now() + delta
        return what, when.isoformat(timespec="minutes")

    # ── Try "at <time>" ──
    # "remind me to call mom at 4 pm" / "at 4 30 pm" / "at 16:00"
    # The minutes group must consume its own separator (a colon or space)
    # so that "at 5 30 pm" reads hour=5 minute=30, not hour=5 with "30 pm"
    # left dangling in the action text.
    m = re.search(
        r"at\s+(\d{1,2})(?:(?:[:\s]+)(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)?\b",
        what,
    )
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2)) if m.group(2) else 0
        ampm = (m.group(3) or "").replace(".", "")

        # Handle 12-hour clock with am/pm.
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0  # 12 am = midnight = 0

        # Remove the time phrase from the action text.
        what = (what[:m.start()] + what[m.end():]).strip()

        # Build today's datetime at the given hour. If that time has
        # already passed today, schedule it for tomorrow.
        now = datetime.now()
        when = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if when <= now:
            when += timedelta(days=1)
        return what, when.isoformat(timespec="minutes")

    # No time understood. Return the action with an empty time so the
    # executor can ask the user when they mean.
    return what.strip(), ""

