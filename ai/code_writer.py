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


def _backup_relative_path(target: Path, workspace_root: Path) -> Path:
    if _is_relative_to(target, workspace_root):
        return target.relative_to(workspace_root)

    drive = target.drive.replace(":", "") if target.drive else "root"
    parts = [part for part in target.parts if part not in {target.anchor, target.drive, "\\"}]
    return Path("outside_workspace") / drive / Path(*parts)


def _resolve_target(path_text: str, base_dir: Path) -> Path:
    target = Path(path_text).expanduser()
    if not target.is_absolute():
        target = base_dir / target
    return target.resolve(strict=False)


def apply_file_writes(
    files: list[FileWrite],
    workspace_root: Path,
    allow_outside_workspace: bool,
    current_dir: Path | None = None,
) -> WriteResult:
    if not files:
        return WriteResult(output="No files were provided by the AI.", success=False)

    workspace_root = workspace_root.resolve(strict=False)
    base_dir = (current_dir or workspace_root).resolve(strict=False)
    backup_root = workspace_root / ".ai_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
    written = []
    backed_up = []

    for file in files:
        target = _resolve_target(file.path, base_dir)

        if not allow_outside_workspace and not _is_relative_to(target, workspace_root):
            return WriteResult(
                output=(
                    f"Blocked write outside AI workspace: {target}\n"
                    f"Workspace: {workspace_root}\n"
                    "Set AI_ALLOW_OUTSIDE_WORKSPACE=true to allow full-PC paths."
                ),
                success=False,
            )

        if target.exists() and target.is_file():
            backup = backup_root / _backup_relative_path(target, workspace_root)
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup)
            backed_up.append(str(backup))

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(file.content, encoding="utf-8", errors="replace")
        written.append(str(target))

    lines = ["AI code write completed.", "", f"Base directory: {base_dir}", "", "Written files:"]
    lines.extend(f"- {path}" for path in written)
    if backed_up:
        lines.extend(["", "Backups:"])
        lines.extend(f"- {path}" for path in backed_up)

    return WriteResult(output="\n".join(lines), success=True)
