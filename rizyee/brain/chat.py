"""
RIZYEE Chat (AI conversation via Ollama)
=====================================
Gives RIZYEE real conversational answers using a local AI model.

This is Milestone 5. Before this, if RIZYEE heard something it didn't
recognize as a command, it said "I don't know how to do that." Now it
passes the question to a local AI (Ollama) and speaks the answer back.

Why Ollama:
    It runs a language model entirely on your laptop — no internet, no
    API key, no monthly bill. That fits RIZYEE's ₹0 budget. You install
    it once (https://ollama.com), pull a small model like "llama3.2",
    and RIZYEE does the rest.

Why urllib (not the `ollama` pip package):
    Ollama exposes a simple local HTTP API at http://localhost:11434.
    We call it with Python's built-in urllib — no pip install needed, no
    extra dependency. Keeps the project lean.

Graceful fallback:
    If Ollama isn't installed or isn't running, chat() returns None.
    The executor then falls back to a canned "I don't know" message, so
    RIZYEE keeps working even before Ollama is set up. Nothing crashes.

Usage:
    from rizyee.brain.chat import Chat
    chat = Chat()
    answer = chat.ask("What is the capital of France?")
    if answer:
        speak(answer)
    else:
        speak("I can't answer that right now.")
"""

import json
import urllib.request
import urllib.error

from rizyee.utils.logger import get_logger

logger = get_logger("brain.chat")

# ── Ollama local API ──
# Default URL when you install Ollama. /api/chat is the conversational
# endpoint that keeps a message history per "session".
OLLAMA_URL = "http://localhost:11434/api/chat"

# ── The model to use ──
# "llama3.2" is small (~2 GB), runs on modest laptops, and answers well.
# You can change this to any model you've pulled (e.g. "phi3", "gemma2",
# "mistral"). Run `ollama list` in a terminal to see what you have.
DEFAULT_MODEL = "llama3.2"

# ── How long to wait for Ollama to answer ──
# A local model can take a few seconds to start answering, especially
# the first time (the model loads into memory). 30s is a safe ceiling.
TIMEOUT_SECONDS = 30


class Chat:
    """
    Talks to a local Ollama model and returns its answers as text.

    Why a class:
        We keep a running list of messages so the model remembers the
        conversation ("What else can it do?" makes sense after "Tell me
        about Python"). The class holds that history in self.messages.

    Attributes:
        model:    The Ollama model name to ask (e.g. "llama3.2").
        messages: The conversation history, sent with every request.
        enabled:  True if Ollama was reached at least once. If the first
                  call fails, we flip this to False and stop retrying so
                  we don't hang on every unknown command.
    """

    # The system prompt sets RIZYEE's personality and keeps answers
    # short (since they're spoken out loud, not read on screen).
    SYSTEM_PROMPT = (
        "You are RIZYEE, a friendly personal voice assistant for a user "
        "named Shiva. Answer clearly and concisely — your replies are "
        "spoken out loud, so keep them short (1-3 sentences) and easy to "
        "hear. Don't use bullet points or code blocks unless asked. "
        "If you don't know something, say so simply."
    )

    def __init__(self, model: str = DEFAULT_MODEL, url: str = OLLAMA_URL):
        """
        Set up the chat client.

        Args:
            model: The Ollama model name. Defaults to "llama3.2".
            url:   The Ollama chat API endpoint.
        """
        self.model = model
        self.url = url
        # Start the conversation with the system prompt so the model
        # knows how to behave from the very first message.
        self.messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        # We don't know yet whether Ollama is available. We find out on
        # the first ask(). None means "haven't checked yet".
        self.enabled = None

    def ask(self, user_text: str):
        """
        Send a question to Ollama and return the answer.

        Args:
            user_text: What the user said.

        Returns:
            The model's answer as a string, or None if Ollama isn't
            available (so the caller can fall back gracefully).
        """
        # If we already found Ollama isn't running, don't keep trying —
        # that would make every unknown command hang for the timeout.
        if self.enabled is False:
            return None

        # Add the user's message to the history.
        self.messages.append({"role": "user", "content": user_text})

        # Build the request body Ollama expects.
        payload = {
            "model": self.model,
            "messages": self.messages,
            "stream": False,  # we want the whole answer at once
        }
        data = json.dumps(payload).encode("utf-8")

        # Build the HTTP request. urllib is low-level but built-in.
        req = urllib.request.Request(
            self.url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            logger.info(f"Asking Ollama ({self.model})...")
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            # The answer comes back in message.content.
            answer = result.get("message", {}).get("content", "").strip()

            if answer:
                # Save the assistant's reply to the history so the
                # conversation makes sense over multiple turns.
                self.messages.append({"role": "assistant", "content": answer})
                self.enabled = True
                logger.info(f"Ollama answered ({len(answer)} chars).")
                return answer

            logger.warning("Ollama returned an empty answer.")
            return None

        except urllib.error.URLError as e:
            # Connection refused / can't reach Ollama → not installed or
            # not running. Flip the flag so we don't retry every time.
            logger.warning(f"Ollama not reachable: {e.reason}")
            self.enabled = False
            # Remove the user message we added, since we didn't get an
            # answer — keeps the history from filling with unanswered
            # questions in case Ollama comes online later.
            if self.messages and self.messages[-1]["role"] == "user":
                self.messages.pop()
            return None
        except Exception as e:
            # Any other error (timeout, malformed response, etc.).
            logger.error(f"Chat failed: {e}")
            if self.messages and self.messages[-1]["role"] == "user":
                self.messages.pop()
            return None

    def reset(self) -> None:
        """Clear the conversation history (start fresh)."""
        self.messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        logger.info("Conversation history cleared.")
