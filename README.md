# SanuShell

SanuShell is a **custom Windows shell replacement** built in Python. It uses a **dark neon UI** made with **PySide6** and a safe command engine that runs your own custom commands instead of forcing you to remember standard CMD-style commands.

It is designed to feel like a real shell, but with your own command language.

## What SanuShell does

SanuShell gives you:

* a custom terminal-style window
* your own command names such as `files`, `folders`, `where`, `goto`, `makefolder`, `makefile`, `read`, `ip`, `processes`, and more
* Windows system access through safe command wrappers
* command history with Up/Down arrow support
* tab completion for command names
* live command suggestions
* a dark neon hacker-style theme
* a backend that can later support autocomplete, plugins, AI commands, and more

## Example command style

Instead of remembering traditional shell commands, you can type your own:

```text
files
folders
where
goto C:\Users
makefolder demo
makefile notes.txt
read notes.txt
ip
processes
system
history
calc 5 + 7 * 2
exit
```

## How it works

The project has two major parts:

### 1. Command backend

This is the brain of the shell.

It:

* reads your input
* parses the command
* finds the matching custom command
* executes it
* returns the output back to the UI

### 2. PySide6 UI

This is the shell window.

It:

* shows the output console
* accepts commands from the input box
* displays suggestions
* supports tab completion
* shows the current path and status bar

## Folder structure

```text
SanuShell/
├── main.py
├── core/
│   ├── __init__.py
│   ├── base.py
│   ├── context.py
│   ├── parser.py
│   ├── registry.py
│   └── shell.py
├── commands/
│   ├── __init__.py
│   └── custom_commands.py
├── ui/
│   ├── __init__.py
│   ├── main_window.py
│   └── styles.py
└── utils/
    ├── __init__.py
    └── safe_fs.py
```

## Main features

### Custom commands

Your shell language is custom. You can create your own command names and map them to actions.

### Windows support

This project is built for **Windows** and can work with real system paths.

### Safe filesystem actions

The shell includes safety checks for destructive actions. Some commands use confirmation before deletion.

### Real shell behavior

The shell supports:

* changing directories
* listing files
* reading files
* creating folders
* creating files
* copying, moving, renaming, and deleting files
* viewing network information
* viewing processes
* checking system information
* showing history

### UI polish

The UI includes:

* dark neon theme
* console output area
* command input box
* live suggestions
* tab completion
* command history navigation
* status bar

## Commands

Here is the basic command set currently planned or supported.

### Navigation

* `where` — show current directory
* `cd <path>` — change directory
* `goto <path>` — alias for change directory
* `up` — go to parent folder
* `home` — go to home folder

### Files and folders

* `files [path]` — list files and folders
* `folders [path]` — list only folders
* `makefolder <name>` — create a folder
* `makefile <file>` — create an empty file
* `read <file>` — read file contents
* `open <path>` — open file or folder with Windows default app
* `duplicate <src> <dst>` — copy file or folder
* `shift <src> <dst>` — move file or folder
* `rename <src> <new_name>` — rename file or folder
* `delete confirm <path>` — delete file or folder after confirmation

### Search and view

* `search <text> [path]` — search file and folder names
* `findtext <text> [path]` — search text inside files
* `tree [path] [depth]` — view directory tree

### System info

* `ip` — show IP configuration
* `netstat` — show active network connections
* `ping <host>` — ping a host
* `processes` — show running tasks
* `system` — show system information
* `me` — show current user
* `pc` — show computer name
* `drives` — show available drives
* `disk [path]` — show disk usage
* `path` — show PATH environment variable

### Utility

* `today` — show current date
* `now` — show current time
* `calc <expression>` — safe calculator
* `env` — show environment variables
* `history` — show command history
* `clear` — clear the screen
* `help` — show all available commands
* `exit` — close the shell

## Installation

### 1. Install Python

Make sure Python is installed on your system.

### 2. Install dependencies

```bash
pip install pyside6
```

### 3. Run the shell

```bash
python main.py
```

If `python` does not work on your system, try:

```bash
py main.py
```

## UI usage

When the app opens:

* type a command in the input box
* press **Enter** or click **Run**
* use **Up / Down** arrows for command history
* press **Tab** to complete a command name
* click **Clear** to clear the console output

## Safety notes

This project is meant to be powerful, but still controlled.

Important safety rules:

* commands are executed through the shell’s command registry
* deletion uses a confirmation word
* filesystem operations should be used carefully
* this is not a full unrestricted command runner by default

## Extending the shell

You can add new commands by creating a new class in `commands/custom_commands.py` and registering it in `commands/__init__.py`.

A new command usually needs:

* a unique `name`
* optional `aliases`
* a short `description`
* a `usage` string
* an `execute()` method

Example shape:

```python
class MyCommand(BaseCommand):
    name = "mycommand"
    aliases = []
    description = "My custom command"
    usage = "mycommand <args>"

    def execute(self, ctx, args):
        return CommandResult(output="Hello")
```

## Future ideas

Possible next upgrades:

* autocomplete dropdown refinement
* command palette
* multi-tab terminal sessions
* command groups and categories
* plugin support
* command macros
* AI assistant mode
* better theming
* sound effects and typing animation
* shortcut buttons for favorite commands

## Project goal

The goal of SanuShell is to build a shell that feels modern, looks cool, and uses your own command language while still behaving like a real terminal replacement on Windows.

## License

MIT License. 

## Credits

Built as a custom shell project with Python and PySide6.

## Author

Sanu Sharma (sanusharma.dev)
