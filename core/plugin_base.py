from abc import ABC, abstractmethod


class BasePlugin(ABC):
    """
    Base interface that every RiftShell plugin must implement.
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