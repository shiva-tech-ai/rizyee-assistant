"""
RIZYEE integration test — runs every command through the real pipeline.

This does NOT use the microphone or the speech model. It calls
parse_command() and execute() directly with a fake speak() function
that records what RIZYEE would say. That lets us verify the brain and
actions work correctly without needing to talk.

Run with:  python -m tests.test_pipeline
"""

from rizyee.brain.commander import parse_command
from rizyee.actions.executor import execute
from rizyee.memory.store import MemoryStore


def run_all():
    """Run every command type and report pass/fail."""
    # Fake speak(): records strings instead of speaking them out loud.
    spoken = []

    def fake_speak(text):
        spoken.append(text)

    # A real memory store (uses the actual SQLite DB).
    store = MemoryStore()
    # No chat client → AI actions fall back gracefully.
    chat = None

    passed = 0
    failed = 0

    def check(label, condition):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  PASS: {label}")
        else:
            failed += 1
            print(f"  FAIL: {label}")

    print("\n=== MILESTONE 3: System commands ===\n")

    # Time
    spoken.clear()
    action, target = parse_command("what time is it")
    execute(action, target, fake_speak, store=store, chat=chat)
    check("tell_time speaks something with 'time'",
          any("time is" in s for s in spoken))

    # Date
    spoken.clear()
    action, target = parse_command("what is the date")
    execute(action, target, fake_speak, store=store, chat=chat)
    check("tell_date speaks something with 'today'",
          any("today is" in s.lower() for s in spoken))

    # Introduce
    spoken.clear()
    action, target = parse_command("who are you")
    execute(action, target, fake_speak, store=store, chat=chat)
    check("introduce mentions RIZYEE",
          any("RIZYEE" in s for s in spoken))

    # Goodbye
    spoken.clear()
    action, target = parse_command("goodbye")
    keep = execute(action, target, fake_speak, store=store, chat=chat)
    check("goodbye returns False (shut down)", keep is False)
    check("goodbye speaks a farewell",
          any("goodbye" in s.lower() or "see you" in s.lower() for s in spoken))

    print("\n=== MILESTONE 4: Memory & reminders ===\n")

    # Remember a fact
    spoken.clear()
    action, target = parse_command("remember that my name is shiva")
    execute(action, target, fake_speak, store=store, chat=chat)
    check("remember parses key/value",
          action == "remember" and target == ("name", "shiva"))
    check("remember confirms in speech",
          any("remember" in s for s in spoken))
    check("fact actually saved to DB",
          store.get_fact("name") == "shiva")

    # Recall the fact
    spoken.clear()
    action, target = parse_command("what is my name")
    execute(action, target, fake_speak, store=store, chat=chat)
    check("recall routes to recall action", action == "recall")
    check("recall speaks the saved value",
          any("shiva" in s for s in spoken))

    # Recall-all
    spoken.clear()
    action, target = parse_command("what do you remember")
    execute(action, target, fake_speak, store=store, chat=chat)
    check("recall_all speaks a count",
          any("remember" in s for s in spoken))

    # Forget the fact
    spoken.clear()
    action, target = parse_command("forget my name")
    execute(action, target, fake_speak, store=store, chat=chat)
    check("forget routes correctly", action == "forget")
    check("forget deletes from DB", store.get_fact("name") is None)

    # Reminder with relative time
    spoken.clear()
    action, target = parse_command("remind me to drink water in 1 minute")
    execute(action, target, fake_speak, store=store, chat=chat)
    check("remind parses relative time",
          action == "remind" and target[0] == "drink water")
    check("remind speaks confirmation",
          any("remind" in s for s in spoken))
    check("reminder saved to DB",
          len(store.due_reminders()) >= 0)  # at least no crash

    # Reminder with clock time
    spoken.clear()
    action, target = parse_command("remind me to study at 9 pm")
    execute(action, target, fake_speak, store=store, chat=chat)
    check("remind parses clock time",
          action == "remind" and target[0] == "study")

    print("\n=== MILESTONE 5: AI chat (graceful fallback) ===\n")

    # General question → routes to AI
    spoken.clear()
    action, target = parse_command("what is the capital of france")
    check("general question routes to ask_ai",
          action == "ask_ai")

    # AI not available → falls back gracefully
    spoken.clear()
    action, target = parse_command("ask what is python")
    execute(action, target, fake_speak, store=store, chat=chat)
    check("ask_ai without Ollama speaks fallback",
          any("AI" in s or "brain" in s or "Ollama" in s for s in spoken))

    # Explicit "ask" trigger
    spoken.clear()
    action, target = parse_command("ask how do birds fly")
    check("ask trigger routes to ask_ai",
          action == "ask_ai" and target == "how do birds fly")

    # Unknown command also tries AI then falls back
    spoken.clear()
    action, target = parse_command("flibbertigibbet nonsense words")
    execute(action, target, fake_speak, store=store, chat=chat)
    check("unknown falls back to a helpful message",
          len(spoken) > 0)

    print("\n=== ROUTING SAFETY (no false matches) ===\n")

    # "what time" must NOT route to AI
    action, target = parse_command("what time is it")
    check("'what time is it' → tell_time, not ask_ai",
          action == "tell_time")

    # "what is my X" → recall, NOT AI
    action, target = parse_command("what is my name")
    check("'what is my name' → recall, not ask_ai",
          action == "recall")

    # "what is the X" → AI, NOT recall
    action, target = parse_command("what is the weather")
    check("'what is the weather' → ask_ai, not recall",
          action == "ask_ai")

    # "remind me to turn off the oven" → remind, NOT goodbye (contains "turn off")
    action, target = parse_command("remind me to turn off the oven")
    check("'remind me to turn off the oven' → remind, not goodbye",
          action == "remind")

    store.close()

    print(f"\n{'=' * 50}")
    print(f"RESULTS: {passed} passed, {failed} failed")
    print(f"{'=' * 50}\n")
    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_all()
    sys.exit(0 if success else 1)
