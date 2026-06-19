from dataclasses import dataclass
from typing import Optional
import shlex


@dataclass
class ParsedCommand:
    raw: str
    name: str
    args: list[str]
    redirect_path: str | None = None
    redirect_append: bool = False


@dataclass
class ParsedPipeline:
    raw: str
    commands: list[ParsedCommand]


@dataclass
class ParsedLinePart:
    operator: str
    pipeline: ParsedPipeline


class CommandParser:
    CONTROL_OPERATORS = ("&&", "||", ";")

    def parse(self, raw: str) -> Optional[ParsedCommand]:
        raw = raw.strip()
        if not raw:
            return None

        command_text, redirect_path, redirect_append = self._extract_redirect(raw)

        try:
            tokens = shlex.split(command_text, posix=False)
        except ValueError:
            return None

        if not tokens:
            return None

        return ParsedCommand(
            raw=command_text,
            name=tokens[0].lower(),
            args=tokens[1:],
            redirect_path=redirect_path,
            redirect_append=redirect_append,
        )

    def parse_line(self, raw: str) -> list[ParsedLinePart]:
        parts: list[ParsedLinePart] = []

        for operator, segment in self._split_controls(raw):
            commands = []
            for item in self._split_operator(segment, "|"):
                parsed = self.parse(item)
                if parsed is not None:
                    commands.append(parsed)

            if commands:
                parts.append(
                    ParsedLinePart(
                        operator=operator,
                        pipeline=ParsedPipeline(raw=segment.strip(), commands=commands),
                    )
                )

        return parts

    def _split_controls(self, raw: str) -> list[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        start = 0
        current_operator = ""
        i = 0
        quote: str | None = None

        while i < len(raw):
            ch = raw[i]
            if ch in ("'", '"'):
                quote = None if quote == ch else ch if quote is None else quote
                i += 1
                continue

            if quote is None:
                matched = next((op for op in self.CONTROL_OPERATORS if raw.startswith(op, i)), None)
                if matched:
                    segment = raw[start:i].strip()
                    if segment:
                        result.append((current_operator, segment))
                    current_operator = matched
                    i += len(matched)
                    start = i
                    continue

            i += 1

        segment = raw[start:].strip()
        if segment:
            result.append((current_operator, segment))
        return result

    def _split_operator(self, raw: str, operator: str) -> list[str]:
        result: list[str] = []
        start = 0
        i = 0
        quote: str | None = None

        while i < len(raw):
            ch = raw[i]
            if ch in ("'", '"'):
                quote = None if quote == ch else ch if quote is None else quote
                i += 1
                continue

            if quote is None and raw.startswith(operator, i):
                segment = raw[start:i].strip()
                if segment:
                    result.append(segment)
                i += len(operator)
                start = i
                continue

            i += 1

        segment = raw[start:].strip()
        if segment:
            result.append(segment)
        return result

    def _extract_redirect(self, raw: str) -> tuple[str, str | None, bool]:
        i = 0
        quote: str | None = None
        redirect_index = -1
        append = False

        while i < len(raw):
            ch = raw[i]
            if ch in ("'", '"'):
                quote = None if quote == ch else ch if quote is None else quote
                i += 1
                continue

            if quote is None and ch == ">":
                redirect_index = i
                append = i + 1 < len(raw) and raw[i + 1] == ">"
                i += 2 if append else 1
                continue

            i += 1

        if redirect_index == -1:
            return raw, None, False

        command_text = raw[:redirect_index].strip()
        path_text = raw[redirect_index + (2 if append else 1):].strip()
        if not command_text or not path_text:
            return raw, None, False

        try:
            path_tokens = shlex.split(path_text, posix=False)
        except ValueError:
            return raw, None, False

        return command_text, path_tokens[0] if path_tokens else None, append
