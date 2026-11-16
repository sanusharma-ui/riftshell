"""Registry-backed tools shared by desktop Orbit and Telegram."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai.risk import classify_risk


@dataclass(frozen=True)
class OrbitTool:
    name: str
    description: str
    risk_tier: int


class OrbitBridge:
    """Expose existing RiftShell executors without duplicating commands."""

    def __init__(self, shell):
        self.shell = shell

    def command_catalog(self) -> list[str]:
        catalog = []
        for meta in self.shell.registry.list_metadata():
            tier = classify_risk("shell", meta.usage).tier
            aliases = f" aliases={','.join(meta.aliases)}" if meta.aliases else ""
            catalog.append(
                f"{meta.name} | usage={meta.usage} | risk=tier{tier} | "
                f"{meta.description}{aliases}"
            )
        return catalog

    def run_command(self, name: str, args: list[str] | tuple[str, ...] = ()):
        command = " ".join([str(name).strip(), *(str(arg) for arg in args)]).strip()
        if not command:
            raise ValueError("A command name is required.")
        return self.shell.execute_line(command)

    def browser(self, operation: str, **kwargs):
        import time
        from utils.browser import get_browser_controller

        controller = get_browser_controller()
        method = {
            "goto": "open_url",
            "click": "click_matching",
            "type": "fill_element",
            "press": "press_key",
            "scroll": "scroll_by_pixels",
            "snapshot": "page_context",
            "read_page_text": "get_current_dom",
            "back": "control",
            "tabs": "control",
            "close": "close",
        }.get(operation)
        if method is None:
            raise ValueError(f"Unknown browser operation: {operation}")
        if operation in {"back", "tabs"}:
            result = getattr(controller, method)(operation)
            time.sleep(0.3)
            return f"{result}\nFRESH SNAPSHOT:\n{controller.page_context()}"
        if operation == "type":
            result = getattr(controller, method)(kwargs["ref"], kwargs["text"])
            time.sleep(0.3)
            return f"{result}\nFRESH SNAPSHOT:\n{controller.page_context()}"
        if operation == "scroll":
            result = getattr(controller, method)(int(kwargs.get("pixels", 0)))
            time.sleep(0.3)
            return f"{result}\nFRESH SNAPSHOT:\n{controller.page_context()}"
        if operation in {"snapshot", "read_page_text"}:
            return getattr(controller, method)()
        if operation == "close":
            return getattr(controller, method)()
        target = kwargs.get("ref") or kwargs.get("target") or kwargs.get("value") or kwargs.get("url") or kwargs.get("key") or ""
        result = getattr(controller, method)(target)
        time.sleep(0.3)
        return f"{result}\nFRESH SNAPSHOT:\n{controller.page_context()}"

    def pc(self, operation: str, **kwargs):
        from utils.pc_control import execute_pc_command

        op = str(operation).lower().strip()
        sub = str(kwargs.get("subcommand") or kwargs.get("action") or "").strip()
        extra_args = []
        if kwargs.get("args"):
            if isinstance(kwargs["args"], (list, tuple)):
                extra_args.extend(str(a) for a in kwargs["args"])
            else:
                extra_args.extend(str(kwargs["args"]).split())
        for key in ("title", "text", "key", "target", "path"):
            if kwargs.get(key) is not None and not extra_args:
                extra_args.append(str(kwargs[key]))
        for key in ("x", "y", "amount", "count", "pixels"):
            if kwargs.get(key) is not None:
                extra_args.append(str(kwargs[key]))
        if kwargs.get("keys"):
            if isinstance(kwargs["keys"], (list, tuple)):
                extra_args.extend(str(k) for k in kwargs["keys"])
            else:
                extra_args.extend(str(kwargs["keys"]).split())

        if op in {"windows", "mouse", "keyboard", "screen"}:
            cmd = op
            default_sub = ("list" if op == "windows" else "position" if op == "mouse" else "press" if op == "keyboard" else "size")
            subcmd = sub or default_sub
            sub_tokens = subcmd.split()
            all_args = (*sub_tokens, *extra_args)
            return execute_pc_command(cmd, *all_args)
        else:
            raw_args = tuple(extra_args) if extra_args else (tuple(str(sub).split()) if sub else ())
            return execute_pc_command(op, *raw_args)

    def tools(self) -> tuple[OrbitTool, ...]:
        return (
            OrbitTool("run_command", "Run any registered RiftShell command.", 1),
            OrbitTool("browser", "Observe and interact with the controlled browser.", 0),
            OrbitTool("pc", "Observe and control windows, mouse, keyboard, and screen.", 0),
        )
