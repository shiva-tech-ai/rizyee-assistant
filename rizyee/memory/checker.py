"""
RIZYEE Reminder Checker
======================
Runs in a background thread and fires reminders when their time comes.

This is the second half of Milestone 4 (memory). The store saves
reminders; this module watches for ones that are due and speaks them.

Why a background thread:
    The main loop spends most of its time inside listener.listen(),
    which blocks for several seconds at a time. If we checked for due
    reminders only inside that loop, a reminder set for 4:00 pm might
    not fire until 4:05 because RIZYEE was busy listening. A separate
    thread polls every 20 seconds, so reminders fire within ~20s of
    their time — good enough for a personal assistant.

Design choice — how it talks:
    The checker doesn't import speak() directly. It takes a `speak`
    function in its constructor, the same way execute() does. This
    keeps it testable without the TTS engine and avoids import cycles
    (the speaker and the checker can both be imported independently).

Usage:
    from rizyee.memory.store import MemoryStore
    from rizyee.memory.checker import ReminderChecker

    store = MemoryStore()
    checker = ReminderChecker(store, speak)
    checker.start()        # begins polling in the background
    ...
    checker.stop()         # call this when RIZYEE shuts down
"""

import threading
from datetime import datetime

from rizyee.utils.logger import get_logger

logger = get_logger("memory.checker")

# How often (seconds) the background thread checks for due reminders.
# 20s is a good balance: reminders fire close to on time, and we're
# not hammering the database with queries.
POLL_INTERVAL = 20.0


class ReminderChecker:
    """
    Watches the memory store for due reminders and speaks them.

    Attributes:
        store:      The MemoryStore to read reminders from.
        speak:      The speak() function (passed in, not imported).
        _thread:    The background thread doing the polling.
        _stop:      A flag that tells the thread to exit.
    """

    def __init__(self, store, speak):
        """
        Set up the checker (but don't start it yet — call start()).

        Args:
            store: A MemoryStore instance.
            speak: The speak() function from rizyee.speech.speaker.
        """
        self.store = store
        self.speak = speak
        self._thread = None
        # threading.Event is a safe way to signal a thread to stop.
        # _stop.set() flips it to "on"; _stop.is_set() checks it.
        self._stop = threading.Event()

    def start(self) -> None:
        """Begin polling for due reminders in a background thread."""
        if self._thread is not None and self._thread.is_alive():
            return  # Already running — don't start a second one.

        # Clear the stop flag in case this checker was stopped and
        # is now being restarted.
        self._stop.clear()
        # daemon=True means the thread won't keep Python alive on its
        # own — when the main program exits, daemon threads are killed
        # automatically. That lets Ctrl+C exit RIZYEE cleanly.
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Reminder checker started (background thread).")

    def stop(self) -> None:
        """Tell the background thread to stop and wait for it to finish."""
        if self._thread is None:
            return
        self._stop.set()
        # Block for up to a few seconds so the thread can finish its
        # current poll. If it's stuck, we don't hang forever — it's a
        # daemon thread and will be killed at exit anyway.
        self._thread.join(timeout=5.0)
        logger.info("Reminder checker stopped.")

    def _run(self) -> None:
        """
        The background loop. Runs until stop() is called.

        We check for due reminders, fire any we find, then sleep for
        POLL_INTERVAL seconds. The sleep uses _stop.wait() instead of
        time.sleep() so that stop() wakes us up immediately instead
        of waiting for the full interval.
        """
        logger.info("Watching for due reminders...")
        while not self._stop.is_set():
            try:
                self._check_once()
            except Exception as e:
                # A background thread must never crash silently and die
                # without logging — if it did, reminders would silently
                # stop firing and you'd never know why. Log and continue.
                logger.error(f"Reminder check failed (will retry): {e}")

            # Wait POLL_INTERVAL seconds, but wake early if stop() is set.
            self._stop.wait(POLL_INTERVAL)

    def _check_once(self) -> None:
        """Check for due reminders and fire any that are ready."""
        due = self.store.due_reminders()
        for reminder in due:
            # Tell the user, then mark it done so it doesn't fire again.
            self.speak(f"Reminder: {reminder['what']}.")
            self.store.mark_reminder_done(reminder["id"])
            logger.info(
                f"Fired reminder #{reminder['id']}: '{reminder['what']}'"
            )
