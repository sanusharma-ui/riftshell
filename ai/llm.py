from __future__ import annotations

import json
from dataclasses import dataclass

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


@dataclass
class AgentPlanner:
    config: AIConfig
    command_names: list[str]
    command_catalog: list[str]

    def __post_init__(self) -> None:
        self._model = None
        if not self.config.gemini_api_key:
            return

        try:
            import google.generativeai as genai

            genai.configure(api_key=self.config.gemini_api_key)
            self._model = genai.GenerativeModel(self.config.gemini_model)
        except Exception:
            self._model = None

    def plan(self, user_text: str) -> AgentAction:
        direct = self._fallback_plan(user_text)
        if direct.action != "respond" or self._model is None:
            return direct

        prompt = self._build_prompt(user_text)
        try:
            response = self._model.generate_content(prompt)
            text = getattr(response, "text", "") or ""
            return AgentAction.from_payload(_extract_json(text))
        except Exception as exc:
            return AgentAction(
                action="respond",
                message=f"Gemini planning failed: {exc}",
            )

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

        if self._model is None:
            return AgentAction(
                action="respond",
                message="Gemini key/dependency ready nahi hai, isliye direct SanuShell command bhejo ya .env set karo.",
            )
        return AgentAction(action="respond", message="")

    def _build_prompt(self, user_text: str) -> str:
        commands = ", ".join(sorted(self.command_names))
        catalog = "\n".join(f"- {item}" for item in self.command_catalog)
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

User request:
{user_text}
""".strip()





