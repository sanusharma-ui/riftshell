from __future__ import annotations

import ast
import time
import ctypes
import getpass
import os
import platform
import shutil
import socket
import string
import subprocess
from datetime import datetime
from pathlib import Path
import random
import hashlib
import base64
import re
import urllib.request
import json
import tempfile
import zipfile
import webbrowser


from core.base import BaseCommand, CommandResult
from ui.themes import get_theme, list_themes
from version import __version__
from utils.safe_fs import (
    resolve_path,
    unquote_path,
    list_entries,
    tree_view,
    find_names,
    find_text,
    copy_item,
    move_item,
    delete_item,
)


def text_source(ctx, args, usage: str) -> tuple[str | None, CommandResult | None]:
    if ctx.piped_input:
        return ctx.piped_input, None

    if args:
        target = resolve_path(ctx, args[0])
        if not target.is_file():
            return None, CommandResult(output=f"Not a file: {target}", success=False)
        try:
            return target.read_text(encoding="utf-8", errors="replace"), None
        except Exception as e:
            return None, CommandResult(output=f"Read error: {e}", success=False)

    if ctx.last_output:
        return ctx.last_output, None

    return None, CommandResult(output=f"Usage: {usage}", success=False)


def safe_eval(expr: str):
    import operator as op

    allowed = {
        ast.Add: op.add,
        ast.Sub: op.sub,
        ast.Mult: op.mul,
        ast.Div: op.truediv,
        ast.FloorDiv: op.floordiv,
        ast.Mod: op.mod,
        ast.Pow: op.pow,
        ast.UAdd: op.pos,
        ast.USub: op.neg,
    }

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in allowed:
            return allowed[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in allowed:
            return allowed[type(node.op)](_eval(node.operand))
        raise ValueError("Only simple math expressions are allowed.")

    tree = ast.parse(expr, mode="eval")
    return _eval(tree)


class ThemeCommand(BaseCommand):
    name = "theme"
    aliases = ["themes"]
    description = "List, show, or switch UI themes."
    usage = "theme [list|current|<name>]"

    def execute(self, ctx, args):
        if not args or args[0].lower() == "list":
            lines = ["Available themes:"]
            for theme in list_themes():
                marker = "*" if theme.key == ctx.current_theme else " "
                alias_text = ", ".join(theme.aliases[:4])
                lines.append(f"{marker} {theme.display_name} ({theme.key}) - aliases: {alias_text}")
            lines.append("Use: theme <name>")
            return CommandResult(output="\n".join(lines))

        if args[0].lower() in ("current", "show"):
            theme = get_theme(ctx.current_theme)
            return CommandResult(output=f"Current theme: {theme.display_name} ({theme.key})")

        requested = " ".join(args)
        try:
            theme = get_theme(requested)
        except KeyError:
            names = ", ".join(theme.key for theme in list_themes())
            return CommandResult(
                output=f"Unknown theme: {requested}\nAvailable: {names}",
                success=False,
            )

        ctx.current_theme = theme.key
        return CommandResult(
            output=f"Theme changed to: {theme.display_name}",
            actions={"theme": theme.key},
        )


class HelpCommand(BaseCommand):
    name = "help"
    aliases = ["?"]
    description = "Show all commands."
    usage = "help"

    def execute(self, ctx, args):
        reg = ctx.registry
        lines = ["Available commands:"]
        for cmd in reg.list_commands():
            alias_text = f" | aliases: {', '.join(cmd.aliases)}" if cmd.aliases else ""
            usage_text = f" | usage: {cmd.usage}" if cmd.usage else ""
            meta = reg.metadata_for(cmd.name) if hasattr(reg, "metadata_for") else None
            source_text = f" | plugin: {meta.plugin}" if meta and meta.plugin else ""
            lines.append(f"- {cmd.name}{alias_text}{usage_text}{source_text} :: {cmd.description}")
        return CommandResult(output="\n".join(lines))


class PluginsCommand(BaseCommand):
    name = "plugins"
    aliases = ["pluginlist"]
    description = "Show plugin load status."
    usage = "plugins"

    def execute(self, ctx, args):
        report = getattr(ctx, "plugins", None)
        if report is None:
            return CommandResult(output="Plugin system is not attached.", success=False)

        lines = ["Plugins:"]
        if report.loaded:
            lines.append("Loaded:")
            for item in report.loaded:
                lines.append(f"- {item.name} v{item.version} :: {item.description}")
        else:
            lines.append("Loaded: none")

        if report.failed:
            lines.append("Failed:")
            for item in report.failed:
                lines.append(f"- {item.name} :: {item.error}")

        return CommandResult(output="\n".join(lines))


class ExitCommand(BaseCommand):
    name = "exit"
    aliases = ["quit"]
    description = "Exit the shell."
    usage = "exit"

    def execute(self, ctx, args):
        return CommandResult(output="Bye.", exit_shell=True)


class ClearCommand(BaseCommand):
    name = "clear"
    aliases = ["cls"]
    description = "Clear screen."
    usage = "clear"

    def execute(self, ctx, args):
        os.system("cls")
        return CommandResult()


class WhereCommand(BaseCommand):
    name = "where"
    aliases = ["pwd"]
    description = "Show current location."
    usage = "where"

    def execute(self, ctx, args):
        return CommandResult(output=str(ctx.cwd))


class FilesCommand(BaseCommand):
    name = "files"
    aliases = ["dir", "ls"]
    description = "Show files and folders in current folder."
    usage = "files [path]"

    def execute(self, ctx, args):
        path = resolve_path(ctx, args[0]) if args else ctx.cwd
        return CommandResult(output=list_entries(path, folders_only=False))


class FoldersCommand(BaseCommand):
    name = "folders"
    aliases = ["dird", "dirfolders"]
    description = "Show only folders in current folder."
    usage = "folders [path]"

    def execute(self, ctx, args):
        path = resolve_path(ctx, args[0]) if args else ctx.cwd
        return CommandResult(output=list_entries(path, folders_only=True))


class CdCommand(BaseCommand):
    name = "cd"
    aliases = ["goto", "chdir"]
    description = "Change current directory."
    usage = "cd <path>"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(output=str(ctx.cwd))

        target = resolve_path(ctx, args[0])
        if not target.exists():
            return CommandResult(output=f"Not found: {target}", success=False)
        if not target.is_dir():
            return CommandResult(output=f"Not a folder: {target}", success=False)

        ctx.set_cwd(target)
        return CommandResult(output=str(ctx.cwd))


class GotoCommand(BaseCommand):
    name = "goto"
    aliases = []
    description = "Change current folder."
    usage = "goto <path>"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(output=str(ctx.cwd))

        target = resolve_path(ctx, args[0])
        if not target.exists():
            return CommandResult(output=f"Not found: {target}", success=False)
        if not target.is_dir():
            return CommandResult(output=f"Not a folder: {target}", success=False)

        ctx.set_cwd(target)
        return CommandResult(output=str(ctx.cwd))


class UpCommand(BaseCommand):
    name = "up"
    aliases = ["back"]
    description = "Go to parent directory."
    usage = "up"

    def execute(self, ctx, args):
        parent = ctx.cwd.parent.resolve()
        ctx.set_cwd(parent)
        return CommandResult(output=str(ctx.cwd))


class HomeCommand(BaseCommand):
    name = "home"
    aliases = []
    description = "Go to user home directory."
    usage = "home"

    def execute(self, ctx, args):
        home = Path.home().resolve()
        ctx.set_cwd(home)
        return CommandResult(output=str(ctx.cwd))


class MakeFolderCommand(BaseCommand):
    name = "makefolder"
    aliases = ["mkdir"]
    description = "Create a folder."
    usage = "makefolder <name>"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(output="Usage: makefolder <name>", success=False)

        target = resolve_path(ctx, args[0])
        target.mkdir(parents=True, exist_ok=True)
        return CommandResult(output=f"Created folder: {target}")


class MakeFileCommand(BaseCommand):
    name = "makefile"
    aliases = ["touch"]
    description = "Create an empty file."
    usage = "makefile <file>"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(output="Usage: makefile <file>", success=False)

        target = resolve_path(ctx, args[0])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch(exist_ok=True)
        return CommandResult(output=f"Created file: {target}")


class ReadCommand(BaseCommand):
    name = "read"
    aliases = ["type", "cat"]
    description = "Read file contents."
    usage = "read <file>"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(output="Usage: read <file>", success=False)

        target = resolve_path(ctx, args[0])
        if not target.exists():
            return CommandResult(output=f"Not found: {target}", success=False)
        if not target.is_file():
            return CommandResult(output=f"Not a file: {target}", success=False)

        try:
            return CommandResult(output=target.read_text(encoding="utf-8", errors="replace"))
        except Exception as e:
            return CommandResult(output=f"Read error: {e}", success=False)


WEB_SHORTCUTS = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "github": "https://github.com",
    "chatgpt": "https://chatgpt.com",
    "netflix": "https://www.netflix.com",
    "spotify": "https://open.spotify.com",
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "whatsapp": "https://web.whatsapp.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "reddit": "https://www.reddit.com",
    "gmail": "https://mail.google.com",
    "mail": "https://mail.google.com",
    "email": "https://mail.google.com",
}

WINDOWS_SYSTEM_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "explorer": "explorer.exe",
    "files": "explorer.exe",
    "file explorer": "explorer.exe",
    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",
    "settings": "ms-settings:",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "terminal": "powershell.exe",
    "powershell": "powershell.exe",
    "task manager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
}


def find_registered_app_path(name: str) -> str | None:
    if os.name != "nt":
        return None
    try:
        import winreg
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for candidate in (name, f"{name}.exe"):
                try:
                    k = winreg.OpenKey(root, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{candidate}")
                    val, _ = winreg.QueryValueEx(k, "")
                    if val:
                        cleaned = str(val).strip("\"'")
                        if Path(cleaned).exists():
                            return cleaned
                except OSError:
                    pass
    except Exception:
        pass
    return None


class OpenCommand(BaseCommand):
    name = "open"
    aliases = ["start", "launch"]
    description = "Open a file, folder, application, URL, or website."
    usage = "open <path|url|app_name>"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(output="Usage: open <path|url|app_name>", success=False)

        raw_query = " ".join(args).strip().strip("\"'")
        first_arg = args[0].strip().strip("\"'")

        # 1. Local path check (preserves exact existing behavior)
        target = resolve_path(ctx, raw_query)
        if target.exists():
            try:
                os.startfile(str(target))
                return CommandResult(output=f"Opened: {target}")
            except Exception as e:
                return CommandResult(output=f"Error opening {target}: {e}", success=False)

        if len(args) > 1:
            first_target = resolve_path(ctx, first_arg)
            if first_target.exists():
                try:
                    os.startfile(str(first_target))
                    return CommandResult(output=f"Opened: {first_target}")
                except Exception as e:
                    return CommandResult(output=f"Error opening {first_target}: {e}", success=False)

        normalized = raw_query.lower()

        # 2. Known web shortcut
        if normalized in WEB_SHORTCUTS:
            url = WEB_SHORTCUTS[normalized]
            webbrowser.open(url)
            return CommandResult(output=f"Opened {raw_query.title()} ({url})")

        # 3. Direct URL or domain check
        if re.match(r"^https?://", normalized) or re.match(r"^[a-z0-9-]+(?:\.[a-z0-9-]+)+(?::\d+)?(?:/[^\s]*)?$", normalized):
            url = raw_query if raw_query.startswith(("http://", "https://")) else f"https://{raw_query}"
            webbrowser.open(url)
            return CommandResult(output=f"Opened URL: {url}")

        # 4. Known Windows system utilities
        if normalized in WINDOWS_SYSTEM_APPS:
            app_target = WINDOWS_SYSTEM_APPS[normalized]
            if app_target.startswith("ms-"):
                webbrowser.open(app_target)
            else:
                options = {}
                if os.name == "nt" and app_target in {"cmd.exe", "powershell.exe"}:
                    options["creationflags"] = subprocess.CREATE_NEW_CONSOLE
                try:
                    os.startfile(app_target)
                except Exception:
                    subprocess.Popen([app_target], **options)
            return CommandResult(output=f"Opened {raw_query.title()}.")

        # 5. Check Windows App Paths (Registry - Chrome, Edge, VS Code, Discord, etc.)
        if reg_app := find_registered_app_path(normalized):
            try:
                os.startfile(reg_app)
                return CommandResult(output=f"Opened application: {Path(reg_app).stem}")
            except Exception:
                subprocess.Popen([reg_app])
                return CommandResult(output=f"Opened application: {Path(reg_app).stem}")

        # 6. Check system PATH executables
        if path_exec := (shutil.which(raw_query) or shutil.which(f"{raw_query}.exe")):
            try:
                os.startfile(path_exec)
                return CommandResult(output=f"Opened program: {Path(path_exec).stem}")
            except Exception:
                subprocess.Popen([path_exec])
                return CommandResult(output=f"Opened program: {Path(path_exec).stem}")

        # 7. Search Windows Start Menu for installed apps
        if os.name == "nt":
            roots = []
            for var in ("APPDATA", "PROGRAMDATA"):
                val = os.environ.get(var)
                if val:
                    roots.append(Path(val) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
            candidates = []
            for root in roots:
                if root.is_dir():
                    candidates.extend(
                        p for p in root.rglob("*.lnk")
                        if p.is_file() and not re.search(r"\b(uninstall|remove|setup|install)\b", p.stem, re.I)
                    )
            exact = [p for p in candidates if p.stem.casefold() == normalized]
            matches = exact or [p for p in candidates if normalized in p.stem.casefold()]
            if matches:
                chosen = matches[0]
                try:
                    os.startfile(str(chosen))
                    return CommandResult(output=f"Opened application: {chosen.stem}")
                except Exception as e:
                    return CommandResult(output=f"Failed to launch {chosen.stem}: {e}", success=False)

        # 8. Fallback: Search common user folders if given a filename (e.g. report.pdf)
        safe_exts = {".pdf", ".txt", ".md", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".docx", ".xlsx", ".pptx", ".csv", ".zip"}
        filename_cand = Path(raw_query)
        if filename_cand.suffix.lower() in safe_exts:
            for folder in (Path.home() / "Desktop", Path.home() / "Documents", Path.home() / "Downloads"):
                cand = folder / raw_query
                if cand.is_file():
                    try:
                        os.startfile(str(cand))
                        return CommandResult(output=f"Opened file: {cand}")
                    except Exception as e:
                        return CommandResult(output=f"Error opening {cand}: {e}", success=False)

        # 9. Generic Windows shell open fallback
        if os.name == "nt":
            try:
                os.startfile(raw_query)
                return CommandResult(output=f"Opened: {raw_query}")
            except Exception:
                pass

        return CommandResult(output=f"Not found: {raw_query}. Specify an existing file/folder, URL, or installed application name.", success=False)


class DuplicateCommand(BaseCommand):
    name = "duplicate"
    aliases = ["copy"]
    description = "Copy file or folder."
    usage = "duplicate <source> <destination>"

    def execute(self, ctx, args):
        if len(args) < 2:
            return CommandResult(output="Usage: duplicate <source> <destination>", success=False)

        src = resolve_path(ctx, args[0])
        dst = resolve_path(ctx, args[1])

        if not src.exists():
            return CommandResult(output=f"Source not found: {src}", success=False)

        copy_item(src, dst)
        return CommandResult(output=f"Copied to: {dst}")


class ShiftCommand(BaseCommand):
    name = "shift"
    aliases = ["move"]
    description = "Move file or folder."
    usage = "shift <source> <destination>"

    def execute(self, ctx, args):
        if len(args) < 2:
            return CommandResult(output="Usage: shift <source> <destination>", success=False)

        src = resolve_path(ctx, args[0])
        dst = resolve_path(ctx, args[1])

        if not src.exists():
            return CommandResult(output=f"Source not found: {src}", success=False)

        move_item(src, dst)
        return CommandResult(output=f"Moved to: {dst}")


class RenameCommand(BaseCommand):
    name = "rename"
    aliases = ["ren"]
    description = "Rename a file or folder."
    usage = "rename <source> <new_name>"

    def execute(self, ctx, args):
        if len(args) < 2:
            return CommandResult(output="Usage: rename <source> <new_name>", success=False)

        src = resolve_path(ctx, args[0])
        if not src.exists():
            return CommandResult(output=f"Source not found: {src}", success=False)

        dst = src.with_name(unquote_path(args[1]))
        src.rename(dst)
        return CommandResult(output=f"Renamed to: {dst}")


class DeleteCommand(BaseCommand):
    name = "delete"
    aliases = ["remove", "del"]
    description = "Delete file or folder safely."
    usage = "delete confirm <path>"

    def execute(self, ctx, args):
        if len(args) < 2 or args[0].lower() != "confirm":
            return CommandResult(
                output="Usage: delete confirm <path>  (confirmation word required)",
                success=False,
            )

        target = resolve_path(ctx, args[1])
        if not target.exists():
            return CommandResult(output=f"Not found: {target}", success=False)

        delete_item(target)
        return CommandResult(output=f"Deleted: {target}")


class SearchCommand(BaseCommand):
    name = "search"
    aliases = []
    description = "Search file/folder names."
    usage = "search <text> [path]"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(output="Usage: search <text> [path]", success=False)

        needle = args[0]
        start = resolve_path(ctx, args[1]) if len(args) > 1 else ctx.cwd
        matches = find_names(start, needle, folders_only=False)
        return CommandResult(output="\n".join(matches) if matches else "No matches found.")


class FindTextCommand(BaseCommand):
    name = "findtext"
    aliases = ["grep"]
    description = "Search text inside files."
    usage = "findtext <text> [path]"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(output="Usage: findtext <text> [path]", success=False)

        needle = args[0]
        start = resolve_path(ctx, args[1]) if len(args) > 1 else ctx.cwd
        matches = find_text(start, needle)
        return CommandResult(output="\n".join(matches) if matches else "No matches found.")


class NetworkCommand(BaseCommand):
    name = "network"
    aliases = []
    description = "Show network info."
    usage = "network"

    def execute(self, ctx, args):
        try:
            out = subprocess.run(["ipconfig"], capture_output=True, text=True, shell=False)
            text = out.stdout.strip() or out.stderr.strip()
            return CommandResult(output=text)
        except Exception as e:
            return CommandResult(output=f"network error: {e}", success=False)


class ProcessesCommand(BaseCommand):
    name = "processes"
    aliases = ["tasklist"]
    description = "Show running processes."
    usage = "processes"

    def execute(self, ctx, args):
        try:
            out = subprocess.run(["tasklist"], capture_output=True, text=True, shell=False)
            text = out.stdout.strip() or out.stderr.strip()
            return CommandResult(output=text)
        except Exception as e:
            return CommandResult(output=f"processes error: {e}", success=False)


class SystemCommand(BaseCommand):
    name = "system"
    aliases = ["sysinfo"]
    description = "Show system info."
    usage = "system"

    def execute(self, ctx, args):
        try:
            out = subprocess.run(["systeminfo"], capture_output=True, text=True, shell=False)
            text = out.stdout.strip() or out.stderr.strip()
            return CommandResult(output=text)
        except Exception as e:
            return CommandResult(output=f"system error: {e}", success=False)


class MeCommand(BaseCommand):
    name = "me"
    aliases = ["whoami"]
    description = "Show current user."
    usage = "me"

    def execute(self, ctx, args):
        try:
            return CommandResult(output=getpass.getuser())
        except Exception:
            return CommandResult(output=os.environ.get("USERNAME", "unknown"))


class PcCommand(BaseCommand):
    name = "pc"
    aliases = ["hostname"]
    description = "Show PC name."
    usage = "pc"

    def execute(self, ctx, args):
        return CommandResult(output=socket.gethostname())


class TodayCommand(BaseCommand):
    name = "today"
    aliases = ["date"]
    description = "Show current date."
    usage = "today"

    def execute(self, ctx, args):
        return CommandResult(output=datetime.now().strftime("%Y-%m-%d"))


class NowCommand(BaseCommand):
    name = "now"
    aliases = ["time"]
    description = "Show current time."
    usage = "now"

    def execute(self, ctx, args):
        return CommandResult(output=datetime.now().strftime("%H:%M:%S"))


class CalcCommand(BaseCommand):
    name = "calc"
    aliases = ["math"]
    description = "Safe calculator."
    usage = "calc <expression>"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(output="Usage: calc <expression>", success=False)

        expr = " ".join(args)
        try:
            return CommandResult(output=str(safe_eval(expr)))
        except Exception as e:
            return CommandResult(output=f"Calc error: {e}", success=False)


class HistoryCommand(BaseCommand):
    name = "history"
    aliases = ["hist"]
    description = "Show command history."
    usage = "history"

    def execute(self, ctx, args):
        if not ctx.history:
            return CommandResult(output="(no history)")
        return CommandResult(output="\n".join(f"{i+1:>3}: {cmd}" for i, cmd in enumerate(ctx.history)))


class EnvCommand(BaseCommand):
    name = "env"
    aliases = []
    description = "Show environment variables."
    usage = "env"

    def execute(self, ctx, args):
        lines = [f"{k}={v}" for k, v in sorted(os.environ.items())]
        return CommandResult(output="\n".join(lines))


class TreeCommand(BaseCommand):
    name = "tree"
    aliases = []
    description = "Show folder tree."
    usage = "tree [path] [depth]"

    def execute(self, ctx, args):
        path = ctx.cwd
        depth = 4

        if args:
            if args[0].isdigit():
                depth = int(args[0])
            else:
                path = resolve_path(ctx, args[0])

        if len(args) > 1 and args[1].isdigit():
            depth = int(args[1])

        return CommandResult(output=tree_view(path, max_depth=depth))


class VersionCommand(BaseCommand):
    name = "version"
    aliases = ["ver"]
    description = "Show shell version."
    usage = "version"

    def execute(self, ctx, args):
        return CommandResult(output=f"RiftShell v{__version__}")


class UpdateCommand(BaseCommand):
    name = "update"
    aliases = ["upgrade"]
    description = "Check for a new RiftShell version and install it."
    usage = "update"

    def execute(self, ctx, args):
        return CommandResult(
            output="Checking for updates...",
            actions={"update": True},
        )


class EchoCommand(BaseCommand):
    name = "echo"
    aliases = []
    description = "Print text."
    usage = "echo <text>"

    def execute(self, ctx, args):
        return CommandResult(output=" ".join(args))


class DrivesCommand(BaseCommand):
    name = "drives"
    aliases = ["volumes"]
    description = "Show available Windows drives."
    usage = "drives"

    def execute(self, ctx, args):
        if os.name != "nt":
            return CommandResult(output="Windows only command.", success=False)

        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        drives = []
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drives.append(f"{letter}:\\")
            bitmask >>= 1

        return CommandResult(output="\n".join(drives) if drives else "(no drives found)")


class DiskCommand(BaseCommand):
    name = "disk"
    aliases = ["space"]
    description = "Show disk usage for a path."
    usage = "disk [path]"

    def execute(self, ctx, args):
        target = resolve_path(ctx, args[0]) if args else ctx.cwd
        usage = shutil.disk_usage(str(target if target.exists() else target.parent))

        gb = 1024 ** 3
        lines = [
            f"Total : {usage.total / gb:.2f} GB",
            f"Used  : {usage.used / gb:.2f} GB",
            f"Free  : {usage.free / gb:.2f} GB",
        ]
        return CommandResult(output="\n".join(lines))


class IpCommand(BaseCommand):
    name = "ip"
    aliases = ["net", "ipconfig"]
    description = "Show IP configuration."
    usage = "ip"

    def execute(self, ctx, args):
        try:
            cmd = ["ipconfig"]
            if args and args[0].lower() == "all":
                cmd.append("/all")

            out = subprocess.run(cmd, capture_output=True, text=True, shell=False)
            return CommandResult(output=(out.stdout.strip() or out.stderr.strip()))
        except Exception as e:
            return CommandResult(output=f"ip error: {e}", success=False)


class NetstatCommand(BaseCommand):
    name = "netstat"
    aliases = ["ports"]
    description = "Show active network connections."
    usage = "netstat"

    def execute(self, ctx, args):
        try:
            cmd = ["netstat"]
            if args:
                cmd.extend(args)

            out = subprocess.run(cmd, capture_output=True, text=True, shell=False)
            return CommandResult(output=(out.stdout.strip() or out.stderr.strip()))
        except Exception as e:
            return CommandResult(output=f"netstat error: {e}", success=False)


class PingCommand(BaseCommand):
    name = "ping"
    aliases = []
    description = "Ping a host."
    usage = "ping <host>"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(output="Usage: ping <host>", success=False)

        host = args[0]
        try:
            out = subprocess.run(
                ["ping", host],
                capture_output=True,
                text=True,
                shell=False
            )
            return CommandResult(output=(out.stdout.strip() or out.stderr.strip()))
        except Exception as e:
            return CommandResult(output=f"ping error: {e}", success=False)


class PathCommand(BaseCommand):
    name = "path"
    aliases = ["envpath"]
    description = "Show PATH environment variable."
    usage = "path"

    def execute(self, ctx, args):
        return CommandResult(output=os.environ.get("PATH", ""))
    

class SleepCommand(BaseCommand):
    name = "sleep"
    aliases = ["pause", "wait"]
    description = "Pause the shell for N seconds."
    usage = "sleep <seconds>"

    def execute(self, ctx, args):
        if not args or not args[0].replace('.', '', 1).isdigit():
            return CommandResult(output="Usage: sleep <seconds>", success=False)
        sec = float(args[0])
        time.sleep(sec)
        return CommandResult(output=f"Slept for {sec} seconds.")


class RandomCommand(BaseCommand):
    name = "random"
    aliases = ["rand", "dice"]
    description = "Generate a random number."
    usage = "random [min] [max]"

    def execute(self, ctx, args):
        min_val, max_val = 1, 100
        if len(args) == 2 and args[0].isdigit() and args[1].isdigit():
            min_val, max_val = int(args[0]), int(args[1])
        elif len(args) == 1 and args[0].isdigit():
            max_val = int(args[0])
            
        res = random.randint(min_val, max_val)
        return CommandResult(output=f"Random number ({min_val}-{max_val}): {res}")


class HashCommand(BaseCommand):
    name = "hash"
    aliases = ["md5", "sha256"]
    description = "Generate hash for text or file."
    usage = "hash <text|file> <target>"

    def execute(self, ctx, args):
        if len(args) < 2:
            return CommandResult(output="Usage: hash <text|file> <target>", success=False)
        
        mode = args[0].lower()
        target = " ".join(args[1:])
        hasher = hashlib.sha256()

        if mode == "file":
            path = resolve_path(ctx, target)
            if not path.exists() or not path.is_file():
                return CommandResult(output=f"File not found: {path}", success=False)
            try:
                with open(path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hasher.update(chunk)
                return CommandResult(output=f"SHA-256 Hash:\n{hasher.hexdigest()}")
            except Exception as e:
                return CommandResult(output=f"Hash error: {e}", success=False)
        elif mode == "text":
            hasher.update(target.encode('utf-8'))
            return CommandResult(output=f"SHA-256 Hash:\n{hasher.hexdigest()}")
        else:
            return CommandResult(output="First argument must be 'text' or 'file'.", success=False)


class Base64Command(BaseCommand):
    name = "base64"
    aliases = ["b64"]
    description = "Encode or decode Base64 strings."
    usage = "base64 <encode|decode> <text>"

    def execute(self, ctx, args):
        if len(args) < 2:
            return CommandResult(output="Usage: base64 <encode|decode> <text>", success=False)
        
        action = args[0].lower()
        text = " ".join(args[1:])
        
        try:
            if action == "encode":
                res = base64.b64encode(text.encode('utf-8')).decode('utf-8')
                return CommandResult(output=res)
            elif action == "decode":
                res = base64.b64decode(text.encode('utf-8')).decode('utf-8')
                return CommandResult(output=res)
            else:
                return CommandResult(output="Action must be 'encode' or 'decode'.", success=False)
        except Exception as e:
            return CommandResult(output=f"Base64 error: {e}", success=False)


class DownloadCommand(BaseCommand):
    name = "download"
    aliases = ["wget", "curl"]
    description = "Download a file from a URL."
    usage = "download <url> [filename]"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(
                output="Usage: download <url> [filename]",
                success=False
            )

        url = args[0]

        filename = (
            args[1]
            if len(args) > 1
            else url.rstrip("/").split("/")[-1] or "downloaded_file"
        )

        dest = resolve_path(ctx, filename)

        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/137.0.0.0 Safari/537.36"
                ),
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/",
                "Connection": "keep-alive",
            }

            req = urllib.request.Request(url, headers=headers)

            with urllib.request.urlopen(req, timeout=20) as response:
                with open(dest, "wb") as out_file:
                    shutil.copyfileobj(response, out_file)

            return CommandResult(
                output=f"Downloaded successfully: {dest}"
            )

        except urllib.error.HTTPError as e:
            return CommandResult(
                output=f"HTTP Error {e.code}: {e.reason}",
                success=False
            )

        except urllib.error.URLError as e:
            return CommandResult(
                output=f"URL Error: {e.reason}",
                success=False
            )

        except Exception as e:
            return CommandResult(
                output=f"Download failed: {str(e)}",
                success=False
            )

class ZipCommand(BaseCommand):
    name = "zip"
    aliases = ["compress"]
    description = "Compress a folder into a zip file."
    usage = "zip <folder_to_compress> <output_zip_name>"

    def execute(self, ctx, args):
        if len(args) < 2:
            return CommandResult(output="Usage: zip <folder_to_compress> <output_zip_name>", success=False)
        
        src = resolve_path(ctx, args[0])
        if not src.is_dir():
            return CommandResult(output=f"Not a folder: {src}", success=False)
            
        out_name = resolve_path(ctx, args[1])
        out_path = out_name if out_name.suffix.lower() == ".zip" else Path(f"{out_name}.zip")
        source_root = src.resolve(strict=False)
        target_path = out_path.resolve(strict=False)
        if target_path == source_root or source_root in target_path.parents:
            return CommandResult(
                output="Zip error: the output archive must be outside the folder being compressed.",
                success=False,
            )
        if not target_path.parent.is_dir():
            return CommandResult(output=f"Output folder not found: {target_path.parent}", success=False)

        # Never write directly to the requested file.  If compression is stopped
        # or a file changes underneath us, the user keeps the last known-good ZIP.
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=".zip", prefix=f".{out_path.stem}-", dir=target_path.parent,
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)

            with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for directory, folders, files in os.walk(source_root):
                    if ctx.cancel_event.is_set():
                        return CommandResult(output="Zip cancelled. No archive was created.", success=False)
                    current = Path(directory)
                    relative_dir = current.relative_to(source_root)
                    if not folders and not files and relative_dir != Path("."):
                        archive.writestr(f"{relative_dir.as_posix()}/", "")
                    for filename in files:
                        if ctx.cancel_event.is_set():
                            return CommandResult(output="Zip cancelled. No archive was created.", success=False)
                        file_path = current / filename
                        archive.write(file_path, file_path.relative_to(source_root).as_posix())

            # Windows Explorer reports a generic "invalid" error for partial or
            # corrupt ZIPs, so prove the archive before publishing it.
            with zipfile.ZipFile(temp_path, "r") as archive:
                corrupt_member = archive.testzip()
            if corrupt_member:
                return CommandResult(output=f"Zip error: integrity check failed for {corrupt_member}", success=False)

            os.replace(temp_path, target_path)
            temp_path = None
            return CommandResult(output=f"Compressed to: {target_path}")
        except Exception as e:
            return CommandResult(output=f"Zip error: {e}", success=False)
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass


class UnzipCommand(BaseCommand):
    name = "unzip"
    aliases = ["extract"]
    description = "Extract a zip file."
    usage = "unzip <zip_file> [destination_folder]"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(output="Usage: unzip <zip_file> [destination_folder]", success=False)
        
        src = resolve_path(ctx, args[0])
        if not src.exists():
            return CommandResult(output=f"File not found: {src}", success=False)
            
        dst = resolve_path(ctx, args[1]) if len(args) > 1 else resolve_path(ctx, src.stem)
        
        try:
            shutil.unpack_archive(str(src), str(dst))
            return CommandResult(output=f"Extracted to: {dst}")
        except Exception as e:
            return CommandResult(output=f"Unzip error: {e}", success=False)


class HeadCommand(BaseCommand):
    name = "head"
    aliases = []
    description = "Read the first N lines of a file."
    usage = "head <file> [lines]"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(output="Usage: head <file> [lines]", success=False)
            
        target = resolve_path(ctx, args[0])
        lines_to_read = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
        
        if not target.is_file():
            return CommandResult(output=f"Not a file: {target}", success=False)
            
        try:
            with open(target, 'r', encoding='utf-8', errors='replace') as f:
                lines = []
                for _ in range(lines_to_read):
                    line = f.readline()
                    if not line:
                        break
                    lines.append(line)
            return CommandResult(output="".join(lines).strip())
        except Exception as e:
            return CommandResult(output=f"Read error: {e}", success=False)


class KillCommand(BaseCommand):
    name = "kill"
    aliases = ["taskkill"]
    description = "Kill a process by PID or Name (Windows)."
    usage = "kill <pid|name>"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(output="Usage: kill <pid|name>", success=False)
            
        target = args[0]
        cmd = ["taskkill", "/F"]
        
        if target.isdigit():
            cmd.extend(["/PID", target])
        else:
            cmd.extend(["/IM", target])
            
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, shell=False)
            return CommandResult(output=(out.stdout.strip() or out.stderr.strip()))
        except Exception as e:
            return CommandResult(output=f"Kill error: {e}", success=False)
        

class TailCommand(BaseCommand):
    name = "tail"
    aliases = []
    description = "Read the last N lines of a file."
    usage = "tail <file> [lines]"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(output="Usage: tail <file> [lines]", success=False)

        target = resolve_path(ctx, args[0])
        lines_to_read = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10

        if not target.is_file():
            return CommandResult(output=f"Not a file: {target}", success=False)

        try:
            with open(target, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            last_lines = lines[-lines_to_read:] if len(lines) > lines_to_read else lines
            return CommandResult(output="".join(last_lines).rstrip())
        except Exception as e:
            return CommandResult(output=f"Read error: {e}", success=False)
        
class WcCommand(BaseCommand):
    name = "wc"
    aliases = []
    description = "Count lines, words and characters in a file."
    usage = "wc <file>"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(output="Usage: wc <file>", success=False)

        target = resolve_path(ctx, args[0])
        if not target.is_file():
            return CommandResult(output=f"Not a file: {target}", success=False)

        try:
            with open(target, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            line_count = len(content.splitlines())
            word_count = len(content.split())
            char_count = len(content)

            output = (
                f"Lines : {line_count}\n"
                f"Words : {word_count}\n"
                f"Chars : {char_count}"
            )
            return CommandResult(output=output)
        except Exception as e:
            return CommandResult(output=f"Error: {e}", success=False)
        

class WhichCommand(BaseCommand):
    name = "which"
    aliases = ["whereis"]
    description = "Find full path of a command/executable."
    usage = "which <command>"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(output="Usage: which <command>", success=False)

        cmd_name = args[0]
        path = shutil.which(cmd_name)

        if path:
            return CommandResult(output=path)
        else:
            return CommandResult(output=f"'{cmd_name}' not found in PATH", success=False)
        
class MemoryCommand(BaseCommand):
    name = "memory"
    aliases = ["ram", "free"]
    description = "Show RAM usage information."
    usage = "memory"

    def execute(self, ctx, args):
        if os.name != "nt":
            return CommandResult(output="This command is for Windows only.", success=False)

        try:
            cmd = ["wmic", "OS", "get", "TotalVisibleMemorySize,FreePhysicalMemory", "/format:list"]
            out = subprocess.run(cmd, capture_output=True, text=True, shell=False)

            total_kb = 0
            free_kb = 0

            for line in out.stdout.splitlines():
                line = line.strip()
                if line.startswith("TotalVisibleMemorySize="):
                    total_kb = int(line.split("=")[1])
                elif line.startswith("FreePhysicalMemory="):
                    free_kb = int(line.split("=")[1])

            if total_kb == 0:
                return CommandResult(output="Could not read memory information.", success=False)

            used_kb = total_kb - free_kb
            total_gb = total_kb / (1024 * 1024)
            used_gb = used_kb / (1024 * 1024)
            free_gb = free_kb / (1024 * 1024)
            used_percent = (used_kb / total_kb) * 100

            lines = [
                f"Total RAM   : {total_gb:.2f} GB",
                f"Used        : {used_gb:.2f} GB ({used_percent:.1f}%)",
                f"Free        : {free_gb:.2f} GB",
            ]
            return CommandResult(output="\n".join(lines))

        except Exception as e:
            return CommandResult(output=f"Memory error: {e}", success=False)

class UptimeCommand(BaseCommand):
    name = "uptime"
    aliases = []
    description = "Show system uptime."
    usage = "uptime"

    def execute(self, ctx, args):
        if os.name != "nt":
            return CommandResult(output="This command is for Windows only.", success=False)

        try:
            kernel32 = ctypes.windll.kernel32
            uptime_ms = kernel32.GetTickCount64()

            total_seconds = uptime_ms // 1000
            days = total_seconds // (24 * 3600)
            hours = (total_seconds % (24 * 3600)) // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60

            parts = []
            if days > 0:
                parts.append(f"{days} day{'s' if days > 1 else ''}")
            if hours > 0:
                parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
            if minutes > 0:
                parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
            if seconds > 0 or not parts:
                parts.append(f"{seconds} second{'s' if seconds > 1 else ''}")

            return CommandResult(output="System Uptime: " + ", ".join(parts))

        except Exception as e:
            return CommandResult(output=f"Uptime error: {e}", success=False)


class RunCommand(BaseCommand):
    name = "run"
    aliases = ["exec", "native"]
    description = "Run a native system command from the current folder."
    usage = "run <program> [args...]"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(output="Usage: run <program> [args...]", success=False)

        cleaned_args = [arg.strip("\"'") for arg in args]
        env = os.environ.copy()
        env.update(ctx.variables)

        try:
            out = self._run_process(cleaned_args, ctx, env)
        except FileNotFoundError:
            if os.name != "nt":
                return CommandResult(output=f"Command not found: {cleaned_args[0]}", success=False)
            try:
                out = self._run_process(["cmd", "/c", " ".join(cleaned_args)], ctx, env)
            except subprocess.TimeoutExpired:
                return CommandResult(output="Command timed out after 60 seconds.", success=False)
            except Exception as e:
                return CommandResult(output=f"Run error: {e}", success=False)
        except subprocess.TimeoutExpired:
            return CommandResult(output="Command timed out after 60 seconds.", success=False)
        except Exception as e:
            return CommandResult(output=f"Run error: {e}", success=False)

        text = "\n".join(part for part in [out.stdout.strip(), out.stderr.strip()] if part)
        if ctx.cancel_event.is_set():
            return CommandResult(output=text or "Native command cancelled.", success=False)
        return CommandResult(output=text, success=out.returncode == 0)

    @staticmethod
    def _run_process(args, ctx, env):
        process = subprocess.Popen(
            args,
            cwd=str(ctx.cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
        )
        deadline = time.monotonic() + 60
        while process.poll() is None:
            if ctx.cancel_event.is_set():
                process.terminate()
                break
            if time.monotonic() >= deadline:
                process.kill()
                raise subprocess.TimeoutExpired(args, timeout=60)
            time.sleep(0.05)
        stdout, stderr = process.communicate()
        return type("ProcessResult", (), {"stdout": stdout, "stderr": stderr, "returncode": process.returncode})()


class SetVarCommand(BaseCommand):
    name = "setvar"
    aliases = ["let"]
    description = "Create or update a shell variable."
    usage = "setvar <name> <value>"

    def execute(self, ctx, args):
        if len(args) < 2:
            return CommandResult(output="Usage: setvar <name> <value>", success=False)

        name = args[0]
        if not name.replace("_", "").isalnum() or name[0].isdigit():
            return CommandResult(output="Variable name must use letters, numbers, or underscore.", success=False)

        value = " ".join(args[1:])
        ctx.variables[name] = value
        return CommandResult(output=f"{name}={value}")


class UnsetVarCommand(BaseCommand):
    name = "unsetvar"
    aliases = ["unset"]
    description = "Remove a shell variable."
    usage = "unsetvar <name>"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(output="Usage: unsetvar <name>", success=False)

        removed = ctx.variables.pop(args[0], None)
        if removed is None:
            return CommandResult(output=f"Variable not found: {args[0]}", success=False)
        return CommandResult(output=f"Removed variable: {args[0]}")


class VarsCommand(BaseCommand):
    name = "vars"
    aliases = []
    description = "Show shell variables."
    usage = "vars"

    def execute(self, ctx, args):
        if not ctx.variables:
            return CommandResult(output="(no shell variables)")
        return CommandResult(output="\n".join(f"{k}={v}" for k, v in sorted(ctx.variables.items())))


class AliasCommand(BaseCommand):
    name = "alias"
    aliases = []
    description = "Create or list command aliases."
    usage = "alias [name command...]"

    def execute(self, ctx, args):
        if not args:
            if not ctx.aliases:
                return CommandResult(output="(no aliases)")
            return CommandResult(output="\n".join(f"{k}={v}" for k, v in sorted(ctx.aliases.items())))

        if "=" in args[0]:
            name, value = args[0].split("=", 1)
            if len(args) > 1:
                value = " ".join([value] + args[1:])
        else:
            if len(args) < 2:
                return CommandResult(output="Usage: alias <name> <command...>", success=False)
            name = args[0]
            value = " ".join(args[1:])

        name = name.lower().strip()
        value = value.strip()
        if not name or not value:
            return CommandResult(output="Usage: alias <name> <command...>", success=False)
        if ctx.registry and ctx.registry.get(name):
            return CommandResult(output=f"Cannot override built-in command: {name}", success=False)

        ctx.aliases[name] = value
        return CommandResult(output=f"Alias added: {name} -> {value}")


class UnaliasCommand(BaseCommand):
    name = "unalias"
    aliases = []
    description = "Remove a command alias."
    usage = "unalias <name>"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(output="Usage: unalias <name>", success=False)

        removed = ctx.aliases.pop(args[0].lower(), None)
        if removed is None:
            return CommandResult(output=f"Alias not found: {args[0]}", success=False)
        return CommandResult(output=f"Removed alias: {args[0]}")


class FilterCommand(BaseCommand):
    name = "filter"
    aliases = ["contains"]
    description = "Filter piped text or a file by matching lines."
    usage = "filter <text> [file]"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(output="Usage: filter <text> [file]", success=False)

        case_sensitive = args[0] == "-case"
        if case_sensitive:
            if len(args) < 2:
                return CommandResult(output="Usage: filter [-case] <text> [file]", success=False)
            needle = args[1]
            source_args = args[2:]
        else:
            needle = args[0]
            source_args = args[1:]

        source, error = text_source(ctx, source_args, self.usage)
        if error:
            return error

        matches = []
        for line in source.splitlines():
            haystack = line if case_sensitive else line.lower()
            target = needle if case_sensitive else needle.lower()
            if target in haystack:
                matches.append(line)
        return CommandResult(output="\n".join(matches) if matches else "No matches found.")


class SortCommand(BaseCommand):
    name = "sort"
    aliases = []
    description = "Sort piped text or file lines."
    usage = "sort [file]"

    def execute(self, ctx, args):
        source, error = text_source(ctx, args, self.usage)
        if error:
            return error

        lines = sorted(source.splitlines(), key=str.lower)
        return CommandResult(output="\n".join(lines))


class UniqueCommand(BaseCommand):
    name = "unique"
    aliases = ["uniq"]
    description = "Remove duplicate lines from piped text or a file."
    usage = "unique [file]"

    def execute(self, ctx, args):
        source, error = text_source(ctx, args, self.usage)
        if error:
            return error

        seen = set()
        lines = []
        for line in source.splitlines():
            key = line.lower()
            if key in seen:
                continue
            seen.add(key)
            lines.append(line)
        return CommandResult(output="\n".join(lines))


class TakeCommand(BaseCommand):
    name = "take"
    aliases = ["first"]
    description = "Show the first N lines from piped text or a file."
    usage = "take <lines> [file]"

    def execute(self, ctx, args):
        if not args or not args[0].isdigit():
            return CommandResult(output="Usage: take <lines> [file]", success=False)

        source, error = text_source(ctx, args[1:], self.usage)
        if error:
            return error

        return CommandResult(output="\n".join(source.splitlines()[:int(args[0])]))


class SkipCommand(BaseCommand):
    name = "skip"
    aliases = []
    description = "Skip the first N lines from piped text or a file."
    usage = "skip <lines> [file]"

    def execute(self, ctx, args):
        if not args or not args[0].isdigit():
            return CommandResult(output="Usage: skip <lines> [file]", success=False)

        source, error = text_source(ctx, args[1:], self.usage)
        if error:
            return error

        return CommandResult(output="\n".join(source.splitlines()[int(args[0]):]))


class CountCommand(BaseCommand):
    name = "count"
    aliases = []
    description = "Count lines, words, and characters in piped text or a file."
    usage = "count [file]"

    def execute(self, ctx, args):
        source, error = text_source(ctx, args, self.usage)
        if error:
            return error

        return CommandResult(
            output=(
                f"Lines : {len(source.splitlines())}\n"
                f"Words : {len(source.split())}\n"
                f"Chars : {len(source)}"
            )
        )


class SaveCommand(BaseCommand):
    name = "save"
    aliases = []
    description = "Save piped text or last command output to a file."
    usage = "save <file>"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(output="Usage: save <file>", success=False)

        text = ctx.piped_input or ctx.last_output
        if not text:
            return CommandResult(output="Nothing to save.", success=False)

        target = resolve_path(ctx, args[0])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", errors="replace")
        return CommandResult(output=f"Saved to: {target}")


class LastCommand(BaseCommand):
    name = "last"
    aliases = ["lastout"]
    description = "Show the previous command output."
    usage = "last"

    def execute(self, ctx, args):
        return CommandResult(output=ctx.last_output or "(no previous output)")


class BrowserCommand(BaseCommand):
    name = "browser"
    aliases = ["browse"]
    description = "Control an automated browser via Playwright (open, search, control tabs, media)."
    usage = "browser <open|search|control|tab|play|pause|click|fill|tabs|close> [args]"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(
                output="Usage: browser <open|search|control|tab|play|pause|click|fill|tabs|close> [args]",
                success=False,
            )

        sub = args[0].lower().strip()
        from utils.browser import get_browser_controller, BrowserError

        try:
            ctrl = get_browser_controller()
        except Exception as e:
            return CommandResult(output=f"Browser error: {e}", success=False)

        try:
            if sub == "open":
                if len(args) < 2:
                    return CommandResult(output="Usage: browser open <url>", success=False)
                url = " ".join(args[1:]).strip()
                res = ctrl.open_url(url)
                return CommandResult(output=res)

            elif sub == "search":
                if len(args) < 2:
                    return CommandResult(
                        output="Usage: browser search <query> [--engine google|youtube|bing|duckduckgo]",
                        success=False,
                    )
                remaining = list(args[1:])
                engine = "Google"
                if "--engine" in remaining:
                    idx = remaining.index("--engine")
                    if idx + 1 < len(remaining):
                        engine = remaining[idx + 1]
                        remaining = remaining[:idx] + remaining[idx + 2:]
                    else:
                        remaining = remaining[:idx]
                query = " ".join(remaining).strip()
                res = ctrl.search(query, engine=engine)
                return CommandResult(output=res)

            elif sub == "control":
                if len(args) < 2:
                    return CommandResult(
                        output="Usage: browser control <back|forward|refresh|new_tab|close_tab|tabs|scroll_up|scroll_down|top|bottom|play|pause>",
                        success=False,
                    )
                action = args[1].lower().strip()
                res = ctrl.control(action)
                return CommandResult(output=res)

            elif sub in {"tabs", "tablist"}:
                res = ctrl.control("tabs")
                return CommandResult(output=res)

            elif sub == "tab":
                if len(args) < 2:
                    return CommandResult(output="Usage: browser tab <number>", success=False)
                try:
                    num = int(args[1])
                except ValueError:
                    return CommandResult(output="Tab index must be an integer.", success=False)
                res = ctrl.switch_tab(num)
                return CommandResult(output=res)

            elif sub == "play":
                if len(args) > 1 and args[1].isdigit():
                    res = ctrl.play_result(int(args[1]))
                else:
                    res = ctrl.control("play")
                return CommandResult(output=res)

            elif sub == "pause":
                res = ctrl.control("pause")
                return CommandResult(output=res)

            elif sub in {"back", "forward", "refresh", "scroll_up", "scroll_down", "top", "bottom", "new_tab", "close_tab"}:
                res = ctrl.control(sub)
                return CommandResult(output=res)

            elif sub == "click":
                if len(args) < 2:
                    return CommandResult(output="Usage: browser click <button/link text>", success=False)
                target = " ".join(args[1:]).strip()
                res = ctrl.click_matching(target)
                return CommandResult(output=res)

            elif sub == "fill":
                if len(args) < 3:
                    return CommandResult(output="Usage: browser fill <ref> <text>", success=False)
                ref = args[1]
                val = " ".join(args[2:])
                res = ctrl.fill_element(ref, val)
                return CommandResult(output=res)

            elif sub in {"context", "snapshot"}:
                res = ctrl.page_context()
                return CommandResult(output=res)

            elif sub in {"close", "quit", "exit"}:
                ctrl.close()
                return CommandResult(output="Controlled browser closed.")

            else:
                return CommandResult(
                    output=f"Unknown browser subcommand '{sub}'.\nUsage: browser <open|search|control|tab|play|pause|click|fill|tabs|close>",
                    success=False,
                )

        except BrowserError as exc:
            return CommandResult(output=f"Browser: {exc}", success=False)
        except Exception as exc:
            return CommandResult(output=f"Browser error: {exc}", success=False)


class NoteCommand(BaseCommand):
    name = "note"
    aliases = ["notes"]
    description = "Quickly create a timestamped note and open it in Notepad."
    usage = "note <text to record>"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(output="Usage: note <text to record>", success=False)

        text = " ".join(args).strip()
        if not text:
            return CommandResult(output="Please provide note content.", success=False)

        notes_dir = Path.home() / "Documents" / "RiftShell Notes"
        try:
            try:
                notes_dir.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError):
                notes_dir = ctx.cwd / ".riftshell_notes"
                notes_dir.mkdir(parents=True, exist_ok=True)

            now = datetime.now()
            note_file = notes_dir / f"note-{now:%Y%m%d-%H%M%S}.txt"
            content = f"--- RiftShell Note ---\nDate: {now:%Y-%m-%d %H:%M:%S}\n\n{text}\n"
            note_file.write_text(content, encoding="utf-8-sig")

            subprocess.Popen(["notepad.exe", str(note_file)])
            return CommandResult(output=f"Note saved and opened in Notepad: {note_file}")
        except Exception as exc:
            return CommandResult(output=f"Could not create note: {exc}", success=False)

    
