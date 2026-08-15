from core.base import BaseCommand, CommandResult
from core.plugin_base import BasePlugin


class HelloCommand(BaseCommand):
    name = "hello"
    aliases = ["hi"]
    description = "Test command from the Hello plugin"
    usage = "hello"

    def execute(self, ctx, args):
        return CommandResult(
            output="Hello from RiftShell Plugin! 🚀"
        )


class HelloPlugin(BasePlugin):
    name = "hello"
    version = "1.0.0"
    description = "Example plugin for testing RiftShell plugin system"

    def register(self, registry):
        registry.register(HelloCommand())


plugin = HelloPlugin()