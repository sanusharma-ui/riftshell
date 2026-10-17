"""Non-executable conversation transport, separate from workspace action JSON."""
import json

from ai.actions import AgentAction


WORKSPACE_HANDOFF = "[[ORBIT_WORKSPACE]]"


def conversation_action(text: str, *, truncated: bool = False) -> AgentAction | None:
    """Only produce a reply or an empty handoff; never return model effects."""
    answer = text.strip()
    if not answer:
        return None
    if answer.startswith("[[ORBIT_") or WORKSPACE_HANDOFF.startswith(answer):
        return AgentAction("inspect") if answer == WORKSPACE_HANDOFF and not truncated else None

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
