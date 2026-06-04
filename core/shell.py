from pathlib import Path

from core.base import CommandResult
from core.context import ShellContext
from core.parser import CommandParser
from commands import build_registry


class Shell:
    def __init__(self):
        start_dir = Path.cwd().resolve()
        self.ctx = ShellContext(cwd=start_dir)
        self.parser = CommandParser()
        self.registry = build_registry()
        self.ctx.registry = self.registry

    def prompt(self) -> str:
        return f"SanuShell {self.ctx.cwd}> "

    def execute_line(self, raw: str) -> CommandResult:
        parsed = self.parser.parse(raw)
        if parsed is None:
            return CommandResult(output="")

        self.ctx.history.append(parsed.raw)

        cmd = self.registry.get(parsed.name)
        if cmd is None:
            return CommandResult(output=f"Unknown command: {parsed.name}", success=False)

        try:
            result = cmd.execute(self.ctx, parsed.args)
            self.ctx.last_output = result.output
            if result.exit_shell:
                self.ctx.running = False
            return result
        except Exception as e:
            return CommandResult(output=f"[error] {e}", success=False)

    def run(self):
        print("SanuShell ready. Type 'help' to see commands.\n")

        while self.ctx.running:
            try:
                raw = input(self.prompt())
            except (KeyboardInterrupt, EOFError):
                print("\nexit")
                break

            result = self.execute_line(raw)
            if result.output:
                print(result.output)