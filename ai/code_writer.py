from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ai.actions import FileWrite


@dataclass(frozen=True)
class WriteResult:
    output: str
    success: bool


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def apply_file_writes(
    files: list[FileWrite],
    workspace_root: Path,
    allow_outside_workspace: bool,
) -> WriteResult:
    if not files:
        return WriteResult(output="No files were provided by the AI.", success=False)

    workspace_root = workspace_root.resolve(strict=False)
    backup_root = workspace_root / ".ai_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
    written = []
    backed_up = []

    for file in files:
        target = Path(file.path).expanduser()
        if not target.is_absolute():
            target = workspace_root / target
        target = target.resolve(strict=False)

        if not allow_outside_workspace and not _is_relative_to(target, workspace_root):
            return WriteResult(
                output=f"Blocked write outside workspace: {target}",
                success=False,
            )

        if target.exists() and target.is_file():
            rel = target.relative_to(workspace_root) if _is_relative_to(target, workspace_root) else target.name
            backup = backup_root / rel
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup)
            backed_up.append(str(backup))

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(file.content, encoding="utf-8", errors="replace")
        written.append(str(target))

    lines = ["AI code write completed.", "", "Written files:"]
    lines.extend(f"- {path}" for path in written)
    if backed_up:
        lines.extend(["", "Backups:"])
        lines.extend(f"- {path}" for path in backed_up)

    return WriteResult(output="\n".join(lines), success=True)

