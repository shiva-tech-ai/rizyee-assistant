# RIZYEE

**Personal AI Voice Assistant for Windows**

RIZYEE is an intelligent voice assistant built in Python that can:
- Understand natural spoken language
- Answer questions like an AI chatbot
- Control your Windows laptop using voice commands
- Open, close, and manage applications
- Search the internet and YouTube
- Manage files and folders
- Help with programming and development

### Voice commands (Milestones 3, 4, 5 & 6)

Say "RIZYEE" to wake it, then try:

| You say... | RIZYEE does |
|---|---|
| "what time is it" | speaks the current time |
| "what's the date" / "what day" | speaks today's date |
| "open notepad" / "open chrome" | launches the app |
| "close chrome" | asks "Should I close chrome?", then shuts it down if you say yes |
| "open youtube" | opens the YouTube homepage in your browser |
| "open google" / "open gmail" / "open github" | opens that website |
| "search youtube cats" | opens YouTube search results |
| "search for python tips" | opens Google search results |
| "volume up" / "volume down" / "mute" | changes system volume |
| "who are you" | introduces itself |
| "remember that my wifi password is mango123" | stores a fact in its SQLite memory |
| "what is my wifi password" | recalls the stored fact |
| "what do you remember" | lists everything it knows |
| "forget my wifi password" | deletes a stored fact |
| "remind me to drink water at 4 pm" | sets a reminder and speaks it when due |
| "remind me to call mom in 30 minutes" | sets a relative-time reminder |
| "ask what is python" | answers via a local AI model (Ollama) |
| "what is the capital of france" | answers general-knowledge questions via the AI |
| "goodbye" / "stop" | shuts RIZYEE down |

RIZYEE replies by voice **and** prints `RIZYEE: ...` text on screen, so you can always read what it said even if the audio was unclear. Closing an app asks for your confirmation first (say yes/yeah/ok or no/nope/cancel).

### Clean terminal

By default RIZYEE shows only its spoken replies and what you said — the detailed logs are hidden. If you're troubleshooting recognition, run with debug logs on:

```bash
$env:RIZYEE_DEBUG = "1"; python -m rizyee.main
```

### Optional: enable AI chat (Milestone 5)

RIZYEE answers questions with a local model through [Ollama](https://ollama.com). This is optional — without it, questions fall back to a friendly "AI not running" message and everything else still works.

```bash
# 1. Install Ollama from https://ollama.com
# 2. Pull a small model (one-time, ~2 GB)
ollama pull llama3.2
# 3. Make sure Ollama is running (it usually starts automatically)
#    Then just run RIZYEE as normal.
```

## Quick Start

```bash
# 1. Create virtual environment
python -m venv venv

# 2. Activate it
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download the speech model (one-time, ~450 MB)
python -m rizyee.utils.download_model

# 5. Run RIZYEE
python -m rizyee.main
```

## Project Structure

```
omniroute/
├── rizyee/          → Main application package
│   ├── speech/      → Listen (Vosk) + Speak (pyttsx3) + Wake word
│   ├── brain/       → Command parsing + AI chat (Ollama)
│   ├── actions/     → System control, apps, web search, files
│   └── utils/       → Logging and helpers
├── models/          → Vosk speech model
├── data/            → SQLite database and user data
└── tests/           → Test files
```

## Developer

Built by **Shiva** — BTech Computer Science & IT student.

## License

Personal project. All rights reserved.
