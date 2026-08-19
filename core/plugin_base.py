from abc import ABC, abstractmethod


class BasePlugin(ABC):
    """
    Base interface that every RiftShell plugin must implement.

    Keep plugins thin: expose one `plugin = YourPlugin()` object from
    plugins/<name>/plugin.py, then register commands in `register`.
    RiftShell handles discovery, command ownership metadata, UI completion,
    help output, and AI catalog adoption automatically.
    """

    name: str = ""
    version: str = "1.0.0"
    description: str = ""

    @abstractmethod
    def register(self, registry):
        """
        Register the plugin's commands into the RiftShell registry.
        """
        raise NotImplementedError
