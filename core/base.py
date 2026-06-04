from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class CommandResult:
    output: str = ""
    success: bool = True
    exit_shell: bool = False


class BaseCommand(ABC):
    name: str = ""
    aliases: List[str] = []
    description: str = ""
    usage: str = ""

    @abstractmethod
    def execute(self, ctx, args: List[str]) -> CommandResult:
        raise NotImplementedError