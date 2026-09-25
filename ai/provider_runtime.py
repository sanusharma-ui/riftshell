"""Process-local provider cooldowns and bounded diagnostics, without prompt storage."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import logging
import math
import re
from threading import RLock
import time


LOG = logging.getLogger(__name__)


def duration_seconds(value) -> float | None:
    """Accept Retry-After seconds and Groq reset durations such as 1m2.5s."""
    text = str(value if value is not None else "").strip().lower()
    try:
        result = float(text)
    except ValueError:
        parts = re.findall(r"(\d+(?:\.\d+)?)(ms|s|m|h)", text)
        if not parts or "".join(number + unit for number, unit in parts) != text:
            return None
        result = sum(float(number) * {"ms": .001, "s": 1, "m": 60, "h": 3600}[unit]
                     for number, unit in parts)
    return result if math.isfinite(result) and result >= 0 else None


def retry_delay(error) -> float | None:
    headers = getattr(getattr(error, "response", None), "headers", {}) or {}
    value = headers.get("retry-after")
    seconds = duration_seconds(value)
    if seconds is not None:
        return seconds
    if value:
        try:
            return max(0, parsedate_to_datetime(value).timestamp() - time.time())
        except (TypeError, ValueError, OverflowError):
            pass
    match = re.search(r"(?:try again|retry) in ([\d.]+)s", str(error), re.I)
    if match:
        return duration_seconds(match[1])
    # google.api_core RetryInfo details, including the legacy protobuf repr.
    for detail in getattr(error, "details", ()) or ():
        delay = getattr(detail, "retry_delay", None)
        if delay is not None:
            return duration_seconds(delay.seconds + delay.nanos / 1e9)
    match = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", str(error))
    return duration_seconds(match[1]) if match else None


def is_rate_limit(error) -> bool:
    return (getattr(error, "status_code", None) == 429
            or getattr(getattr(error, "response", None), "status_code", None) == 429
            or getattr(error, "code", None) == 429)


def daily_quota(error) -> bool:
    # A generic free_tier_requests metric or a limit of 20 does NOT identify RPD.
    details = str(error) + str(getattr(error, "details", ""))
    return bool(re.search(r"per.?day|requests/day|tokens/day|\b[RT]PD\b", details, re.I))


def seconds_until_pacific_midnight() -> float:
    try:
        from zoneinfo import ZoneInfo
        pacific = ZoneInfo("America/Los_Angeles")
    except (ImportError, KeyError):
        # Windows may not have tzdata; PST is conservative during daylight time.
        pacific = timezone(timedelta(hours=-8))
    now = datetime.now(pacific)
    midnight = datetime.combine(now.date() + timedelta(days=1), datetime.min.time(), pacific)
    return midnight.timestamp() - now.timestamp()


@dataclass(frozen=True)
class Cooldown:
    remaining: float
    daily: bool = False

    def message(self, provider: str) -> str:
        if self.daily:
            return f"{provider.title()}: daily quota exhausted; retry after the quota resets."
        return f"{provider.title()}: rate limited; retry in {max(1, math.ceil(self.remaining))} seconds."


class ProviderRuntime:
    """Shared by desktop turns; credentials are hashed and never logged.

    Limits are scoped to provider, credential and model. Other processes/keys may
    share server quota, so server 429s remain authoritative. No guessed tokenizer
    budget is used to discard context or block a potentially valid request.
    """
    def __init__(self, clock=None, sleep=None):
        self.clock = clock or time.monotonic
        self.sleep = sleep or time.sleep
        self._lock = RLock()
        self._cooldowns = {}
        self._diagnostics = deque(maxlen=100)

    @staticmethod
    def key(provider, credential, model):
        digest = hashlib.sha256(credential.encode()).hexdigest()
        return provider, digest, model

    def cooldown(self, key) -> Cooldown | None:
        with self._lock:
            until, daily = self._cooldowns.get(key, (0, False))
            remaining = until - self.clock()
            if remaining <= 0:
                self._cooldowns.pop(key, None)
                return None
            return Cooldown(remaining, daily)

    def _set(self, key, seconds, daily=False):
        with self._lock:
            now = self.clock()
            # Expire stale entries on writes as well as lookups.
            self._cooldowns = {k: v for k, v in self._cooldowns.items() if v[0] > now}
            old_until, old_daily = self._cooldowns.get(key, (0, False))
            self._cooldowns[key] = (max(old_until, now + seconds), daily or old_daily)

    def record_failure(self, key, error) -> Cooldown | None:
        if not is_rate_limit(error):
            return None
        size = re.search(r"Limit[: ]+([\d,]+).*Requested[: ]+([\d,]+)", str(error), re.I)
        if size and int(size[2].replace(",", "")) > int(size[1].replace(",", "")):
            # Waiting cannot fit this prompt. Try fallback without disabling this
            # provider for smaller requests on subsequent turns.
            return None
        daily = daily_quota(error)
        delay = retry_delay(error)
        if daily:
            if key[0] == "gemini":
                delay = max(delay or 0, seconds_until_pacific_midnight())
            else:
                headers = getattr(getattr(error, "response", None), "headers", {}) or {}
                delay = max(delay or 0, duration_seconds(headers.get("x-ratelimit-reset-requests")) or 3600)
        # Without a server delay, avoid repeated probes but do not invent a reset time.
        self._set(key, max(.1, delay if delay is not None else 60), daily)
        return self.cooldown(key)

    def record_headers(self, key, headers):
        """Preempt only explicit exhaustion; never estimate tokens from characters."""
        for dimension in ("tokens", "requests"):
            try:
                remaining = float(headers.get(f"x-ratelimit-remaining-{dimension}", "nan"))
            except (TypeError, ValueError):
                continue
            delay = duration_seconds(headers.get(f"x-ratelimit-reset-{dimension}"))
            if remaining <= 0 and delay is not None and delay > 0:
                self._set(key, delay, daily=dimension == "requests")

    def wait(self, seconds, cancelled=None, progress=None) -> bool:
        deadline = self.clock() + seconds
        displayed = None
        while self.clock() < deadline:
            if cancelled and cancelled():
                return False
            remaining = deadline - self.clock()
            count = math.ceil(remaining)
            if progress and count != displayed:
                progress(f"AI rate limit: retrying in {count}s. You can stop this request.")
                displayed = count
            self.sleep(min(.1, max(0, remaining)))
        return not (cancelled and cancelled())

    def record(self, stage, *, secrets=(), **fields):
        # Diagnostics contain counts/durations/errors, never prompts or responses.
        if "error" in fields:
            detail = str(fields["error"])
            for secret in secrets:
                if secret:
                    detail = detail.replace(secret, "[redacted]")
            fields["error"] = detail[:8000]
        event = {"stage": stage, "monotonic_seconds": self.clock(), **fields}
        with self._lock:
            self._diagnostics.append(event)
        LOG.debug("Orbit diagnostic: %s", event)

    def diagnostics(self):
        with self._lock:
            return [dict(item) for item in self._diagnostics]


PROVIDER_RUNTIME = ProviderRuntime()
