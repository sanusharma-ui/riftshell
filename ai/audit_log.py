"""Audit logging for Orbit actions with secret redaction and append-only persistence."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re


_SECRET_PATTERNS = re.compile(
    r"(?i)(password|passwd|pwd|pass|token|api[_-]?key|secret|otp|totp|cvv|cvc|credit|card)(\s*[:=]\s*)\S+"
)


class AuditLogger:
    """Append-only audit logger for tracking actions across all interfaces."""

    def __init__(self, log_path: Path | str | None = None):
        if log_path is None:
            self.log_path = Path.home() / ".riftshell" / "audit.jsonl"
        else:
            self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def redact_secrets(cls, text: str) -> str:
        """Redact secrets like passwords, tokens, API keys from logged strings."""
        if not text:
            return ""
        return _SECRET_PATTERNS.sub(r"\1\2[REDACTED]", str(text))[:1000]

    def log_action(
        self,
        source: str,
        user_id: int | None,
        action: str,
        tier: int,
        result: str,
        success: bool = True,
        args: str = "",
    ) -> None:
        """Write an entry to the audit log."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "user_id": user_id,
            "action": self.redact_secrets(action),
            "args": self.redact_secrets(args),
            "tier": tier,
            "result": self.redact_secrets(result),
            "success": success,
        }
        try:
            with open(self.log_path, "a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass


_global_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    global _global_logger
    if _global_logger is None:
        _global_logger = AuditLogger()
    return _global_logger


def audit_action(
    source: str,
    user_id: int | None,
    action: str,
    tier: int,
    result: str,
    success: bool = True,
    args: str = "",
) -> None:
    """Convenience function to log an action with secret redaction."""
    get_audit_logger().log_action(source, user_id, action, tier, result, success=success, args=args)
