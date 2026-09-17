"""Local command extraction. This module never executes commands or calls a model."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Literal, Protocol

from core.parser import CommandParser
from core.registry import CommandMetadata


@dataclass(frozen=True)
class IntentRule:
    """A trusted, whole-request grammar for one registered command.

    Pattern captures become argument slots; constants (e.g. delete's `confirm`)
    stay separate. `starts` indexes patterns by first word, never by substrings.
    """

    intent: str
    command: str
    message: str
    phrases: tuple[str, ...] = ()
    patterns: tuple[str, ...] = ()
    starts: tuple[str, ...] = ()
    arguments: tuple[str, ...] = ()
    slots: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class CommandCandidate:
    intent: str
    name: str
    arguments: tuple[str, ...]
    message: str
    source: str = "rules"
    confidence: float = 1.0  # Grammar certainty, not a calibrated probability.

    @property
    def command(self) -> str:
        return " ".join((self.name, *(quote_argument(arg) for arg in self.arguments)))


@dataclass(frozen=True)
class Extraction:
    status: Literal["matched", "no_match", "ambiguous"] = "no_match"
    candidates: tuple[CommandCandidate, ...] = ()

    @property
    def match(self) -> CommandCandidate | None:
        return self.candidates[0] if self.status == "matched" and len(self.candidates) == 1 else None


class IntentExtractor(Protocol):
    """Future ML/LLM adapters can return candidates through this same contract."""

    def extract(self, text: str) -> Extraction: ...


_UNSAFE = re.compile(r'''[\x00-\x1f\x7f"'`$%;&|<>]''')
_RESERVED = frozenset((
    "it this that these those them me you us him her here there something anything everything all "
    "command commands file folder directory code script program app website current parent home "
    "mat nahi nahin nhi don't dont never not please plz abhi isko usko ye yeh woh "
    "kya kaise kyun kyu how why when if unless and then aur phir kar karo kardo do"
).split())
_PREFIX = re.compile(
    r"^(?:(?:hey\s+)?orbit[, ]+)?(?:please\s+|kindly\s+|plz\s+)?"
    r"(?:(?:can|could|would|will)\s+you\s+(?:please\s+)?|"
    r"i(?:'d| would)\s+like\s+you\s+to\s+|i\s+want\s+you\s+to\s+)?",
    re.IGNORECASE,
)
_SUFFIX = re.compile(r",?\s+(?:please|plz|thanks|thank you)[.!?]?$", re.IGNORECASE)


def normalize_request(text: str) -> str:
    # Preserve case, spaces inside paths, and punctuation belonging to arguments.
    return _SUFFIX.sub("", _PREFIX.sub("", text.strip())).strip()


def phrase_key(text: str) -> str:
    return " ".join(text.casefold().split()).rstrip(".!?")


def quote_argument(value: str) -> str:
    if not value or _UNSAFE.search(value):
        raise ValueError("Argument cannot be represented as a literal RiftShell argument")
    return f'"{value}"' if any(ch.isspace() for ch in value) else value


def _slot_value(raw: str, kind: str) -> str | None:
    quoted = len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'"
    value = raw[1:-1] if quoted else raw
    if not value or value != value.strip() or _UNSAFE.search(value):
        return None
    if kind == "integer":
        return value if value.isascii() and value.isdigit() and 0 < int(value) <= 10000 else None
    if kind == "host":
        return value if value.casefold() not in _RESERVED and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9.-]{0,252}", value) else None
    if kind not in {"path", "file_path"}:
        return None
    if not quoted and (value.casefold() in _RESERVED or any(ch.isspace() for ch in value)):
        return None
    if any(ch in value for ch in "*?\n\r"):
        return None
    # Don't turn sentence punctuation into a different file target.
    if value.endswith((".", "!", ",")) and value not in {".", ".."}:
        return None
    if kind == "file_path" and not quoted and not re.search(r"[./\\]", value):
        return None
    return value


class RuleIntentExtractor:
    """Indexed exact phrases + compiled grammars; misses are silent abstentions.

    No fuzzy execution, network, filesystem inspection, or mutation. Conflicting
    complete matches abstain. Only commands in the live registry are eligible.
    """

    MAX_REQUEST_LENGTH = 4096

    def __init__(
        self,
        command_names: Iterable[str],
        *,
        metadata: Iterable[CommandMetadata] = (),
        rules: Iterable[IntentRule] | None = None,
    ):
        if rules is None:
            from ai.command_intents import BUILTIN_INTENTS
            rules = BUILTIN_INTENTS
        self.names = frozenset(name.lower() for name in command_names)
        definitions = list(rules)
        for meta in metadata:
            # Plugins opt in explicitly. Never infer executable phrases from
            # descriptions or accept a declaration for a different command.
            declared = meta.extra.get("orbit_intents", ())
            if isinstance(declared, (tuple, list)):
                definitions.extend(rule for rule in declared
                                   if isinstance(rule, IntentRule) and rule.command == meta.name)
        self._phrases: dict[str, list[IntentRule]] = {}
        self._patterns: dict[str, list[tuple[IntentRule, re.Pattern]]] = {}
        for rule in definitions:
            if rule.command not in self.names:
                continue
            for phrase in rule.phrases:
                self._phrases.setdefault(phrase_key(phrase), []).append(rule)
            for pattern in rule.patterns:
                compiled = re.compile(pattern, re.IGNORECASE)
                for first in rule.starts or ("*",):
                    self._patterns.setdefault(first.casefold(), []).append((rule, compiled))

    def extract(self, text: str) -> Extraction:
        if not text or len(text) > self.MAX_REQUEST_LENGTH or any(c in text for c in "\n\r\x00"):
            return Extraction()
        request = normalize_request(text)
        if not request:
            return Extraction()
        matches: dict[str, CommandCandidate] = {}
        for rule in self._phrases.get(phrase_key(request), ()):
            self._collect(matches, rule, {})
        first = request.split(maxsplit=1)[0].casefold()
        for rule, pattern in (*self._patterns.get(first, ()), *self._patterns.get("*", ())):
            if match := pattern.fullmatch(request):
                slots = {}
                for name, kind in rule.slots:
                    value = _slot_value(match.groupdict().get(name) or "", kind)
                    if value is None:
                        break
                    slots[name] = value
                else:
                    self._collect(matches, rule, slots)
        candidates = tuple(matches.values())
        return Extraction("matched" if len(candidates) == 1 else "ambiguous" if candidates else "no_match", candidates)

    @staticmethod
    def _collect(matches: dict[str, CommandCandidate], rule: IntentRule, slots: dict[str, str]):
        try:
            args = tuple(slots[arg[1:-1]] if arg.startswith("{") and arg.endswith("}") else arg
                         for arg in rule.arguments)
            candidate = CommandCandidate(rule.intent, rule.command, args, rule.message)
            command = candidate.command
        except (KeyError, ValueError):
            return
        if valid_candidate(candidate, {rule.command}):
            matches[command] = candidate


def valid_candidate(candidate: CommandCandidate, names: Iterable[str]) -> bool:
    """Recheck even injected adapters: exactly one known command, literal args."""
    if candidate.name not in names or not re.fullmatch(r"[a-zA-Z][\w-]*", candidate.name):
        return False
    try:
        parts = CommandParser().parse_line(candidate.command)
    except (ValueError, TypeError):
        return False
    if len(parts) != 1 or len(parts[0].pipeline.commands) != 1:
        return False
    parsed = parts[0].pipeline.commands[0]
    return (parsed.name == candidate.name and not parsed.redirect_path
            and len(parsed.args) == len(candidate.arguments)
            and tuple(arg[1:-1] if arg.startswith('"') and arg.endswith('"') else arg for arg in parsed.args)
            == candidate.arguments)
