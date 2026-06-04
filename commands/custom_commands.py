from __future__ import annotations

import ast
import getpass
import os
import platform
import socket
import subprocess
from datetime import datetime
from pathlib import Path

from core.base import BaseCommand, CommandResult
from utils.safe_fs import (
    resolve_path,
    list_entries,
    tree_view,
    find_names,
    find_text,
    copy_item,
    move_item,
    delete_item,
)


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
            lines.append(f"- {cmd.name}{alias_text}{usage_text} :: {cmd.description}")
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
    aliases = []
    description = "Show current location."
    usage = "where"

    def execute(self, ctx, args):
        return CommandResult(output=str(ctx.cwd))


class FilesCommand(BaseCommand):
    name = "files"
    aliases = []
    description = "Show files and folders in current folder."
    usage = "files [path]"

    def execute(self, ctx, args):
        path = resolve_path(ctx, args[0]) if args else ctx.cwd
        return CommandResult(output=list_entries(path, folders_only=False))


class FoldersCommand(BaseCommand):
    name = "folders"
    aliases = []
    description = "Show only folders in current folder."
    usage = "folders [path]"

    def execute(self, ctx, args):
        path = resolve_path(ctx, args[0]) if args else ctx.cwd
        return CommandResult(output=list_entries(path, folders_only=True))


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
    aliases = ["type"]
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


class OpenCommand(BaseCommand):
    name = "open"
    aliases = ["start"]
    description = "Open a file or folder."
    usage = "open <path>"

    def execute(self, ctx, args):
        if not args:
            return CommandResult(output="Usage: open <path>", success=False)

        target = resolve_path(ctx, args[0])
        if not target.exists():
            return CommandResult(output=f"Not found: {target}", success=False)

        os.startfile(str(target))
        return CommandResult(output=f"Opened: {target}")


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

        dst = src.with_name(args[1])
        src.rename(dst)
        return CommandResult(output=f"Renamed to: {dst}")


class DeleteCommand(BaseCommand):
    name = "delete"
    aliases = ["remove"]
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
    aliases = []
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
    aliases = []
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
        return CommandResult(output="SanuShell v1.0")


class EchoCommand(BaseCommand):
    name = "echo"
    aliases = []
    description = "Print text."
    usage = "echo <text>"

    def execute(self, ctx, args):
        return CommandResult(output=" ".join(args))