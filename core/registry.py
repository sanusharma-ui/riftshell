from core.base import BaseCommand


class CommandRegistry:
    def __init__(self):
        self._commands: dict[str, BaseCommand] = {}
        self._primary_names: list[str] = []

    def register(self, command: BaseCommand):
        name = command.name.lower()
        self._commands[name] = command
        self._primary_names.append(name)

        for alias in getattr(command, "aliases", []):
            self._commands[alias.lower()] = command

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