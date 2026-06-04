from core.registry import CommandRegistry
from .custom_commands import (
    HelpCommand, ExitCommand, ClearCommand, WhereCommand, FilesCommand, FoldersCommand,
    GotoCommand, MakeFolderCommand, MakeFileCommand, ReadCommand, OpenCommand,
    DuplicateCommand, ShiftCommand, RenameCommand, DeleteCommand, SearchCommand,
    FindTextCommand, NetworkCommand, ProcessesCommand, SystemCommand, MeCommand,
    PcCommand, TodayCommand, NowCommand, CalcCommand, HistoryCommand, EnvCommand,
    TreeCommand, VersionCommand, EchoCommand
)


def build_registry() -> CommandRegistry:
    reg = CommandRegistry()
    for cmd in [
        HelpCommand(),
        ExitCommand(),
        ClearCommand(),
        WhereCommand(),
        FilesCommand(),
        FoldersCommand(),
        GotoCommand(),
        MakeFolderCommand(),
        MakeFileCommand(),
        ReadCommand(),
        OpenCommand(),
        DuplicateCommand(),
        ShiftCommand(),
        RenameCommand(),
        DeleteCommand(),
        SearchCommand(),
        FindTextCommand(),
        NetworkCommand(),
        ProcessesCommand(),
        SystemCommand(),
        MeCommand(),
        PcCommand(),
        TodayCommand(),
        NowCommand(),
        CalcCommand(),
        HistoryCommand(),
        EnvCommand(),
        TreeCommand(),
        VersionCommand(),
        EchoCommand(),
    ]:
        reg.register(cmd)
    return reg