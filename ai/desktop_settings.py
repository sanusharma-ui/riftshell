"""Desktop-only provider preferences. Secrets never enter QSettings."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QSettings

from ai.config import AIConfig


SERVICE = "RiftShell Orbit"
ACCOUNTS = {"groq": "groq_api_key", "gemini": "gemini_api_key"}


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


def load_desktop_config() -> AIConfig:
    config = AIConfig.from_env()
    settings = QSettings("RiftShell", "RiftShell")
    if not settings.contains("ai/provider"):
        return config

    provider = settings.value("ai/provider", "auto", type=str)
    if provider not in {"auto", "groq", "gemini", "ollama"}:
        provider = "auto"
    store = credential_store() if provider != "ollama" else None
    return replace(
        config,
        ai_provider=provider,
        groq_api_key=(store.get_password(SERVICE, ACCOUNTS["groq"]) or config.groq_api_key) if store else "",
        gemini_api_key=(store.get_password(SERVICE, ACCOUNTS["gemini"]) or config.gemini_api_key) if store else "",
        groq_model=settings.value("ai/groq_model", config.groq_model, type=str).strip() or config.groq_model,
        ollama_base_url=settings.value("ai/ollama_base_url", config.ollama_base_url, type=str).strip().rstrip("/"),
        ollama_model=settings.value("ai/ollama_model", config.ollama_model, type=str).strip(),
        workspace_root=Path(settings.value("ai/workspace_root", str(config.workspace_root), type=str)).expanduser().resolve(strict=False),
        allow_outside_workspace=settings.value("ai/allow_outside_workspace", config.allow_outside_workspace, type=bool),
    )
