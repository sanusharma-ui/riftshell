from pathlib import Path
import os
import shutil


PROTECTED_PATHS = {
    Path.home().resolve(strict=False),
}

if os.name == "nt":
    for value in (os.environ.get("SystemRoot"), os.environ.get("WINDIR")):
        if value:
            PROTECTED_PATHS.add(Path(value).resolve(strict=False))


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def _ctx_workspace_root(ctx) -> Path | None:
    root = getattr(ctx, "workspace_root", None)
    if root is None:
        return None
    return Path(root).expanduser().resolve(strict=False)


def _ctx_allows_outside_workspace(ctx) -> bool:
    return bool(getattr(ctx, "allow_outside_workspace", True))


def is_path_allowed(ctx, path: Path) -> bool:
    workspace_root = _ctx_workspace_root(ctx)
    if workspace_root is None or _ctx_allows_outside_workspace(ctx):
        return True
    return _is_relative_to(path.resolve(strict=False), workspace_root)


def ensure_path_allowed(ctx, path: Path) -> Path:
    resolved = path.resolve(strict=False)
    if not is_path_allowed(ctx, resolved):
        workspace_root = _ctx_workspace_root(ctx)
        raise PermissionError(
            f"Blocked path outside AI workspace: {resolved}. "
            f"Workspace: {workspace_root}. Set AI_ALLOW_OUTSIDE_WORKSPACE=true to allow full-PC paths."
        )
    return resolved


def _is_drive_root(path: Path) -> bool:
    resolved = path.resolve(strict=False)
    return resolved.parent == resolved


def ensure_safe_delete_target(path: Path) -> None:
    resolved = path.resolve(strict=False)
    if _is_drive_root(resolved):
        raise PermissionError(f"Refusing to delete drive/root path: {resolved}")

    for protected in PROTECTED_PATHS:
        if resolved == protected:
            raise PermissionError(f"Refusing to delete protected folder: {resolved}")


def resolve_path(ctx, user_path: str | None = None) -> Path:
    base = Path(ctx.cwd)

    if not user_path or user_path.strip() == "":
        target = base
    else:
        candidate = Path(user_path).expanduser()
        target = candidate if candidate.is_absolute() else (base / candidate)

    return ensure_path_allowed(ctx, target)


def list_entries(path: Path, folders_only: bool = False) -> str:
    if not path.exists():
        return f"Path not found: {path}"
    if not path.is_dir():
        return f"Not a directory: {path}"

    items = []
    for item in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if folders_only and not item.is_dir():
            continue

        kind = "<DIR>" if item.is_dir() else "FILE "
        try:
            size = "-" if item.is_dir() else f"{item.stat().st_size} B"
        except Exception:
            size = "?"
        items.append(f"{kind:6} {size:10} {item.name}")

    return "\n".join(items) if items else "(empty)"


def tree_view(path: Path, max_depth: int = 4) -> str:
    if not path.exists():
        return f"Path not found: {path}"

    lines = [path.name if path.name else str(path)]

    def walk(current: Path, depth: int, prefix: str = ""):
        if depth > max_depth:
            return
        try:
            entries = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except Exception as e:
            lines.append(f"{prefix}[error] {e}")
            return

        for i, entry in enumerate(entries):
            branch = "└── " if i == len(entries) - 1 else "├── "
            lines.append(f"{prefix}{branch}{entry.name}")
            if entry.is_dir():
                next_prefix = prefix + ("    " if i == len(entries) - 1 else "│   ")
                walk(entry, depth + 1, next_prefix)

    if path.is_dir():
        walk(path, 1)

    return "\n".join(lines)


def find_names(start: Path, needle: str, folders_only: bool = False) -> list[str]:
    results = []
    needle = needle.lower()

    if not start.exists():
        return results

    for p in start.rglob("*"):
        if folders_only and not p.is_dir():
            continue
        if needle in p.name.lower():
            results.append(str(p))
    return results


def find_text(start: Path, needle: str) -> list[str]:
    results = []
    needle = needle.lower()

    if not start.exists():
        return results

    for p in start.rglob("*"):
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for i, line in enumerate(text.splitlines(), start=1):
            if needle in line.lower():
                results.append(f"{p} [{i}]: {line.strip()}")
                if len(results) >= 200:
                    return results
    return results


def copy_item(src: Path, dst: Path):
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def move_item(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))


def delete_item(path: Path):
    ensure_safe_delete_target(path)
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
