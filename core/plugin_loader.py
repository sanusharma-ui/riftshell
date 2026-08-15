from pathlib import Path
import importlib.util


class PluginLoader:

    def __init__(self, plugins_dir: Path):
        self.plugins_dir = plugins_dir
        self.loaded_plugins = []
        self.failed_plugins = []

    def load_plugins(self, registry):
        """
        Discover and load all RiftShell plugins.
        """

        if not self.plugins_dir.exists():
            return

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

                plugin.register(registry)

                self.loaded_plugins.append({
                    "name": plugin.name,
                    "version": plugin.version,
                    "description": plugin.description,
                })

            except Exception as exc:
                self.failed_plugins.append({
                    "name": plugin_dir.name,
                    "error": str(exc),
                })

    def _load_plugin(self, plugin_dir: Path, plugin_file: Path):
        """
        Dynamically import a plugin.py file and create its plugin instance.
        """

        module_name = f"riftshell_plugin_{plugin_dir.name}"

        spec = importlib.util.spec_from_file_location(
            module_name,
            plugin_file,
        )

        if spec is None or spec.loader is None:
            raise ImportError(
                f"Could not load plugin: {plugin_dir.name}"
            )

        module = importlib.util.module_from_spec(spec)

        spec.loader.exec_module(module)

        # Every plugin.py must expose `plugin`
        plugin = getattr(module, "plugin", None)

        if plugin is None:
            raise ImportError(
                f"Plugin '{plugin_dir.name}' does not define "
                f"a 'plugin' object."
            )

        return plugin