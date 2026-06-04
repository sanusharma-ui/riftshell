from dataclasses import dataclass
from typing import Optional
import shlex


@dataclass
class ParsedCommand:
    raw: str
    name: str
    args: list[str]


class CommandParser:
    def parse(self, raw: str) -> Optional[ParsedCommand]:
        raw = raw.strip()
        if not raw:
            return None

        try:
            tokens = shlex.split(raw, posix=False)
        except ValueError:
            return None

        if not tokens:
            return None

        return ParsedCommand(
            raw=raw,
            name=tokens[0].lower(),
            args=tokens[1:]
        )