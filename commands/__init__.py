from core.registry import CommandRegistry
from .custom_commands import (
    HelpCommand, ExitCommand, ClearCommand, WhereCommand, FilesCommand, FoldersCommand,
    CdCommand, GotoCommand, UpCommand, HomeCommand, MakeFolderCommand, MakeFileCommand,
    ReadCommand, OpenCommand, DuplicateCommand, ShiftCommand, RenameCommand, DeleteCommand,
    SearchCommand, FindTextCommand, NetworkCommand, ProcessesCommand, SystemCommand,
    MeCommand, PcCommand, TodayCommand, NowCommand, CalcCommand, HistoryCommand,
    EnvCommand, TreeCommand, VersionCommand, EchoCommand, DrivesCommand, DiskCommand,
    IpCommand, NetstatCommand, PingCommand, PathCommand,
    
    # New Custom Commands
    SleepCommand, RandomCommand, HashCommand, Base64Command,
    DownloadCommand, ZipCommand, UnzipCommand, HeadCommand, KillCommand
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
        CdCommand(),
        GotoCommand(),
        UpCommand(),
        HomeCommand(),
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
        DrivesCommand(),
        DiskCommand(),
        IpCommand(),
        NetstatCommand(),
        PingCommand(),
        PathCommand(),
        
        # New Custom Commands
        SleepCommand(),
        RandomCommand(),
        HashCommand(),
        Base64Command(),
        DownloadCommand(),
        ZipCommand(),
        UnzipCommand(),
        HeadCommand(),
        KillCommand()
    ]:
        reg.register(cmd)
    return reg