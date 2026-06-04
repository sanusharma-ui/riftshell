from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ShellContext:
    cwd: Path
    history: list[str] = field(default_factory=list)
    last_output: str = ""
    running: bool = True
    registry: object | None = None

    def set_cwd(self, path: Path):
        self.cwd = path