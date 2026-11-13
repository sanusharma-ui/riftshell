"""Non-executable conversation transport, separate from workspace action JSON."""
import json
import re

from ai.actions import AgentAction


WORKSPACE_HANDOFF = "[[ORBIT_WORKSPACE]]"


def conversation_action(text: str, *, truncated: bool = False) -> AgentAction | None:
    """Only produce a reply or an empty handoff; never return model effects."""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    answer = cleaned if cleaned else text.strip()
    if not answer:
        return None
    if WORKSPACE_HANDOFF in answer or answer.startswith("[[ORBIT_") or WORKSPACE_HANDOFF.startswith(answer):
        return AgentAction("inspect") if not truncated else None

    # If the model attempted to propose an action, explain shell execution, or deflect a system query in conversational mode,
    # hand off to the workspace planner so RiftShell can actually execute it in the terminal.
    if re.search(
        r"Proposed (?:next )?action(?: \(execution not confirmed\))?:\s*(?:shell|code_write)|"
        r"^\s*Command:\s*\S|"
        r"```(?:shell|bash|cmd|powershell|sh|bat)\b|"
        r"^\s*cd\s+(?:/d\s+)?[a-zA-Z]:|"
        r"\b(?:command prompt|terminal)\b.*?\b(?:run|use|type)\b|"
        r"I don't have access to the (?:current )?system clock|"
        r"cannot provide the exact (?:current )?date|"
        r"by running (?:date|time|[a-zA-Z0-9_\-]+) in a terminal",
        answer,
        re.MULTILINE | re.IGNORECASE,
    ):
        return None if truncated else AgentAction("inspect")

    # Compatibility with models echoing old envelopes from conversation history.
    # Parse only complete JSON and discard every field except a reply's message.
    if answer.startswith("{") and '"action"' in answer[:100]:
        try:
            payload = json.loads(answer)
        except ValueError:
            return None
        if not isinstance(payload, dict):
            return None
        if payload.get("action") != "respond":
            return None if truncated else AgentAction("inspect")
        answer = payload.get("message")
        if not isinstance(answer, str) or not answer.strip():
            return None
        answer = answer.strip()
    if truncated:
        if answer.count("```") % 2:
            answer += "\n```"
        answer += "\n\n*The reply stopped here. Ask me to continue for the rest.*"
    return AgentAction("respond", answer)
