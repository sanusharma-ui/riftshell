from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ai.actions import AgentAction
from ai.config import AIConfig


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return {"action": "respond", "message": text or "No response from model."}

    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {"action": "respond", "message": text}


class MemoryManager:
    def __init__(self, path: str, limit: int, enabled: bool):
        self.path = Path(path)
        self.limit = limit
        self.enabled = enabled

    def load(self) -> list[dict]:
        if not self.enabled or not self.path.exists():
            return []
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []

    def add(self, role: str, content: str) -> None:
        if not self.enabled:
            return
        history = self.load()
        history.append({"role": role, "content": content})

        # Multiply limit by 2 because 1 turn = 1 user message + 1 assistant message
        max_messages = self.limit * 2
        if len(history) > max_messages:
            history = history[-max_messages:]

        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

    def format_for_prompt(self) -> str:
        history = self.load()
        if not history:
            return "No previous memory."
        return "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history])


@dataclass
class AgentPlanner:
    config: AIConfig
    command_names: list[str]
    command_catalog: list[str]
    current_dir_provider: Callable[[], Path] | None = None

    def __post_init__(self) -> None:
        # 1. Memory Setup using env vars or config
        memory_enabled = str(getattr(self.config, "ai_memory_enabled", os.getenv("AI_MEMORY_ENABLED", "true"))).lower() == "true"
        memory_path = getattr(self.config, "ai_memory_path", os.getenv("AI_MEMORY_PATH", ".riftshell_ai_memory.json"))
        memory_turns = int(getattr(self.config, "ai_memory_recent_turns", os.getenv("AI_MEMORY_RECENT_TURNS", 12)))

        self.memory = MemoryManager(path=memory_path, limit=memory_turns, enabled=memory_enabled)

        # 2. Gemini Setup
        self._gemini = None
        if getattr(self.config, "gemini_api_key", None):
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.config.gemini_api_key)
                self._gemini = genai.GenerativeModel(getattr(self.config, "gemini_model", "gemini-2.5-flash"))
            except Exception:
                pass

        # 3. Groq Fallback Setup
        self._groq = None
        groq_key = getattr(self.config, "groq_api_key", os.getenv("GROQ_API_KEY"))
        if groq_key:
            try:
                import groq
                self._groq = groq.Groq(api_key=groq_key)
                self._groq_model = getattr(self.config, "groq_model", os.getenv("GROQ_MODEL", "llama3-8b-8192"))
            except Exception:
                pass

    def plan(self, user_text: str) -> AgentAction:
        direct = self._fallback_plan(user_text)
        if direct.action != "respond" or direct.message or (self._gemini is None and self._groq is None):
            return direct

        prompt = self._build_prompt(user_text)
        action = None
        error_msg = ""

        # Attempt 1: Gemini
        if self._gemini:
            try:
                response = self._gemini.generate_content(prompt)
                text = getattr(response, "text", "") or ""
                action = AgentAction.from_payload(_extract_json(text))
            except Exception as exc:
                error_msg += f"Gemini error: {exc} | "

        # Attempt 2: Groq Fallback
        if action is None and self._groq:
            try:
                response = self._groq.chat.completions.create(
                    messages=[{"role": "system", "content": prompt}],
                    model=self._groq_model,
                    temperature=0.1,
                )
                text = response.choices[0].message.content
                action = AgentAction.from_payload(_extract_json(text))
            except Exception as exc:
                error_msg += f"Groq error: {exc}"

        # If both fail
        if action is None:
            return AgentAction(
                action="respond",
                message=f"I could not reach the AI model right now.\nDetails: {error_msg}",
            )

        # Save to Memory
        self.memory.add("user", user_text)
        # Save a compressed version of what the bot decided to do
        ai_response_summary = f"Action: {action.action}, Command: {action.command}, Message: {action.message}"
        self.memory.add("assistant", ai_response_summary)

        return action

    def _fallback_plan(self, user_text: str) -> AgentAction:
        text = user_text.strip()
        lowered = text.lower()
        first_word = lowered.split(maxsplit=1)[0] if lowered else ""
        command_names = {name.lower() for name in self.command_names}

        if not text:
            return AgentAction(
                action="respond",
                message="Tell me what you need. I can answer questions, explain things, or run RiftShell commands when you ask for computer work.",
            )

        if self._is_greeting(lowered):
            return AgentAction(
                action="respond",
                message="Hello. I am your RiftShell copilot. Ask me a question, or tell me what you want done on the system.",
            )

        if self._is_simple_general_question(lowered):
            return AgentAction(action="respond", message=self._answer_simple_general_question(lowered))

        if "screenshot" in lowered or "screen shot" in lowered or ("screen" in lowered and "photo" in lowered):
            return AgentAction(action="screenshot", message="Taking a screenshot.")
        if lowered in {"help", "commands", "command list", "show commands", "list commands"}:
            return AgentAction(action="shell", command="help")
        if any(phrase in lowered for phrase in ["file dikhao", "files dikhao", "folder dikhao", "list files"]) or lowered in {"ls", "dir", "files"}:
            return AgentAction(action="shell", command="files")
        if any(phrase in lowered for phrase in ["kaha ho", "where am i", "current folder"]) or lowered in {"pwd", "where"}:
            return AgentAction(action="shell", command="where")
        if re.search(r"\b(process|processes|tasklist|running tasks)\b", lowered):
            return AgentAction(action="shell", command="processes")
        if re.search(r"\b(ip|network config|ipconfig)\b", lowered):
            return AgentAction(action="shell", command="ip")
        if lowered in {"time", "current time", "what time is it", "show time"}:
            return AgentAction(action="shell", command="now")
        if lowered in {"date", "today", "current date", "show date"}:
            return AgentAction(action="shell", command="today")

        if first_word in command_names and not self._looks_like_chat(lowered):
            return AgentAction(action="shell", command=text)

        if self._gemini is None and self._groq is None:
            return self._offline_response(text)
        return AgentAction(action="respond", message="")

    def _is_greeting(self, lowered: str) -> bool:
        cleaned = re.sub(r"[^a-z0-9\s]", "", lowered).strip()
        words = cleaned.split()
        if not words:
            return False
        greetings = {
            "hello",
            "hi",
            "hey",
            "hii",
            "helo",
            "namaste",
            "namaskar",
            "salam",
            "yo",
        }
        if cleaned in greetings:
            return True
        return words[0] in greetings and len(words) <= 3

    def _looks_like_chat(self, lowered: str) -> bool:
        if lowered.endswith("?"):
            return True
        chat_starters = (
            "how ",
            "what ",
            "why ",
            "when ",
            "who ",
            "which ",
            "can you explain",
            "tell me",
            "explain ",
            "kya ",
            "kaise ",
            "kyu ",
            "batao ",
        )
        return lowered.startswith(chat_starters)

    def _is_simple_general_question(self, lowered: str) -> bool:
        return bool(
            re.search(r"\bhow\s+many\s+continents\b", lowered)
            or re.search(r"\bcontinents\s+(are|in)\b", lowered)
        )

    def _answer_simple_general_question(self, lowered: str) -> str:
        if "continent" in lowered:
            return "There are 7 continents: Asia, Africa, North America, South America, Antarctica, Europe, and Australia/Oceania."
        return "I can answer that, but I need the question to be a little clearer."

    def _offline_response(self, text: str) -> AgentAction:
        return AgentAction(
            action="respond",
            message=(
                "I can handle basic conversation and direct RiftShell commands locally. "
                "For broader AI answers, configure a Gemini or Groq API key. "
                "To run a command directly, send something like `files`, `where`, `ip`, or `/cmd files`."
            ),
        )

    def _build_prompt(self, user_text: str) -> str:
        catalog = "\n".join(f"- {item}" for item in self.command_catalog)
        history = self.memory.format_for_prompt()
        current_dir = self.current_dir_provider() if self.current_dir_provider else self.config.workspace_root
        access_mode = "FULL_PC" if self.config.allow_outside_workspace else "WORKSPACE_ONLY"

        return f"""
You are RiftShell Copilot: a friendly, practical AI assistant inside a Telegram-controlled Python shell.
You can chat naturally, answer general questions, clarify intent, and execute safe shell actions when the user clearly wants computer work.
Your output must always be STRICT, VALID JSON.

Allowed JSON shapes:
{{"action":"shell","command":"STRICT_COMMAND_HERE","message":"short explanation"}}
{{"action":"screenshot","message":"taking screenshot"}}
{{"action":"code_write","message":"writing code","files":[{{"path":"EXACT_GIVEN_PATH","content":"full code"}}]}}
{{"action":"respond","message":"chat or clarification"}}

Runtime context:
- Current directory: {current_dir}
- AI workspace root: {self.config.workspace_root}
- Access mode: {access_mode}

UNIVERSAL RULES (READ AND OBEY):
1. GENERAL CHAT IS ALLOWED: If the user greets you, asks a general knowledge question, asks for advice, or is just talking, return {{"action":"respond","message":"..."}} with a warm concise answer. Do not force a shell command.
2. COMMAND INTENT: Use "shell" only when the user clearly asks to inspect or change the computer, run a listed command, navigate files, show system info, capture screenshot, or execute a specific task.
3. READ THE CATALOG: Never guess command syntax. Look at the "Available Commands" catalog below. Format shell commands EXACTLY as the catalog requires.
4. UNKNOWN COMMANDS: If the user asks for something that is not supported by the catalog, respond conversationally and explain what you can do instead. Never say "No such commands" for general chat.
5. LOCATION: Relative paths run from the Current directory above. Use `cd <path>` when the user asks to move to a location. Use absolute paths only when the user gives or clearly asks for one.
6. FULL-PC MODE: If Access mode is FULL_PC, commands and code_write may target any user-provided location on this PC. If Access mode is WORKSPACE_ONLY, stay inside the AI workspace root.
7. WINDOWS PROCESSES: If killing or finding a process, append `.exe` (e.g., `kill chrome.exe`).
8. EXACT FILE PATHS (CRITICAL): Use the EXACT filename and path the user provides. Escape backslashes (e.g., `D:\\j.txt`). Do NOT change the filename.
9. NO CHAT IN COMMAND: The "command" field MUST ONLY contain executable RiftShell syntax. Put explanation in "message".
10. PIPING: You can use `|` if the catalog supports it.
11. CODE WRITES: Use "code_write" only when the user explicitly asks you to create or rewrite files with code/content. Keep file paths exact and content complete.
12. TONE: Use clear, professional English. Be helpful like a copilot, but do not pretend a command ran unless the action is "shell", "screenshot", or "code_write".

Routing examples:
- User: "hello" -> {{"action":"respond","message":"Hello. How can I help?"}}
- User: "How many continents are there?" -> {{"action":"respond","message":"There are 7 continents: Asia, Africa, North America, South America, Antarctica, Europe, and Australia/Oceania."}}
- User: "list files" -> {{"action":"shell","command":"files","message":"Listing files."}}
- User: "show my current folder" -> {{"action":"shell","command":"where","message":"Showing the current folder."}}
- User: "take a screenshot" -> {{"action":"screenshot","message":"Taking a screenshot."}}
- User: "write a Python script at hello.py that prints hello" -> {{"action":"code_write","message":"Preparing hello.py.","files":[{{"path":"hello.py","content":"print('hello')\n"}}]}}

Available Commands & Aliases:
{catalog}

Recent Conversation History:
{history}

User request:
{user_text}
""".strip()
