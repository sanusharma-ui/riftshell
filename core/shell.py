from pathlib import Path

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

    def run(self):
        print("SanuShell ready. Type 'help' to see commands.\n")

        while self.ctx.running:
            try:
                raw = input(self.prompt())
            except (KeyboardInterrupt, EOFError):
                print("\nexit")
                break

            parsed = self.parser.parse(raw)
            if parsed is None:
                continue

            self.ctx.history.append(parsed.raw)

            cmd = self.registry.get(parsed.name)
            if cmd is None:
                print(f"Unknown command: {parsed.name}")
                continue

            try:
                result = cmd.execute(self.ctx, parsed.args)
                if result.output:
                    print(result.output)
                self.ctx.last_output = result.output
                if result.exit_shell:
                    self.ctx.running = False
            except Exception as e:
                print(f"[error] {e}")