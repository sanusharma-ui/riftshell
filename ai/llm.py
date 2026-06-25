from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

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

    def __post_init__(self) -> None:
        # 1. Memory Setup using env vars or config
        memory_enabled = str(getattr(self.config, "ai_memory_enabled", os.getenv("AI_MEMORY_ENABLED", "true"))).lower() == "true"
        memory_path = getattr(self.config, "ai_memory_path", os.getenv("AI_MEMORY_PATH", ".sanushell_ai_memory.json"))
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
        if direct.action != "respond" or (self._gemini is None and self._groq is None):
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
                    temperature=0.1
                )
                text = response.choices[0].message.content
                action = AgentAction.from_payload(_extract_json(text))
            except Exception as exc:
                error_msg += f"Groq error: {exc}"

        # If both fail
        if action is None:
            return AgentAction(action="respond", message=f"Dono models fail ho gaye bhai.\nDetails: {error_msg}")

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

        if not text:
            return AgentAction(action="respond", message="Kya karna hai?")
        if "screenshot" in lowered or "screen shot" in lowered or "screen" in lowered and "photo" in lowered:
            return AgentAction(action="screenshot", message="Taking screenshot.")
        if lowered in {"help", "commands", "command list"} or "help" in lowered:
            return AgentAction(action="shell", command="help")
        if any(word in lowered for word in ["file dikhao", "files dikhao", "folder dikhao", "list files", "ls"]):
            return AgentAction(action="shell", command="files")
        if any(word in lowered for word in ["kaha ho", "where am i", "current folder", "pwd"]):
            return AgentAction(action="shell", command="where")
        if "process" in lowered:
            return AgentAction(action="shell", command="processes")
        if "ip" in lowered:
            return AgentAction(action="shell", command="ip")
        if "time" in lowered or "samay" in lowered:
            return AgentAction(action="shell", command="now")
        if "date" in lowered or "tarikh" in lowered:
            return AgentAction(action="shell", command="today")
        if first_word in {name.lower() for name in self.command_names}:
            return AgentAction(action="shell", command=text)

        if self._gemini is None and self._groq is None:
            return AgentAction(
                action="respond",
                message="Koi API key set nahi hai (Gemini/Groq), isliye direct SanuShell command bhejo ya .env set karo.",
            )
        return AgentAction(action="respond", message="")

    def _build_prompt(self, user_text: str) -> str:
        commands = ", ".join(sorted(self.command_names))
        catalog = "\n".join(f"- {item}" for item in self.command_catalog)
        history = self.memory.format_for_prompt()

        return f"""
You are the agentic AI layer for SanuShell, a Windows-focused custom Python shell.
Convert the user's natural language request into exactly one JSON object and nothing else.

Allowed JSON shapes:
{{"action":"shell","command":"SanuShell command here","message":"short explanation"}}
{{"action":"screenshot","message":"short explanation"}}
{{"action":"code_write","message":"what will be written","files":[{{"path":"relative/path.py","content":"full file content"}}]}}
{{"action":"respond","message":"ask a short clarification or explain why not safe"}}

Rules:
- Prefer existing SanuShell commands over native commands.
- Existing command names are: {commands}
- Command catalog:
{catalog}
- For system/native commands use the SanuShell form: run <program> [args...].
- If the user asks to write or create code, use code_write with full file contents.
- Use relative paths for code_write unless the user explicitly gives an absolute path.
- Do not invent destructive commands. If the request is ambiguous, use respond.
- Dangerous commands will be approval-gated by the controller; still return the intended action.
- Keep the message short and in the user's Hinglish style when possible.
- Think like an operator: identify the user's goal, choose the smallest useful command/action, and avoid unnecessary steps.

Recent Conversation History:
{history}

User request:
{user_text}
""".strip()