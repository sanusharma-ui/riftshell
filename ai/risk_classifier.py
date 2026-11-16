"""Centralized risk classification for all execution sources (local Orbit, Telegram, CLI)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal


@dataclass(frozen=True)
class RiskDecision:
    """Risk classification result."""
    tier: Literal[0, 1, 2]  # 0=auto, 1=session grant, 2=confirm every time
    reason: str
    requires_approval: bool  # True for tier 1 (first time) or tier 2 (always)
    session_grantable: bool  # True for tier 1 only


class SessionGrant:
    """Tracks tier-1 approvals valid for a time window."""

    def __init__(self, duration_minutes: int = 30):
        self.duration = timedelta(minutes=duration_minutes)
        self._grants: dict[str, datetime] = {}  # action_key -> expiry

    def grant(self, action_key: str) -> None:
        """Grant approval for this action."""
        self._grants[action_key] = datetime.now() + self.duration

    def is_granted(self, action_key: str) -> bool:
        """Check if action is currently granted."""
        expiry = self._grants.get(action_key)
        if expiry is None:
            return False
        if datetime.now() > expiry:
            del self._grants[action_key]
            return False
        return True

    def revoke_all(self) -> None:
        """Revoke all grants (called by /stop or /panic)."""
        self._grants.clear()


class RiskClassifier:
    """Central risk classification for all actions."""

    # Commands that are always safe (tier 0)
    SAFE_COMMANDS = {
        "help", "?", "plugins", "where", "pwd", "files", "dir", "ls", "folders",
        "dird", "dirfolders", "read", "type", "cat", "tree", "find", "findtext",
        "search", "searchtext", "vars", "alias", "history", "last", "theme", "themes",
        "me", "today", "now", "system", "processes", "drives", "ip", "netstat", "path",
        "memory", "uptime", "version", "hello", "pc windows list", "pc screen size",
        "pc mouse position", "browser tabs", "browser control tabs",
    }

    # Sensitive field / data patterns (tier 2 when filling or typing)
    SENSITIVE_PATTERNS = [
        r"(password|passwd|pwd|pass)",
        r"(otp|2fa|mfa|totp)",
        r"(credit|card|cvv|cvc)",
        r"(token|api[_-]?key|secret|auth)",
        r"(ssn|social.?security)",
        r"(pin|pincode)",
    ]

    # Destructive patterns (tier 2 always)
    DESTRUCTIVE_PATTERNS = [
        r"\b(format|rm\s+-rf|del\s+/s|deltree)\b",
        r"\b(reg(?:edit|\.exe)?\s+delete)\b",
        r"\b(sc(?:\.exe)?\s+delete)\b",
        r"\b(disable|stop).*\b(firewall|defender|uac|security)\b",
        r"\b(shutdown|restart|reboot)\s+/[sfr]",
        r"powershell.*-enc",  # any encoded powershell command
        r"curl.*\|\s*(sh|bash|powershell)",  # pipe to shell
    ]

    # Safe hotkeys (tier 0)
    SAFE_HOTKEYS = {
        "ctrl c", "ctrl v", "ctrl x", "ctrl a", "ctrl z", "ctrl y",
        "ctrl f", "ctrl h", "ctrl n", "ctrl t", "ctrl w", "ctrl tab",
        "alt tab", "win tab", "f5", "f11", "escape", "enter", "tab",
        "backspace", "space", "up", "down", "left", "right",
    }

    def __init__(self, duration_minutes: int = 30):
        self.session_grant = SessionGrant(duration_minutes=duration_minutes)
        global _global_classifier
        _global_classifier = self

    def classify(
        self,
        action: str,
        args: Any = "",
        source: Literal["local", "telegram"] = "local",
        from_untrusted: bool = False,
    ) -> RiskDecision:
        """
        Classify an action's risk level.

        Args:
            action: Action type (shell, browser, tool, etc.)
            args: Arguments/command string
            source: Where the action originates
            from_untrusted: True if triggered by webpage/file content
        """
        action = str(action or "").lower().strip()
        args_str = args if isinstance(args, str) else str(args or "")
        args_lower = args_str.lower().strip()

        # Always tier 2: Destructive patterns
        if any(re.search(pat, args_lower, re.I) for pat in self.DESTRUCTIVE_PATTERNS):
            return self._tier2("Destructive operation requires confirmation")

        # Always tier 2: Security configuration or sensitive credentials modification
        if any(word in args_lower for word in [
            "whitelist", "telegram_token", "allowed_users", "telegram_allowed_user_ids",
            "safety_policy", "api_key", "groq_api_key", "gemini_api_key", "telegram_bot_token"
        ]):
            return self._tier2("Security configuration change requires confirmation")

        if "setvar" in args_lower and any(w in args_lower for w in ["token", "key", "secret", "password"]):
            return self._tier2("Security configuration change requires confirmation")

        if "config" in args_lower and any(w in args_lower for w in ["api_key", "token", "secret", "password"]):
            return self._tier2("Security configuration change requires confirmation")

        # Tier 2 if from untrusted source (prompt injection defense)
        if from_untrusted and action in {"shell", "browser", "tool", "code_write"}:
            return self._tier2("Action triggered from untrusted content requires confirmation")

        # Action-specific classification
        if action == "respond":
            return self._tier0("Conversational response")

        if action == "screenshot":
            return self._tier0("Screenshot capture")

        if action == "code_write":
            if args_lower and ("temp" in args_lower or "tmp" in args_lower):
                return self._tier0("Temporary file write")
            return self._tier1("File modification", action_key="file_ops")

        if action in {"windows", "mouse", "keyboard", "screen", "pc"} or action.startswith("mouse_") or action.startswith("keyboard_") or action.startswith("pc_"):
            return self._classify_pc(args_str, f"{action.replace('_', ' ')} {args_lower}")

        if action.startswith("browser_") or action == "browser":
            sub = action[len("browser_"):] if action.startswith("browser_") else ""
            return self._classify_browser(args_str, f"{sub} {args_lower}".strip())

        if action == "tool":
            return self._classify_tool(args_str, args_lower)

        if action == "shell":
            return self._classify_shell(args_str, args_lower)

        # Unknown action: fail safe to Tier 1
        return self._tier1("Unknown action type", action_key=f"unknown_{action}")

    def _classify_browser(self, args_str: str, args_lower: str) -> RiskDecision:
        """Classify browser actions."""
        # Tier 2: Filling sensitive fields (passwords, tokens, cards, etc.)
        if "fill" in args_lower or "type" in args_lower:
            if any(re.search(pat, args_str, re.I) for pat in self.SENSITIVE_PATTERNS):
                return self._tier2("Browser form fill with sensitive credentials requires approval")

        # Tier 0: Safe browser navigation and inspect operations
        if any(cmd in args_lower for cmd in [
            "open", "search", "goto", "navigate", "back", "forward", "refresh",
            "scroll", "tabs", "dom", "snapshot", "youtube", "new_tab", "newtab"
        ]):
            return self._tier0("Safe browser navigation")

        # Tier 1: Form filling (non-sensitive), clicking, submitting, closing
        if "fill" in args_lower:
            return self._tier1("Form field input", action_key="browser_fill")

        if any(word in args_lower for word in ["click", "submit", "send", "post"]):
            return self._tier1("Browser interaction", action_key="browser_click")

        if "close" in args_lower:
            return self._tier1("Closing browser tab", action_key="browser_close")

        return self._tier0("Safe browser operation")

    def _classify_tool(self, args_str: str, args_lower: str) -> RiskDecision:
        """Classify tool actions."""
        if args_lower.startswith("pc "):
            return self._classify_pc(args_str, args_lower)

        if args_lower.startswith("browser"):
            return self._classify_browser(args_str, args_lower)

        if args_lower.startswith("run_command "):
            cmd = args_str[len("run_command "):].strip()
            return self._classify_shell(cmd, cmd.lower())

        return self._tier1("Tool execution", action_key="tool")

    def _classify_pc(self, args_str: str, args_lower: str) -> RiskDecision:
        """Classify PC control actions."""
        clean = args_lower.strip()

        # Tier 0: Read-only operations / listing windows
        if clean in {"windows", "window", "windows list", "window list"} or any(cmd in args_lower for cmd in [
            "windows list", "window list", "mouse position", "screen size", "screen capture"
        ]):
            return self._tier0("Read-only PC inspection")

        # Tier 0: Safe mouse operations
        if clean == "mouse" or any(op in args_lower for op in [
            "mouse move", "mouse click", "mouse scroll", "mouse_click", "mouse_move",
            "mouse right_click", "mouse double_click", "click center", "click"
        ]):
            return self._tier0("Mouse control")

        # Typing
        if "keyboard type" in args_lower:
            if any(re.search(pat, args_str, re.I) for pat in self.SENSITIVE_PATTERNS):
                return self._tier2("Typing sensitive information")
            return self._tier0("Keyboard input")

        # Pressing keys
        if clean in {"keyboard", "keyboard press"} or "keyboard press" in args_lower or "press " in args_lower:
            key = args_lower.replace("pc keyboard press", "").replace("keyboard press", "").replace("keyboard", "").replace("press", "").strip()
            if not key or key in self.SAFE_HOTKEYS or key.lower() in self.SAFE_HOTKEYS:
                return self._tier0("Safe key press")
            return self._tier1("Keyboard key press", action_key="keyboard_press")

        # Hotkeys
        if "keyboard hotkey" in args_lower or "hotkey " in args_lower:
            keys = args_lower.replace("pc keyboard hotkey", "").replace("keyboard hotkey", "").replace("hotkey", "").strip()
            if keys in self.SAFE_HOTKEYS or keys.lower() in self.SAFE_HOTKEYS:
                return self._tier0("Safe keyboard shortcut")
            return self._tier1("System keyboard shortcut", action_key="keyboard_hotkey")

        # Window close is Tier 2 (or Tier 1; tested as Tier 2)
        if "windows close" in args_lower or "window close" in args_lower:
            return self._tier2("Closing application window")

        # Window focus / minimize / maximize
        if any(cmd in args_lower for cmd in [
            "windows focus", "windows minimize", "windows maximize",
            "window focus", "window minimize", "window maximize"
        ]):
            return self._tier1("Window management", action_key="window_manage")

        return self._tier1("PC control action", action_key="pc_control")

    def _classify_shell(self, args_str: str, args_lower: str) -> RiskDecision:
        """Classify shell commands."""
        if not args_lower:
            return self._tier0("Empty command")

        # Extract first command word
        tokens = args_lower.split()
        cmd = tokens[0] if tokens else ""

        # PC control commands run directly as shell commands
        if cmd in {"pc", "windows", "mouse", "keyboard", "screen"}:
            pc_args = args_lower if cmd == "pc" else f"{cmd} {' '.join(tokens[1:])}".strip()
            return self._classify_pc(args_str, pc_args)

        # Browser command run as shell command
        if cmd == "browser":
            sub = tokens[1] if len(tokens) > 1 else ""
            if sub in {"click", "tap"}:
                if any(w in args_lower for w in ["pay", "purchase", "checkout", "buy now", "transfer"]):
                    return self._tier2("Financial checkout transaction requires confirmation")
                return self._tier0("Clicking browser button/link")
            return self._classify_browser(args_str, " ".join(tokens[1:]))

        # Sensitive typing in shell
        if "keyboard type" in args_lower or (cmd == "keyboard" and len(tokens) > 1 and tokens[1] == "type"):
            if any(re.search(pat, args_str, re.I) for pat in self.SENSITIVE_PATTERNS):
                return self._tier2("Typing sensitive information")

        # Safe read-only commands
        full_cmd = args_lower.split("|")[0].strip()
        if full_cmd in self.SAFE_COMMANDS or cmd in self.SAFE_COMMANDS:
            return self._tier0("Safe read-only command")

        # Temp file creation
        if cmd in {"makefile", "touch", "makefolder", "mkdir"} and ("temp" in args_lower or "tmp" in args_lower):
            return self._tier0("Temporary file creation")

        # Non-destructive file operations: Tier 1
        if cmd in {
            "makefile", "touch", "makefolder", "mkdir", "duplicate", "copy",
            "shift", "move", "rename", "ren", "save"
        }:
            return self._tier1("File operation", action_key="file_ops")

        # App launching & URLs
        if cmd in {"open", "start", "launch"}:
            if any(ext in args_lower for ext in [".exe", ".bat", ".cmd", ".ps1", ".msi"]):
                return self._tier2("Launching executable file")
            # URLs and web destinations (YouTube, Google, websites) are Tier 0
            if any(term in args_lower for term in ["youtube", "google", "http://", "https://", "www.", ".com", ".org", ".net", ".io", ".dev", ".in"]):
                return self._tier0("Opening URL")
            return self._tier1("Opening application", action_key="app_launch")

        # Deletion: Tier 2
        if cmd in {"delete", "remove", "del"}:
            return self._tier2("File deletion")

        # Native command execution
        if cmd in {"run", "exec", "native"}:
            if any(word in args_lower for word in ["format", "reg delete", "sc delete", "del /s"]):
                return self._tier2("Destructive native command")
            return self._tier1("Native command execution", action_key="native_cmd")

        # Git operations
        if cmd.startswith("g") and cmd in {
            "gcommit", "gc", "gpull", "gpl", "gpush", "gps", "gcheckout", "gco", "gbranch", "gb"
        }:
            return self._tier1("Git operation", action_key="git_ops")

        return self._tier1(f"Command execution: {cmd}", action_key=f"cmd_{cmd}")

    def _tier0(self, reason: str) -> RiskDecision:
        return RiskDecision(tier=0, reason=reason, requires_approval=False, session_grantable=False)

    def _tier1(self, reason: str, action_key: str) -> RiskDecision:
        if self.session_grant.is_granted(action_key):
            return RiskDecision(
                tier=1,
                reason=f"{reason} (session granted)",
                requires_approval=False,
                session_grantable=True,
            )
        return RiskDecision(
            tier=1,
            reason=reason,
            requires_approval=True,
            session_grantable=True,
        )

    def _tier2(self, reason: str) -> RiskDecision:
        return RiskDecision(tier=2, reason=reason, requires_approval=True, session_grantable=False)


_global_classifier: RiskClassifier | None = None


def get_risk_classifier() -> RiskClassifier:
    """Get the global risk classifier instance."""
    global _global_classifier
    if _global_classifier is None:
        _global_classifier = RiskClassifier()
    return _global_classifier


def classify_risk(
    action: str,
    args: Any = "",
    source: Literal["local", "telegram"] = "local",
    from_untrusted: bool = False,
    classifier: RiskClassifier | None = None,
) -> RiskDecision:
    """Classify an action's risk level. Central entry point used by all sources."""
    c = classifier or get_risk_classifier()
    return c.classify(action, args, source, from_untrusted)
