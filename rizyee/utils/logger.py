"""
RIZYEE Logger
=============
Creates a logger that prints colored messages to the terminal.
Each module gets its own named logger so you can tell
which part of RIZYEE is talking.

Usage:
    from rizyee.utils.logger import get_logger
    logger = get_logger("speech")
    logger.info("Listening...")
    logger.error("Microphone not found!")
"""

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """
    Create and return a logger for a RIZYEE module.

    Args:
        name: The module name (e.g., "speech", "brain", "actions").

    Returns:
        A configured Logger object.

    How it works:
        1. Creates a logger with the name "rizyee.<name>"
        2. Sets it to show all messages (DEBUG level and above)
        3. Formats messages like: [RIZYEE.speech] INFO: Listening...
        4. Sends output to the terminal (stdout)
    """
    # Create the logger with a name like "rizyee.speech"
    logger = logging.getLogger(f"rizyee.{name}")

    # Only add a handler if this logger doesn't have one yet.
    # Without this check, calling get_logger("speech") twice
    # would print each message twice!
    if not logger.handlers:
        # Set the minimum level — DEBUG means "show everything"
        logger.setLevel(logging.DEBUG)

        # Create a handler that prints to the terminal.
        # By default we only show WARNINGs and errors on screen so the
        # terminal stays clean — just RIZYEE's spoken replies (printed
        # by the speaker) and what you said. Set RIZYEE_DEBUG=1 to see
        # the full INFO/DEBUG logs again for troubleshooting.
        import os as _os
        _console_level = (
            logging.DEBUG if _os.environ.get("RIZYEE_DEBUG") else logging.WARNING
        )
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(_console_level)

        # Define the message format:
        #   [RIZYEE.SPEECH] INFO: Listening...
        #   ──────────────  ────  ───────────
        #   module name     level your message
        formatter = logging.Formatter(
            fmt="[RIZYEE.%(name)s] %(levelname)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)

        # Attach the handler to the logger
        logger.addHandler(handler)

    return logger
