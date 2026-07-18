from __future__ import annotations

from dataclasses import dataclass

from core.parser import CommandParser


@dataclass(frozen=True)
class SafetyDecision:
    requires_approval: bool
    reason: str = ""


class SafetyPolicy:
    """Decides whether an AI-planned action can run immediately."""

    DANGEROUS_RIFTSHELL_COMMANDS = {
        "delete",
        "remove",
        "del",
        "kill",
        "taskkill",
        "run",
        "exec",
        "native",
        "open",
        "download",
        "shift",
        "move",
        "rename",
        "duplicate",
        "copy",
        "zip",
        "unzip",
    }

    DANGEROUS_NATIVE_WORDS = {
        "rm",
        "rmdir",
        "del",
        "erase",
        "format",
        "shutdown",
        "restart",
        "reboot",
        "taskkill",
        "kill",
        "reg",
        "regedit",
        "bcdedit",
        "diskpart",
        "powershell",
        "cmd",
        "curl",
        "wget",
        "pip",
        "npm",
        "git",
        "ssh",
        "scp",
        "netsh",
    }

    def __init__(self) -> None:
        self.parser = CommandParser()

    def check_action(self, action: str, command: str = "") -> SafetyDecision:
        action = action.lower().strip()
        if action == "code_write":
            return SafetyDecision(True, "AI-generated code writes always need approval.")
        if action == "screenshot":
            return SafetyDecision(False)
        if action != "shell":
            return SafetyDecision(False)
        return self.check_shell_command(command)

    def check_shell_command(self, command: str) -> SafetyDecision:
        raw = command.strip()
        if not raw:
            return SafetyDecision(False)

        parsed_parts = self.parser.parse_line(raw)
        for part in parsed_parts:
            for parsed in part.pipeline.commands:
                name = parsed.name.lower()
                if name in self.DANGEROUS_RIFTSHELL_COMMANDS:
                    return SafetyDecision(True, f"`{name}` can change files, launch apps, or run native commands.")

                if name == "run" and parsed.args:
                    native = parsed.args[0].strip("\"'").lower()
                    if native in self.DANGEROUS_NATIVE_WORDS:
                        return SafetyDecision(True, f"Native command `{native}` needs approval.")

        lowered = raw.lower()
        for word in self.DANGEROUS_NATIVE_WORDS:
            if f" {word} " in f" {lowered} ":
                return SafetyDecision(True, f"`{word}` is a sensitive native/system command.")

        return SafetyDecision(False)

