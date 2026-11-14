"""Desktop-only provider preferences. Secrets never enter QSettings."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QSettings

from ai.config import AIConfig
from ai.modes import decode_modes, select_mode


SERVICE = "RiftShell Orbit"
ACCOUNTS = {
    "groq": "groq_api_key",
    "gemini": "gemini_api_key",
    "telegram": "telegram_bot_token",
}


def credential_store():
    import keyring

    return keyring


def saved_key_exists(provider: str) -> bool:
    return bool(credential_store().get_password(SERVICE, ACCOUNTS[provider]))


def save_api_key(provider: str, value: str) -> None:
    credential_store().set_password(SERVICE, ACCOUNTS[provider], value)


def remove_api_key(provider: str) -> None:
    store = credential_store()
    account = ACCOUNTS[provider]
    if store.get_password(SERVICE, account) is not None:
        store.delete_password(SERVICE, account)


def saved_telegram_token_exists() -> bool:
    return bool(credential_store().get_password(SERVICE, ACCOUNTS["telegram"]))


def save_telegram_token(value: str) -> None:
    credential_store().set_password(SERVICE, ACCOUNTS["telegram"], value)


def remove_telegram_token() -> None:
    store = credential_store()
    account = ACCOUNTS["telegram"]
    if store.get_password(SERVICE, account) is not None:
        store.delete_password(SERVICE, account)


def load_desktop_config() -> AIConfig:
    config = AIConfig.from_env()
    settings = QSettings("RiftShell", "RiftShell")
    if settings.contains("ai/modes") or settings.contains("ai/mode"):
        modes, mode = load_mode_preferences(config, settings)
        config = replace(config, orbit_modes=modes, orbit_mode=mode)
    has_desktop_settings = any(
        settings.contains(key)
        for key in ("ai/provider", "controls/telegram_allowed_user_ids", "controls/telegram_enabled")
    )
    if not has_desktop_settings:
        return config

    provider = settings.value("ai/provider", config.ai_provider, type=str)
    if provider not in {"auto", "groq", "gemini", "ollama"}:
        provider = "auto"
    store = credential_store() if provider != "ollama" else None
    telegram_token = config.telegram_bot_token
    if settings.contains("controls/telegram_enabled"):
        telegram_store = credential_store()
        telegram_token = telegram_store.get_password(SERVICE, ACCOUNTS["telegram"]) or telegram_token
    allowed_ids = _parse_ids(settings.value("controls/telegram_allowed_user_ids", "", type=str))
    return replace(
        config,
        telegram_bot_token=telegram_token,
        telegram_allowed_user_ids=allowed_ids or config.telegram_allowed_user_ids,
        telegram_allow_unlisted_users=settings.value(
            "controls/telegram_allow_unlisted_users",
            config.telegram_allow_unlisted_users,
            type=bool,
        ),
        ai_provider=provider,
        groq_api_key=(store.get_password(SERVICE, ACCOUNTS["groq"]) or config.groq_api_key) if store else "",
        gemini_api_key=(store.get_password(SERVICE, ACCOUNTS["gemini"]) or config.gemini_api_key) if store else "",
        groq_model=settings.value("ai/groq_model", config.groq_model, type=str).strip() or config.groq_model,
        ollama_base_url=settings.value("ai/ollama_base_url", config.ollama_base_url, type=str).strip().rstrip("/"),
        ollama_model=settings.value("ai/ollama_model", config.ollama_model, type=str).strip(),
        workspace_root=Path(settings.value("ai/workspace_root", str(config.workspace_root), type=str)).expanduser().resolve(strict=False),
        allow_outside_workspace=settings.value("ai/allow_outside_workspace", config.allow_outside_workspace, type=bool),
    )


def _parse_ids(value: str) -> set[int]:
    result: set[int] = set()
    for item in (value or "").replace(";", ",").split(","):
        try:
            if item.strip():
                result.add(int(item.strip()))
        except ValueError:
            continue
    return result


def load_mode_preferences(config=None, settings=None):
    """Read non-secret mode preferences without accessing the credential store."""
    config = config or AIConfig.from_env()
    settings = settings or QSettings("RiftShell", "RiftShell")
    modes = decode_modes(settings.value("ai/modes", "", type=str)) if settings.contains("ai/modes") else config.orbit_modes
    mode = select_mode(modes, settings.value("ai/mode", config.orbit_mode.name, type=str))
    return modes, mode
