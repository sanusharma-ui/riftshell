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
        r"I don't have access to (?:the\s+)?(?:current\s+)?(?:system\s+)?(?:clock|hardware|hardware details|disks?|drives?)|"
        r"cannot (?:provide|determine) (?:the\s+)?(?:exact\s+)?(?:current\s+)?(?:date|time|how many disks?|how many drives?)|"
        r"run a command such as `(?:lsblk|diskutil|wmic|df|fdisk|Get-Disk|Get-PhysicalDisk)|"
        r"Microsoft Store\s*->\s*[\"']?Themes[\"']?|"
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


# Replies that, on their own, mean "yes, go ahead" (English + Hinglish).
CONFIRMATION_PHRASES = {
    "yes", "yeah", "yep", "sure", "ok", "okay", "proceed", "go ahead",
    "do it", "run it", "execute", "confirm", "agreed", "correct",
    "haan", "ha", "bilkul", "kar do", "karo", "chal", "theek hai",
    "thik hai", "ho jaye", "ho jao", "chal do", "bhai kar do",
}
_CONFIRMATION_WORDS = {
    "yes", "yeah", "yep", "sure", "ok", "okay", "please", "proceed", "go", "ahead",
    "do", "it", "confirm", "confirmed", "agreed", "correct",
    "haan", "han", "ha", "bilkul", "kar", "karo", "chal", "theek", "thik", "hai",
    "ho", "jaye", "jao", "bhai", "de", "dena",
}
_STRONG_CONFIRMATION_WORDS = {
    "yes", "yeah", "yep", "sure", "ok", "okay", "proceed", "confirm", "confirmed",
    "agreed", "haan", "han", "ha", "bilkul", "kar", "karo", "chal", "theek", "thik",
    "jaye", "jao",
}


def is_confirmation(text: str) -> bool:
    """True only for short replies such as "yes", "haan kar do" or "ok go ahead".

    A longer sentence never counts, so a new request like "delete a.txt kar do"
    is not mistaken for approval of a pending plan.
    """
    normalized = re.sub(r"[^\w\s]", "", text.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return False
    if normalized in CONFIRMATION_PHRASES:
        return True
    words = normalized.split()
    return (
        len(words) <= 4
        and all(word in _CONFIRMATION_WORDS for word in words)
        and any(word in _STRONG_CONFIRMATION_WORDS for word in words)
    )
