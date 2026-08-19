from __future__ import annotations

import importlib.util
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from core.plugin_base import BasePlugin


@dataclass(frozen=True)
class LoadedPlugin:
    name: str
    version: str
    description: str
    path: Path


@dataclass(frozen=True)
class FailedPlugin:
    name: str
    error: str
    path: Path


@dataclass(frozen=True)
class PluginLoadReport:
    loaded: tuple[LoadedPlugin, ...]
    failed: tuple[FailedPlugin, ...]

    @property
    def ok(self) -> bool:
        return not self.failed


class PluginLoader:

    def __init__(self, plugins_dir: Path):
        self.plugins_dir = plugins_dir
        self.loaded_plugins: list[LoadedPlugin] = []
        self.failed_plugins: list[FailedPlugin] = []

    def load_plugins(self, registry) -> PluginLoadReport:
        """
        Discover and load all RiftShell plugins.
        """

        if not self.plugins_dir.exists():
            return self.report()

        for plugin_dir in sorted(self.plugins_dir.iterdir()):

            # Only folders can be plugins
            if not plugin_dir.is_dir():
                continue

            plugin_file = plugin_dir / "plugin.py"

            if not plugin_file.exists():
                continue

            try:
                plugin = self._load_plugin(plugin_dir, plugin_file)

                if plugin is None:
                    continue

                plugin_name = self._plugin_attr(plugin, "name", plugin_dir.name)
                with registry.plugin_scope(plugin_name):
                    plugin.register(registry)

                self.loaded_plugins.append(
                    LoadedPlugin(
                        name=plugin_name,
                        version=self._plugin_attr(plugin, "version", "0.0.0"),
                        description=self._plugin_attr(plugin, "description", ""),
                        path=plugin_dir,
                    )
                )

            except Exception as exc:
                self.failed_plugins.append(
                    FailedPlugin(
                        name=plugin_dir.name,
                        error=str(exc),
                        path=plugin_dir,
                    )
                )

        return self.report()

    def _load_plugin(self, plugin_dir: Path, plugin_file: Path):
        """
        Dynamically import a plugin.py file and create its plugin instance.
        """

        safe_name = re.sub(r"\W+", "_", plugin_dir.name).strip("_") or "plugin"
        module_name = f"riftshell_plugin_{safe_name}"

        spec = importlib.util.spec_from_file_location(
            module_name,
            plugin_file,
        )

        if spec is None or spec.loader is None:
            raise ImportError(
                f"Could not load plugin: {plugin_dir.name}"
            )

        module = importlib.util.module_from_spec(spec)

        plugin_path = str(plugin_dir)
        added_to_path = False
        if plugin_path not in sys.path:
            sys.path.insert(0, plugin_path)
            added_to_path = True

        try:
            spec.loader.exec_module(module)
        finally:
            if added_to_path:
                try:
                    sys.path.remove(plugin_path)
                except ValueError:
                    pass

        # Every plugin.py must expose `plugin`
        plugin = getattr(module, "plugin", None)

        if plugin is None:
            raise ImportError(
                f"Plugin '{plugin_dir.name}' does not define "
                f"a 'plugin' object."
            )

        if not isinstance(plugin, BasePlugin):
            raise TypeError(
                f"Plugin '{plugin_dir.name}' must expose an instance of BasePlugin."
            )

        return plugin

    def _plugin_attr(self, plugin: BasePlugin, attr: str, fallback: str) -> str:
        value = getattr(plugin, attr, fallback) or fallback
        return str(value).strip() or fallback

    def report(self) -> PluginLoadReport:
        return PluginLoadReport(
            loaded=tuple(self.loaded_plugins),
            failed=tuple(self.failed_plugins),
        )
