"""User-owned Orbit budgets. Presets are starting values, never routing rules."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, replace
from pathlib import Path


# Shared validation ranges for JSON configuration and the desktop editor.
MODE_LIMITS = {
    "prompt_tokens": (2000, 200000), "output_tokens": (128, 32768),
    "history_turns": (0, 50), "max_files": (1, 100),
    "file_chars": (256, 100000), "max_steps": (1, 20),
    "inspection_passes": (1, 10),
}


@dataclass(frozen=True)
class OrbitMode:
    name: str = "Balanced"
    prompt_tokens: int = 4500
    output_tokens: int = 768
    history_turns: int = 3
    max_files: int = 3
    file_chars: int = 4000
    max_steps: int = 4
    inspection_passes: int = 2
    compact_prompt: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "OrbitMode":
        if not isinstance(data, dict) or set(data) - set(cls.__dataclass_fields__):
            raise ValueError("Each Orbit mode must contain only supported mode settings.")
        mode = cls(**data)
        if not isinstance(mode.name, str) or not mode.name.strip() or len(mode.name) > 40:
            raise ValueError("Orbit mode names must contain 1 to 40 characters.")
        for key, (low, high) in MODE_LIMITS.items():
            value = getattr(mode, key)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"Orbit {key} must be an integer from {low} to {high}.")
        if type(mode.compact_prompt) is not bool:
            raise ValueError("Orbit compact_prompt must be true or false.")
        return replace(mode, name=mode.name.strip())


def default_modes() -> tuple[OrbitMode, ...]:
    return (OrbitMode(), OrbitMode(
        name="High", prompt_tokens=32000, output_tokens=4096, history_turns=12,
        max_files=16, file_chars=16000, max_steps=8, inspection_passes=3,
        compact_prompt=False,
    ))


def decode_modes(text: str) -> tuple[OrbitMode, ...]:
    try:
        values = json.loads(text)
        if not isinstance(values, list) or not 1 <= len(values) <= 20:
            raise ValueError("Provide between 1 and 20 Orbit modes in a JSON array.")
        modes = tuple(OrbitMode.from_dict(value) for value in values)
        if len({mode.name.casefold() for mode in modes}) != len(modes):
            raise ValueError("Orbit mode names must be unique.")
        return modes
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid Orbit modes JSON. Check AI_MODES_FILE or Orbit mode settings.") from exc


def encode_modes(modes: tuple[OrbitMode, ...]) -> str:
    return json.dumps([asdict(mode) for mode in modes], indent=2)


def select_mode(modes: tuple[OrbitMode, ...], name: str) -> OrbitMode:
    for mode in modes:
        if mode.name.casefold() == name.strip().casefold():
            return mode
    raise ValueError(f"Unknown Orbit mode '{name}'. Choose: {', '.join(m.name for m in modes)}")


def modes_from_env() -> tuple[tuple[OrbitMode, ...], OrbitMode]:
    path = os.getenv("AI_MODES_FILE", "").strip()
    modes = default_modes()
    if path:
        try:
            modes = decode_modes(Path(path).expanduser().read_text(encoding="utf-8"))
        except OSError as exc:
            raise ValueError("Cannot read AI_MODES_FILE. Choose an existing Orbit modes JSON file.") from exc
    return modes, select_mode(modes, os.getenv("AI_MODE", modes[0].name))


def estimated_tokens(text: str) -> int:
    """Local planning estimate, NOT a provider tokenizer or remaining quota.

    Three UTF-8 bytes per token leaves more headroom than the usual English
    four-character estimate. Actual tokenization varies by model and content.
    """
    return (len(text.encode("utf-8")) + 2) // 3


def fit_text(text: str, tokens: int, *, tail: bool = False) -> str:
    if tokens <= 0:
        return ""
    if estimated_tokens(text) <= tokens:
        return text
    marker = "\n[Context shortened to the selected Orbit budget]\n"
    if tokens * 3 < len(marker.encode("utf-8")):
        return "..."[:tokens * 3]
    allowance = max(0, tokens * 3 - len(marker.encode("utf-8")))
    raw = text.encode("utf-8")
    fragment = (raw[-allowance:] if tail and allowance else raw[:allowance]).decode("utf-8", errors="ignore")
    return marker + fragment if tail else fragment + marker


class PromptBudgetError(ValueError):
    pass


class OutputBudgetError(ValueError):
    def __init__(self, message: str, *, partial_text: str = ""):
        super().__init__(message)
        # Visible final-answer content only; never internal reasoning tokens.
        self.partial_text = partial_text
