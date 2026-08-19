from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

from core.base import BaseCommand


@dataclass(frozen=True)
class CommandMetadata:
    name: str
    aliases: tuple[str, ...] = ()
    description: str = ""
    usage: str = ""
    source: str = "core"
    plugin: str | None = None
    extra: dict[str, object] = field(default_factory=dict)


class CommandRegistry:
    def __init__(self):
        self._commands: dict[str, BaseCommand] = {}
        self._primary_names: list[str] = []
        self._metadata: dict[str, CommandMetadata] = {}
        self._active_source = "core"
        self._active_plugin: str | None = None

    def register(
        self,
        command: BaseCommand,
        *,
        source: str | None = None,
        plugin: str | None = None,
        extra: dict[str, object] | None = None,
    ):
        name = command.name.lower()
        aliases = tuple(alias.lower() for alias in getattr(command, "aliases", []))
        source = source or self._active_source
        plugin = plugin if plugin is not None else self._active_plugin

        self._commands[name] = command
        if name not in self._primary_names:
            self._primary_names.append(name)

        self._metadata[name] = CommandMetadata(
            name=name,
            aliases=aliases,
            description=getattr(command, "description", "") or "",
            usage=getattr(command, "usage", "") or name,
            source=source,
            plugin=plugin,
            extra=extra or {},
        )

        for alias in aliases:
            self._commands[alias] = command

    def get(self, name: str):
        return self._commands.get(name.lower())

    def list_commands(self):
        seen = set()
        result = []
        for name in self._primary_names:
            if name in seen:
                continue
            seen.add(name)
            result.append(self._commands[name])
        return result

    def metadata_for(self, name: str) -> CommandMetadata | None:
        command = self.get(name)
        if command is None:
            return None
        return self._metadata.get(command.name.lower())

    def list_metadata(self) -> list[CommandMetadata]:
        return [
            self._metadata[name]
            for name in self._primary_names
            if name in self._metadata
        ]

    def catalog_entries(self) -> list[str]:
        entries = []
        for meta in self.list_metadata():
            alias_text = f" aliases: {', '.join(meta.aliases)};" if meta.aliases else ""
            source_text = f" source: plugin:{meta.plugin};" if meta.plugin else " source: core;"
            entries.append(
                f"{meta.usage};{alias_text}{source_text} {meta.description}".strip()
            )
        return entries

    def all_names(self):
        return sorted(set(self._commands.keys()))

    @contextmanager
    def plugin_scope(self, plugin_name: str) -> Iterator[None]:
        previous_source = self._active_source
        previous_plugin = self._active_plugin
        self._active_source = "plugin"
        self._active_plugin = plugin_name
        try:
            yield
        finally:
            self._active_source = previous_source
            self._active_plugin = previous_plugin
