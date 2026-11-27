/**
 * RIZYEE AI — Frontend Controller
 * Handles multi-view navigation, persistent chat sessions, browser voice
 * input/output, and robust communication with the FastAPI backend.
 */

const STORAGE_KEYS = {
  CHATS: "rizyee_chats_v1",
  ACTIVE_CHAT: "rizyee_active_chat_v1",
  API_BASE: "rizyee_api_base_v1",
  TTS_ENABLED: "rizyee_tts_enabled_v1",
};

const DEFAULT_API_BASE = "http://127.0.0.1:8000";
const WELCOME_MESSAGE =
  "Hello! I'm RIZYEE, your personal AI assistant. How can I help you today?";

const VIEW_META = {
  chat: {
    title: "AI Assistant",
    subtitle: "Ask questions, plan tasks, and explore RIZYEE",
  },
  voice: {
    title: "Voice Mode",
    subtitle: "Browser speech-to-text and spoken AI responses",
  },
  devices: {
    title: "Device Dashboard",
    subtitle: "Monitor your paired Windows laptop and remote task status",
  },
  permissions: {
    title: "Permissions & Security",
    subtitle: "Review action boundaries and approval rules",
  },
  milestones: {
    title: "Milestones & About",
    subtitle: "Complete RIZYEE architecture and phased build roadmap",
  },
  settings: {
    title: "Settings",
    subtitle: "Configure your FastAPI backend URL and local preferences",
  },
};

const state = {
  chats: [],
  activeChatId: null,
  apiBase: localStorage.getItem(STORAGE_KEYS.API_BASE) || DEFAULT_API_BASE,
  ttsEnabled: localStorage.getItem(STORAGE_KEYS.TTS_ENABLED) === "true",
  backendOnline: false,
  isGenerating: false,
  recognition: null,
  isListening: false,
};

// ---------------------------------------------------------------------------
// DOM References
// ---------------------------------------------------------------------------
const el = {
  sidebar: document.getElementById("sidebar"),
  sidebarBackdrop: document.getElementById("sidebar-backdrop"),
  openSidebarBtn: document.getElementById("open-sidebar-btn"),
  closeSidebarBtn: document.getElementById("close-sidebar-btn"),
  navItems: document.querySelectorAll(".nav-item[data-view]"),
  views: document.querySelectorAll(".view"),
  viewTitle: document.getElementById("view-title"),
  viewSubtitle: document.getElementById("view-subtitle"),
  newChatBtn: document.getElementById("new-chat-btn"),
  clearChatBtn: document.getElementById("clear-chat-btn"),
  clearHistoryBtn: document.getElementById("clear-history-btn"),
  historyList: document.getElementById("chat-history-list"),
  messageList: document.getElementById("message-list"),
  suggestedPrompts: document.getElementById("suggested-prompts"),
  chatInput: document.getElementById("chat-input"),
  sendBtn: document.getElementById("send-btn"),
  micBtn: document.getElementById("mic-btn"),
  voiceStatusHint: document.getElementById("voice-status-hint"),
  ttsToggleBtn: document.getElementById("tts-toggle-btn"),
  ttsToggleLabel: document.getElementById("tts-toggle-label"),
  backendStatusDot: document.getElementById("backend-status-dot"),
  backendStatusText: document.getElementById("backend-status-text"),
  voiceOrb: document.getElementById("voice-orb"),
  voicePanelStatus: document.getElementById("voice-panel-status"),
  voiceListenBtn: document.getElementById("voice-listen-btn"),
  voiceStopBtn: document.getElementById("voice-stop-btn"),
  apiUrlInput: document.getElementById("api-url-input"),
  saveSettingsBtn: document.getElementById("save-settings-btn"),
  resetSettingsBtn: document.getElementById("reset-settings-btn"),
  settingsFeedback: document.getElementById("settings-feedback"),
};

// ---------------------------------------------------------------------------
// Chat Storage Helpers
// ---------------------------------------------------------------------------
function createChatObject(title = "New conversation") {
  return {
    id: `chat_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
    title,
    createdAt: Date.now(),
    messages: [
      {
        role: "assistant",
        content: WELCOME_MESSAGE,
        timestamp: Date.now(),
      },
    ],
  };
}

function loadChats() {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.CHATS);
    const parsed = raw ? JSON.parse(raw) : [];
    state.chats = Array.isArray(parsed) && parsed.length > 0 ? parsed : [createChatObject()];
  } catch {
    state.chats = [createChatObject()];
  }

  const savedActive = localStorage.getItem(STORAGE_KEYS.ACTIVE_CHAT);
  const exists = state.chats.some((c) => c.id === savedActive);
  state.activeChatId = exists ? savedActive : state.chats[0].id;
  saveChats();
}

function saveChats() {
  localStorage.setItem(STORAGE_KEYS.CHATS, JSON.stringify(state.chats));
  localStorage.setItem(STORAGE_KEYS.ACTIVE_CHAT, state.activeChatId);
}

function getActiveChat() {
  return state.chats.find((c) => c.id === state.activeChatId) || state.chats[0];
}

// ---------------------------------------------------------------------------
// UI Rendering
// ---------------------------------------------------------------------------
function renderHistory() {
  el.historyList.innerHTML = "";
  state.chats.forEach((chat) => {
    const btn = document.createElement("button");
    btn.className = `history-item ${chat.id === state.activeChatId ? "active" : ""}`;
    btn.textContent = chat.title;
    btn.title = chat.title;
    btn.addEventListener("click", () => {
      state.activeChatId = chat.id;
      saveChats();
      renderHistory();
      renderMessages();
      switchView("chat");
      closeMobileSidebar();
    });
    el.historyList.appendChild(btn);
  });
}

function createCopyButton(text) {
  const btn = document.createElement("button");
  btn.className = "copy-btn";
  btn.title = "Copy response";
  btn.setAttribute("aria-label", "Copy response");
  const copyIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`;
  const checkIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
  btn.innerHTML = copyIcon;

  btn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(text);
      btn.innerHTML = checkIcon;
      setTimeout(() => {
        btn.innerHTML = copyIcon;
      }, 1500);
    } catch {
      btn.title = "Clipboard unavailable";
    }
  });
  return btn;
}

function renderMessages() {
  const chat = getActiveChat();
  el.messageList.innerHTML = "";

  chat.messages.forEach((msg) => {
    const row = document.createElement("div");
    row.className = `message-row ${msg.role}`;

    const meta = document.createElement("div");
    meta.className = "message-meta";
    meta.textContent = msg.role === "user" ? "You" : "RIZYEE AI";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.textContent = msg.content;

    if (msg.role === "assistant") {
      bubble.appendChild(createCopyButton(msg.content));
    }

    row.appendChild(meta);
    row.appendChild(bubble);
    el.messageList.appendChild(row);
  });

  const hasUserMessages = chat.messages.some((m) => m.role === "user");
  el.suggestedPrompts.style.display = hasUserMessages ? "none" : "grid";

  scrollToBottom();
}

function showTypingIndicator() {
  const row = document.createElement("div");
  row.className = "message-row assistant";
  row.id = "typing-row";

  const meta = document.createElement("div");
  meta.className = "message-meta";
  meta.textContent = "RIZYEE AI is thinking...";

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.innerHTML = `<div class="typing-dots"><span></span><span></span><span></span></div>`;

  row.appendChild(meta);
  row.appendChild(bubble);
  el.messageList.appendChild(row);
  scrollToBottom();
  return row;
}

function scrollToBottom() {
  el.messageList.scrollTop = el.messageList.scrollHeight;
}

// ---------------------------------------------------------------------------
// Navigation & Responsive Sidebar
// ---------------------------------------------------------------------------
function switchView(viewName) {
  el.views.forEach((view) => {
    view.classList.toggle("active", view.id === `view-${viewName}`);
  });
  el.navItems.forEach((item) => {
    item.classList.toggle("active", item.dataset.view === viewName);
  });

  const meta = VIEW_META[viewName] || VIEW_META.chat;
  el.viewTitle.textContent = meta.title;
  el.viewSubtitle.textContent = meta.subtitle;
}

function openMobileSidebar() {
  el.sidebar.classList.add("open");
  el.sidebarBackdrop.classList.add("open");
}

function closeMobileSidebar() {
  el.sidebar.classList.remove("open");
  el.sidebarBackdrop.classList.remove("open");
}

// ---------------------------------------------------------------------------
// Backend Health & Chat Request
// ---------------------------------------------------------------------------
async function checkBackendHealth() {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 2000);
    const res = await fetch(`${state.apiBase}/health`, { signal: controller.signal });
    clearTimeout(timer);
    state.backendOnline = res.ok;
  } catch {
    state.backendOnline = false;
  }

  el.backendStatusDot.className = `status-dot ${state.backendOnline ? "online" : "offline"}`;
  el.backendStatusText.textContent = state.backendOnline
    ? "Backend: Online"
    : "Backend: Offline (Using Local Assistant)";
}

function getSmartLocalReply(userText) {
  const lower = userText.toLowerCase();

  if (lower.includes("milestone") || lower.includes("building step") || lower.includes("roadmap")) {
    return (
      "RIZYEE Build Roadmap & Milestones (Shiva's Assistant):\n\n" +
      "1. Local Core (Milestones 1–7): Vosk offline STT, pyttsx3 TTS, custom openWakeWord ('RIZYEE' -> 'Yes Shiva.'), SQLite memory/reminders, Ollama chat, and Windows action executor.\n" +
      "2. Frontend Website (Current): Modern dark UI in `web/` with AI chat, speech mode, devices, and permissions.\n" +
      "3. FastAPI Backend: Secure endpoints for chat, auth, and task dispatch.\n" +
      "4. Windows Agent Pairing: One-time pairing code and secure outbound task polling.\n" +
      "5. Android Access: Mobile-responsive chat & remote Windows control.\n" +
      "6. Advanced Automation & Security: Screenshots, audit logs, and permission gating."
    );
  }

  if (lower.includes("python") || lower.includes("code") || lower.includes("debug") || lower.includes("programming")) {
    return (
      "I'd be happy to help you with Python and software development! As a BTech CS student, you can ask me to explain concepts, write functions, or debug errors. " +
      "Once you connect the local FastAPI backend with Ollama running (`ollama run llama3.2`), I'll generate fully customized AI code and explanations directly."
    );
  }

  if (lower.includes("hello") || lower.includes("hi") || lower.includes("hey")) {
    return "Hello Shiva! RIZYEE is online and ready. How can I help you with your project today?";
  }

  if (lower.includes("who are you") || lower.includes("what is rizyee")) {
    return "I am RIZYEE, your personal AI assistant built for Windows and web. I understand conversations, remember preferences, and can control your authorized laptop securely.";
  }

  return (
    `I understand you asked: "${userText}".\n\n` +
    `Right now the frontend is running in standalone mode. To get full AI generation, start your FastAPI backend (` +
    `uvicorn backend.app.main:app --reload) with Ollama running locally!`
  );
}

async function handleSendMessage(rawText) {
  const text = rawText.trim();
  if (!text || state.isGenerating) return;

  const chat = getActiveChat();
  if (chat.title === "New conversation") {
    chat.title = text.length > 34 ? `${text.slice(0, 34)}...` : text;
  }

  chat.messages.push({
    role: "user",
    content: text,
    timestamp: Date.now(),
  });
  saveChats();
  renderHistory();
  renderMessages();

  el.chatInput.value = "";
  autoResizeTextarea();

  state.isGenerating = true;
  el.sendBtn.disabled = true;
  const typingRow = showTypingIndicator();

  let replyText = "";

  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 3000);

    const res = await fetch(`${state.apiBase}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
      signal: controller.signal,
    });
    clearTimeout(timer);

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const data = await res.json();
    replyText = data.answer || data.reply || getSmartLocalReply(text);
    state.backendOnline = true;
  } catch {
    state.backendOnline = false;
    // Fallback gracefully to smart local response so the user always gets an immediate answer
    replyText = getSmartLocalReply(text);
  } finally {
    if (typingRow && typingRow.parentNode) {
      typingRow.remove();
    }
    state.isGenerating = false;
    el.sendBtn.disabled = false;
    checkBackendHealth();
  }

  chat.messages.push({
    role: "assistant",
    content: replyText,
    timestamp: Date.now(),
  });
  saveChats();
  renderMessages();

  if (state.ttsEnabled) {
    speakText(replyText);
  }
}

// ---------------------------------------------------------------------------
// Browser Voice (SpeechRecognition + SpeechSynthesis)
// ---------------------------------------------------------------------------
function speakText(text) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1.0;
  utterance.pitch = 1.0;
  window.speechSynthesis.speak(utterance);
}

function updateTtsButton() {
  el.ttsToggleBtn.classList.toggle("active", state.ttsEnabled);
  el.ttsToggleLabel.textContent = state.ttsEnabled ? "Voice Reply: On" : "Voice Reply: Off";
}

function setListeningUI(active, statusMessage) {
  state.isListening = active;
  el.micBtn.classList.toggle("listening", active);
  el.voiceOrb.classList.toggle("listening", active);
  if (statusMessage) {
    el.voiceStatusHint.textContent = statusMessage;
    el.voicePanelStatus.textContent = statusMessage;
  }
}

function startVoiceInput({ autoSend = false } = {}) {
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;

  if (!SpeechRecognition) {
    const msg =
      "Speech recognition is not supported in this browser. Please use Google Chrome on Windows or Android.";
    setListeningUI(false, msg);
    alert(msg);
    return;
  }

  if (state.isListening && state.recognition) {
    state.recognition.stop();
    return;
  }

  try {
    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    state.recognition = recognition;

    recognition.onstart = () => {
      setListeningUI(true, "Listening... Speak your prompt now!");
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript?.trim() || "";
      if (!transcript) return;

      setListeningUI(false, `Heard: "${transcript}"`);
      if (autoSend) {
        switchView("chat");
        handleSendMessage(transcript);
      } else {
        el.chatInput.value = transcript;
        autoResizeTextarea();
        el.chatInput.focus();
      }
    };

    recognition.onerror = (event) => {
      let reason = `Voice error: ${event.error}`;
      if (event.error === "not-allowed") {
        reason = "Microphone access denied. Please click the camera/mic icon in your browser address bar to allow microphone permissions.";
      } else if (event.error === "no-speech") {
        reason = "No speech detected. Please try speaking closer to your microphone.";
      }
      setListeningUI(false, reason);
    };

    recognition.onend = () => {
      if (state.isListening) {
        setListeningUI(false, "Voice input ended.");
      }
    };

    recognition.start();
  } catch (err) {
    setListeningUI(false, `Could not start voice recognition: ${err.message}`);
  }
}

function stopVoiceInput() {
  if (state.recognition && state.isListening) {
    state.recognition.stop();
  }
  setListeningUI(false, "Voice input stopped.");
}

// ---------------------------------------------------------------------------
// Textarea Auto-resize & Event Wiring
// ---------------------------------------------------------------------------
function autoResizeTextarea() {
  el.chatInput.style.height = "auto";
  el.chatInput.style.height = `${Math.min(el.chatInput.scrollHeight, 150)}px`;
}

function initEvents() {
  el.openSidebarBtn.addEventListener("click", openMobileSidebar);
  el.closeSidebarBtn.addEventListener("click", closeMobileSidebar);
  el.sidebarBackdrop.addEventListener("click", closeMobileSidebar);

  el.navItems.forEach((btn) => {
    btn.addEventListener("click", () => {
      switchView(btn.dataset.view);
      closeMobileSidebar();
    });
  });

  document.querySelectorAll("[data-view-link]").forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      switchView(link.dataset.viewLink);
      closeMobileSidebar();
    });
  });

  el.newChatBtn.addEventListener("click", () => {
    const newChat = createChatObject();
    state.chats.unshift(newChat);
    state.activeChatId = newChat.id;
    saveChats();
    renderHistory();
    renderMessages();
    switchView("chat");
    closeMobileSidebar();
    el.chatInput.focus();
  });

  el.clearChatBtn.addEventListener("click", () => {
    const chat = getActiveChat();
    chat.title = "New conversation";
    chat.messages = [
      {
        role: "assistant",
        content: WELCOME_MESSAGE,
        timestamp: Date.now(),
      },
    ];
    saveChats();
    renderHistory();
    renderMessages();
  });

  el.clearHistoryBtn.addEventListener("click", () => {
    state.chats = [createChatObject()];
    state.activeChatId = state.chats[0].id;
    saveChats();
    renderHistory();
    renderMessages();
  });

  document.querySelectorAll(".prompt-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const prompt = chip.dataset.prompt || "";
      handleSendMessage(prompt);
    });
  });

  el.chatInput.addEventListener("input", autoResizeTextarea);
  el.chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(el.chatInput.value);
    }
  });
  el.sendBtn.addEventListener("click", () => handleSendMessage(el.chatInput.value));

  el.micBtn.addEventListener("click", () => startVoiceInput({ autoSend: false }));
  el.voiceListenBtn.addEventListener("click", () => startVoiceInput({ autoSend: true }));
  el.voiceStopBtn.addEventListener("click", stopVoiceInput);

  el.ttsToggleBtn.addEventListener("click", () => {
    state.ttsEnabled = !state.ttsEnabled;
    localStorage.setItem(STORAGE_KEYS.TTS_ENABLED, String(state.ttsEnabled));
    updateTtsButton();
    if (!state.ttsEnabled && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
  });

  el.apiUrlInput.value = state.apiBase;
  el.saveSettingsBtn.addEventListener("click", async () => {
    const cleaned = el.apiUrlInput.value.trim().replace(/\/+$/, "") || DEFAULT_API_BASE;
    state.apiBase = cleaned;
    el.apiUrlInput.value = cleaned;
    localStorage.setItem(STORAGE_KEYS.API_BASE, cleaned);
    await checkBackendHealth();
    el.settingsFeedback.textContent = state.backendOnline
      ? `Saved and connected to ${cleaned}`
      : `Saved ${cleaned}. Backend is currently offline (smart local responses active).`;
  });

  el.resetSettingsBtn.addEventListener("click", async () => {
    state.apiBase = DEFAULT_API_BASE;
    el.apiUrlInput.value = DEFAULT_API_BASE;
    localStorage.setItem(STORAGE_KEYS.API_BASE, DEFAULT_API_BASE);
    await checkBackendHealth();
    el.settingsFeedback.textContent = `Reset to default (${DEFAULT_API_BASE}).`;
  });
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  loadChats();
  renderHistory();
  renderMessages();
  updateTtsButton();
  initEvents();
  checkBackendHealth();
});
