"""ai/knowledge_brain.py - Dynamic Command Knowledge Base & Capability Brain.

Maintains structured intelligence about all available commands, their subcommands,
controls, capabilities, usage patterns, and disambiguation notes.
Enables the AI to inspect capabilities when a user asks whether a task is feasible,
how to accomplish a goal, or what commands exist, without bloating prompts with
static raw lists.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Sequence


@dataclass(frozen=True)
class CommandKnowledgeProfile:
    name: str
    aliases: tuple[str, ...] = ()
    description: str = ""
    usage: str = ""
    category: str = "general"
    capabilities: tuple[str, ...] = ()
    controls: tuple[str, ...] = ()
    examples: tuple[tuple[str, str], ...] = ()
    notes: str = ""
    source: str = "core"
    tags: tuple[str, ...] = ()


# --------------------------------------------------------------------------
# Built-in seed profiles for core RiftShell commands with rich capabilities
# --------------------------------------------------------------------------
SEED_PROFILES: dict[str, dict[str, Any]] = {
    "open": {
        "category": "system_and_apps",
        "capabilities": (
            "Launch Windows desktop applications (Notepad, Calculator, VS Code, Chrome, Edge, Discord, etc.)",
            "Open websites and web shortcuts in default browser (YouTube, GitHub, Google, Reddit, etc.)",
            "Open local files with their associated system program",
            "Open folders directly in Windows File Explorer",
            "Launch Windows system utilities (cmd, powershell, taskmgr, settings)",
        ),
        "controls": (
            "open <app_name> -> launch application by name or executable",
            "open <url|domain> -> open website or web address",
            "open <file_path> -> open file in default editor/viewer",
            "open <folder_path> -> reveal folder in Windows Explorer",
        ),
        "examples": (
            ("open notepad", "open notepad"),
            ("open youtube", "open youtube"),
            ("open https://github.com", "open https://github.com"),
            ("open D:\\projects", "open D:\\projects"),
        ),
        "notes": "Fastest way to launch programs, websites, and files on Windows. Uses Registry App Paths and PATH discovery.",
        "tags": ("kholo", "launch", "start", "run", "app", "website", "program", "browser", "folder", "explorer", "calculator", "notepad", "chrome"),
    },
    "browser": {
        "category": "browser_and_web",
        "capabilities": (
            "Automate browser navigation and web browsing via Playwright",
            "Search the web using Google, YouTube, DuckDuckGo, Bing, or GitHub",
            "Play video/audio or music directly on YouTube",
            "Control active browser tab (refresh, back, forward, new tab, close, scroll up/down)",
            "Inspect page context and active tabs",
            "Click matching text and fill form inputs programmatically",
        ),
        "controls": (
            "browser open <url> -> open URL in browser session",
            "browser search <query> [--engine <google|youtube|duckduckgo>] -> search web",
            "browser play <query_or_index> -> play video or search result",
            "browser control <back|forward|refresh|new_tab|close_tab|scroll_up|scroll_down|play|pause> -> tab controls",
            "browser tabs -> list active browser tabs",
            "browser tab <index> -> switch active tab",
            "browser click <text_or_css> -> click element",
            "browser fill <selector> <text> -> fill form element",
            "browser close -> close browser session",
        ),
        "examples": (
            ("search python tutorials in browser", "browser search python tutorials"),
            ("play lofi music on youtube", "browser search lofi hip hop --engine youtube"),
            ("refresh current webpage", "browser control refresh"),
            ("open github in browser", "browser open https://github.com"),
        ),
        "notes": "Interactive headless/headed browser automation controller. Handles search, playback, navigation, and web scraping.",
        "tags": ("browse", "internet", "web", "youtube", "google", "search", "play", "gaana", "music", "video", "tabs", "tab", "automation"),
    },
    "note": {
        "category": "text_and_utilities",
        "capabilities": (
            "Quickly capture text notes with automatic timestamping",
            "Persist notes to a safe notes folder and launch in Notepad for immediate viewing/editing",
        ),
        "controls": (
            "note <text> -> append timestamped note and open in Notepad",
        ),
        "examples": (
            ("note buy groceries and finish homework", "note buy groceries and finish homework"),
            ("take note meeting at 5pm", "note meeting at 5pm"),
        ),
        "notes": "Creates or appends to a dated notes file in user Documents (or workspace) and displays it in Notepad.",
        "tags": ("note", "notes", "write", "memo", "diary", "notepad", "likho", "yaad"),
    },
    "findtext": {
        "category": "search_and_inspection",
        "capabilities": (
            "Search for specific text, keywords, or strings INSIDE file contents (grep equivalent)",
            "Find passwords, API keys, error strings, function definitions across project files",
        ),
        "controls": (
            "findtext <query> -> search inside all files in current directory",
            "findtext <query> <folder> -> search inside files under specified directory",
        ),
        "examples": (
            ("find text password in files", "findtext password"),
            ("search for function main in src", "findtext def main src"),
        ),
        "notes": "Searches INSIDE file content. To find files by filename, use 'search' instead.",
        "tags": ("grep", "search", "find", "content", "inside", "text", "password", "dhundho", "dhoondo", "string"),
    },
    "search": {
        "category": "search_and_inspection",
        "capabilities": (
            "Search for files or directories by name (filename matching)",
            "Filter filenames matching a substring or pattern across subdirectories",
        ),
        "controls": (
            "search <pattern> -> search filenames in current directory",
            "search <pattern> <folder> -> search filenames within a specific directory",
        ),
        "examples": (
            ("find files named config", "search config"),
            ("search for python files in tests", "search test tests"),
        ),
        "notes": "Searches file and directory NAMES only. For content search, use 'findtext'.",
        "tags": ("filename", "find", "search", "locate", "files", "naam", "dhundho"),
    },
    "zip": {
        "category": "files_and_archives",
        "capabilities": (
            "Compress directories or files into standard .zip archives",
            "Package folders for backup or distribution",
        ),
        "controls": (
            "zip <source_folder> <target_archive.zip> -> compress folder into zip",
        ),
        "examples": (
            ("zip project folder into backup.zip", "zip project backup.zip"),
        ),
        "notes": "Creates a compressed zip archive from source directory.",
        "tags": ("compress", "archive", "zip", "backup", "package", "bundle"),
    },
    "unzip": {
        "category": "files_and_archives",
        "capabilities": (
            "Extract contents of a .zip archive into the current or target directory",
            "Unpack downloaded or backup archives",
        ),
        "controls": (
            "unzip <archive.zip> -> extract here",
            "unzip <archive.zip> <destination_folder> -> extract to specific folder",
        ),
        "examples": (
            ("unzip data.zip", "unzip data.zip"),
            ("extract backup.zip to output folder", "unzip backup.zip output"),
        ),
        "notes": "Safely uncompresses zip files with path traversal protections.",
        "tags": ("extract", "unzip", "unpack", "uncompress", "archive"),
    },
    "download": {
        "category": "network_and_web",
        "capabilities": (
            "Download files from HTTP/HTTPS URLs directly onto the local filesystem",
            "Fetch online datasets, scripts, or assets",
        ),
        "controls": (
            "download <url> -> download with original filename",
            "download <url> <destination_filename> -> save to specific file",
        ),
        "examples": (
            ("download https://example.com/data.csv", "download https://example.com/data.csv"),
            ("download file and save as sample.txt", "download https://example.com/file.txt sample.txt"),
        ),
        "notes": "Direct HTTP download utility without requiring external curl/wget.",
        "tags": ("download", "fetch", "get", "url", "web", "internet"),
    },
    "files": {
        "category": "files_and_navigation",
        "capabilities": (
            "List all files and folders in the current or specified directory",
            "Inspect directory contents with file sizes and timestamps",
        ),
        "controls": (
            "files -> list current directory",
            "files <path> -> list specific directory",
        ),
        "examples": (
            ("list files", "files"),
            ("show files in src", "files src"),
        ),
        "notes": "Shows both files and folders. For folders only, use 'folders'.",
        "tags": ("ls", "dir", "list", "files", "dikhana", "folders", "contents"),
    },
    "folders": {
        "category": "files_and_navigation",
        "capabilities": (
            "List only subdirectories/folders, omitting files",
        ),
        "controls": (
            "folders -> list subdirectories in current directory",
            "folders <path> -> list subdirectories in path",
        ),
        "examples": (
            ("show folders", "folders"),
        ),
        "notes": "Filters out files and displays only directories.",
        "tags": ("folders", "directories", "subdirectories", "dir", "dibbe"),
    },
    "where": {
        "category": "files_and_navigation",
        "capabilities": (
            "Report current working directory path",
        ),
        "controls": ("where -> display current directory",),
        "examples": (("where am i", "where"), ("current folder", "where")),
        "notes": "Tells where the shell currently is. To find where an executable is installed, use 'which'.",
        "tags": ("pwd", "where", "location", "current", "folder", "kaha"),
    },
    "cd": {
        "category": "files_and_navigation",
        "capabilities": (
            "Change active working directory or drive",
            "Navigate into project subfolders or parent folders",
        ),
        "controls": (
            "cd <path> -> navigate to directory",
            "goto <path> -> alias for cd",
        ),
        "examples": (("go to src", "cd src"), ("switch to D drive", "cd D:\\")),
        "notes": "Changes directory. Supports relative and absolute paths.",
        "tags": ("cd", "goto", "navigate", "change", "drive", "jao", "chal"),
    },
    "makefolder": {
        "category": "files_and_navigation",
        "capabilities": (
            "Create a new directory/folder",
        ),
        "controls": ("makefolder <folder_name> -> create folder",),
        "examples": (("create folder test", "makefolder test"),),
        "notes": "Equivalent to mkdir.",
        "tags": ("mkdir", "makefolder", "folder", "create", "bana", "dabba"),
    },
    "makefile": {
        "category": "files_and_navigation",
        "capabilities": (
            "Create a new blank/empty file",
        ),
        "controls": ("makefile <file_name> -> create empty file",),
        "examples": (("create empty file a.txt", "makefile a.txt"),),
        "notes": "Creates a zero-byte blank file.",
        "tags": ("touch", "makefile", "file", "create", "empty", "bana"),
    },
    "read": {
        "category": "files_and_navigation",
        "capabilities": (
            "Print file contents directly in terminal console",
        ),
        "controls": ("read <file_path> -> print file text",),
        "examples": (("read notes.txt", "read notes.txt"),),
        "notes": "Prints text in the terminal. To open in GUI editor, use 'open'.",
        "tags": ("cat", "read", "type", "content", "print", "parho"),
    },
    "duplicate": {
        "category": "files_and_navigation",
        "capabilities": (
            "Copy a file or directory to a target destination",
        ),
        "controls": ("duplicate <source> <target> -> copy file or directory",),
        "examples": (("copy a.txt to b.txt", "duplicate a.txt b.txt"),),
        "notes": "Equivalent to copy / cp.",
        "tags": ("cp", "copy", "duplicate", "clone", "nakal"),
    },
    "shift": {
        "category": "files_and_navigation",
        "capabilities": (
            "Move a file or directory to a different folder",
        ),
        "controls": ("shift <source> <target_folder> -> move file",),
        "examples": (("move notes.txt to archive", "shift notes.txt archive"),),
        "notes": "Equivalent to move / mv.",
        "tags": ("mv", "move", "shift", "relocate"),
    },
    "rename": {
        "category": "files_and_navigation",
        "capabilities": (
            "Change the name of a file or folder",
        ),
        "controls": ("rename <old_name> <new_name> -> rename item",),
        "examples": (("rename a.txt b.txt", "rename a.txt b.txt"),),
        "notes": "Changes filename in-place.",
        "tags": ("rename", "name", "badlo"),
    },
    "delete": {
        "category": "files_and_navigation",
        "capabilities": (
            "Permanently delete files or directories",
        ),
        "controls": ("delete confirm <path> -> permanently delete item",),
        "examples": (("delete file a.txt", "delete confirm a.txt"),),
        "notes": "DESTRUCTIVE. Requires confirmation argument.",
        "tags": ("rm", "delete", "remove", "erase", "hatao", "saaf"),
    },
    "processes": {
        "category": "system_and_hardware",
        "capabilities": (
            "List active running system processes with PID, name, and memory consumption",
            "Check for resource hogs or unresponsive programs",
        ),
        "controls": ("processes -> list running processes",),
        "examples": (("show running processes", "processes"),),
        "notes": "Provides process name and ID needed for 'kill'.",
        "tags": ("ps", "processes", "tasklist", "running", "cpu", "apps", "chal"),
    },
    "kill": {
        "category": "system_and_hardware",
        "capabilities": (
            "Terminate a running process by name or PID",
        ),
        "controls": ("kill <process_name.exe|pid> -> terminate process",),
        "examples": (("kill chrome.exe", "kill chrome.exe"), ("kill 1234", "kill 1234")),
        "notes": "Terminates hung or unwanted tasks. On Windows, use .exe extension or PID.",
        "tags": ("kill", "terminate", "stop", "taskkill", "band", "roko"),
    },
    "memory": {
        "category": "system_and_hardware",
        "capabilities": (
            "Check total, used, and free RAM/memory statistics",
        ),
        "controls": ("memory -> display RAM usage",),
        "examples": (("check memory usage", "memory"), ("how much ram is used", "memory")),
        "notes": "Reports system RAM consumption and percentages.",
        "tags": ("ram", "memory", "usage", "hardware"),
    },
    "system": {
        "category": "system_and_hardware",
        "capabilities": (
            "Display comprehensive OS, CPU, RAM, and machine system specifications",
        ),
        "controls": ("system -> display machine specs",),
        "examples": (("system info", "system"),),
        "notes": "Full computer hardware and OS overview.",
        "tags": ("specs", "hardware", "cpu", "os", "system", "computer"),
    },
    "network": {
        "category": "network_and_connectivity",
        "capabilities": (
            "Display network adapter configurations, IP addresses, and gateway details",
        ),
        "controls": ("network -> show network adapters",),
        "examples": (("check network info", "network"),),
        "notes": "Equivalent to ipconfig.",
        "tags": ("ipconfig", "network", "adapters", "wifi", "ethernet", "lan"),
    },
    "netstat": {
        "category": "network_and_connectivity",
        "capabilities": (
            "Inspect active network connections and listening ports",
        ),
        "controls": ("netstat -> list connections and ports",),
        "examples": (("show open ports", "netstat"),),
        "notes": "Reveals active TCP connections and listening ports.",
        "tags": ("ports", "connections", "netstat", "sockets"),
    },
    "ping": {
        "category": "network_and_connectivity",
        "capabilities": (
            "Test network reachability and packet latency to a remote host or IP",
        ),
        "controls": ("ping <host> -> test connectivity",),
        "examples": (("ping google.com", "ping google.com"),),
        "notes": "Tests internet or LAN reachability.",
        "tags": ("ping", "connectivity", "latency", "host"),
    },
    "run": {
        "category": "native_execution",
        "capabilities": (
            "Execute arbitrary native CLI programs (python, pip, git, npm, node, uvicorn, etc.)",
        ),
        "controls": ("run <command_line> -> run external program",),
        "examples": (("run python main.py", "run python main.py"), ("run git status", "run git status")),
        "notes": "Runs native executable directly inside shell environment.",
        "tags": ("exec", "execute", "run", "native", "python", "npm", "cli"),
    },
    "gstatus": {
        "category": "git_vcs",
        "capabilities": (
            "Check Git repository working tree status, staged files, and branch info",
        ),
        "controls": ("gstatus -> show Git status",),
        "examples": (("git status", "gstatus"),),
        "notes": "Shows modified, staged, and untracked files.",
        "tags": ("git", "status", "gstatus", "branch", "repo"),
    },
    "gdiff": {
        "category": "git_vcs",
        "capabilities": (
            "Show unstaged Git differences and code modifications",
        ),
        "controls": ("gdiff -> show git diff",),
        "examples": (("show git changes", "gdiff"),),
        "notes": "Inspects line-by-line changes.",
        "tags": ("git", "diff", "gdiff", "changes"),
    },
    "gadd": {
        "category": "git_vcs",
        "capabilities": (
            "Stage files in Git",
        ),
        "controls": ("gadd <path> -> stage file or all (.)",),
        "examples": (("stage all files", "gadd ."),),
        "notes": "Prepares files for commit.",
        "tags": ("git", "add", "stage", "gadd"),
    },
    "gcommit": {
        "category": "git_vcs",
        "capabilities": (
            "Create a new Git commit with a descriptive message",
        ),
        "controls": ("gcommit <message> -> commit staged files",),
        "examples": (("commit changes", "gcommit fix issue"),),
        "notes": "Commits staged files.",
        "tags": ("git", "commit", "gcommit"),
    },
    "calc": {
        "category": "text_and_utilities",
        "capabilities": (
            "Perform mathematical calculations and evaluate arithmetic expressions safely",
        ),
        "controls": ("calc <expression> -> evaluate math",),
        "examples": (("calc 25 * 40", "calc 25 * 40"),),
        "notes": "Evaluates arithmetic expressions safely using AST without eval.",
        "tags": ("math", "calculate", "calc", "hisaab"),
    },
    "hash": {
        "category": "text_and_utilities",
        "capabilities": (
            "Calculate SHA256 cryptographic checksum of a file or string",
        ),
        "controls": (
            "hash file <path> -> compute SHA256 of file",
            "hash text <string> -> compute SHA256 of string",
        ),
        "examples": (("hash file main.py", "hash file main.py"),),
        "notes": "Provides file integrity verification.",
        "tags": ("hash", "sha256", "checksum", "integrity"),
    },
    "theme": {
        "category": "environment_and_shell",
        "capabilities": (
            "List, show, or switch RiftShell UI themes (vscode-dark-plus / Rift Horizon, github-dark, midnight-aurora, ember-grove)",
            "Discover new themes and inspect active color theme",
            "Switch the terminal interface theme dynamically",
        ),
        "controls": (
            "theme list (or theme) -> list all available RiftShell themes",
            "theme current -> show the active theme",
            "theme <name> -> switch to theme (e.g. theme midnight-aurora, theme ember-grove, theme github-dark)",
        ),
        "examples": (
            ("show themes", "theme"),
            ("list themes", "theme list"),
            ("help me to find new themes", "theme"),
            ("change theme to midnight-aurora", "theme midnight-aurora"),
        ),
        "notes": "RiftShell themes are vscode-dark-plus (Rift Horizon), github-dark, midnight-aurora, and ember-grove.",
        "tags": ("theme", "themes", "color", "appearance", "ui", "look", "dark", "aurora", "midnight", "ember", "horizon", "badlo"),
    },
    "drives": {
        "category": "system_and_hardware",
        "capabilities": (
            "List all installed storage drives, disks, partitions, and volumes on the computer",
            "Display drive letters (C:, D:), volume names, drive types, total storage, and free space",
            "Determine how many physical and logical disks are installed on the system",
        ),
        "controls": (
            "drives -> list all system drives and storage disks",
        ),
        "examples": (
            ("how many disks are installed on my computer", "drives"),
            ("list all drives", "drives"),
            ("show installed disks", "drives"),
            ("kitne disk hai", "drives"),
        ),
        "notes": "Always use `drives` to inspect how many disks/drives are installed and their storage breakdown.",
        "tags": ("drives", "drive", "disks", "disk", "storage", "harddrive", "hdd", "ssd", "partitions", "volumes", "hardware", "installed"),
    },
    "disk": {
        "category": "system_and_hardware",
        "capabilities": (
            "Check disk space and usage for the current directory or a specified folder/drive",
            "Display total, used, and free storage space in human-readable format",
        ),
        "controls": (
            "disk -> display disk usage of current directory",
            "disk <path> -> display disk usage of specified path or drive",
        ),
        "examples": (
            ("check disk space", "disk"),
            ("disk space of D:", "disk D:"),
        ),
        "notes": "For all installed disks across the system, use `drives`. For a folder/drive space, use `disk`.",
        "tags": ("disk", "space", "usage", "free", "storage"),
    },
    "system": {
        "category": "system_and_hardware",
        "capabilities": (
            "Display comprehensive system specifications and hardware details",
            "Show OS name and version, computer name, processor / CPU model, core count, architecture, and total physical RAM",
        ),
        "controls": (
            "system -> display complete system hardware and OS information",
        ),
        "examples": (
            ("system info", "system"),
            ("hardware details", "system"),
            ("pc specs", "system"),
        ),
        "notes": "Provides complete hardware and operating system details without external scripts.",
        "tags": ("system", "specs", "hardware", "cpu", "processor", "os", "specifications", "computer", "machine"),
    },
    "memory": {
        "category": "system_and_hardware",
        "capabilities": (
            "Inspect computer RAM and memory usage",
            "Display total physical RAM, used RAM, free RAM, and swap memory statistics",
        ),
        "controls": (
            "memory -> display current RAM consumption and availability",
        ),
        "examples": (
            ("check ram", "memory"),
            ("ram usage", "memory"),
            ("ram kitni hai", "memory"),
        ),
        "notes": "Instant memory diagnostics.",
        "tags": ("ram", "memory", "usage", "free", "swap"),
    },
    "ip": {
        "category": "network_and_connectivity",
        "capabilities": (
            "Display the computer's IP address and network configuration",
            "Show network adapter names, IPv4/IPv6 addresses, subnet masks, and gateways",
        ),
        "controls": (
            "ip -> display IP configuration",
        ),
        "examples": (
            ("what is my ip address", "ip"),
            ("mera ip kya hai", "ip"),
        ),
        "notes": "Instant network IP identification.",
        "tags": ("ip", "ipconfig", "address", "network", "adapter", "internet"),
    },
}

# Hindi / Hinglish translation map for natural task inquiries
HINDI_TASK_KEYWORDS: dict[str, tuple[str, ...]] = {
    "kholo": ("open", "browser"),
    "kholna": ("open", "browser"),
    "chalao": ("browser", "open", "run"),
    "chala": ("browser", "open", "run"),
    "gaana": ("browser", "open"),
    "gana": ("browser", "open"),
    "music": ("browser", "open"),
    "video": ("browser", "open"),
    "dhundho": ("findtext", "search"),
    "dhundhna": ("findtext", "search"),
    "dhoondo": ("findtext", "search"),
    "khojo": ("findtext", "search"),
    "nakal": ("duplicate",),
    "copy": ("duplicate",),
    "hatao": ("delete", "kill"),
    "hata": ("delete", "kill"),
    "band": ("kill", "exit"),
    "roko": ("kill",),
    "dabba": ("makefolder", "folders"),
    "folder": ("makefolder", "folders", "files", "cd"),
    "khali": ("makefile",),
    "parho": ("read",),
    "padho": ("read",),
    "likho": ("note",),
    "likhna": ("note",),
    "tareekh": ("today",),
    "samay": ("now",),
    "waqt": ("now",),
    "chal raha": ("processes",),
    "kitna": ("memory", "disk", "uptime"),
    "kitne": ("drives", "files", "folders"),
    "internet": ("network", "ping", "browser", "download"),
    "net": ("network", "ping", "browser"),
    "zip": ("zip", "unzip"),
    "unzip": ("unzip",),
    "theme": ("theme",),
    "themes": ("theme",),
    "badlo": ("theme", "rename", "shift", "cd"),
    "badal": ("theme", "rename", "shift", "cd"),
    "disk": ("drives", "disk"),
    "disks": ("drives", "disk"),
    "drive": ("drives",),
    "drives": ("drives",),
    "hardware": ("system", "drives", "memory"),
    "specs": ("system", "drives", "memory"),
    "ram": ("memory",),
    "ip": ("ip",),
}


COMMON_STOPWORD_COMMANDS = {"me", "up", "cd", "now", "last", "path", "run", "where"}

ACTION_OFFER = "Want me to do this now? Reply **yes** or **kar do**."

CORE_CATEGORY_MAP: dict[str, str] = {
    # Files & Navigation
    "files": "files_and_navigation", "folders": "files_and_navigation", "cd": "files_and_navigation",
    "goto": "files_and_navigation", "home": "files_and_navigation", "up": "files_and_navigation",
    "where": "files_and_navigation", "makefolder": "files_and_navigation", "makefile": "files_and_navigation",
    "delete": "files_and_navigation", "duplicate": "files_and_navigation", "rename": "files_and_navigation",
    "tree": "files_and_navigation", "path": "files_and_navigation", "drives": "files_and_navigation",
    # Search & Inspection
    "findtext": "search_and_inspection", "search": "search_and_inspection", "which": "search_and_inspection",
    "read": "search_and_inspection", "head": "search_and_inspection", "tail": "search_and_inspection",
    "wc": "search_and_inspection", "count": "search_and_inspection",
    # System & Hardware
    "open": "system_and_apps", "processes": "system_and_hardware", "kill": "system_and_hardware",
    "memory": "system_and_hardware", "disk": "system_and_hardware", "uptime": "system_and_hardware",
    "system": "system_and_hardware", "pc": "system_and_hardware", "sleep": "system_and_hardware",
    "exit": "system_and_hardware", "clear": "system_and_hardware",
    # Browser & Web
    "browser": "browser_and_web", "download": "network_and_web", "ping": "network_and_connectivity",
    "network": "network_and_connectivity", "netstat": "network_and_connectivity", "ip": "network_and_connectivity",
    # Git & VCS
    "gstatus": "git_vcs", "gadd": "git_vcs", "gcommit": "git_vcs", "gdiff": "git_vcs",
    "glog": "git_vcs", "gbranch": "git_vcs", "gcheckout": "git_vcs", "gpush": "git_vcs",
    "gpull": "git_vcs", "gremote": "git_vcs",
    # Archives
    "zip": "files_and_archives", "unzip": "files_and_archives",
    # Text & Utilities
    "note": "text_and_utilities", "calc": "text_and_utilities", "hash": "text_and_utilities",
    "base64": "text_and_utilities", "today": "text_and_utilities", "now": "text_and_utilities",
    "echo": "text_and_utilities", "random": "text_and_utilities", "sort": "text_and_utilities",
    "filter": "text_and_utilities", "unique": "text_and_utilities", "take": "text_and_utilities",
    "skip": "text_and_utilities", "shift": "text_and_utilities", "save": "text_and_utilities",
    # Environment & Shell
    "alias": "environment_and_shell", "unalias": "environment_and_shell", "setvar": "environment_and_shell",
    "unsetvar": "environment_and_shell", "vars": "environment_and_shell", "env": "environment_and_shell",
    "history": "environment_and_shell", "last": "environment_and_shell", "theme": "environment_and_shell",
    "plugins": "environment_and_shell", "update": "environment_and_shell", "version": "environment_and_shell",
    "help": "environment_and_shell",
    # Native
    "run": "native_execution",
}


class CommandKnowledgeBrain:
    """Dynamic Knowledge Brain that indexes and queries shell command capabilities."""

    def __init__(
        self,
        command_metadata: Sequence[Any] | None = None,
        command_names: Sequence[str] | None = None,
    ):
        self._profiles: dict[str, CommandKnowledgeProfile] = {}
        self._primary_names: set[str] = set()
        self.index_commands(command_metadata, command_names)

    def index_commands(
        self,
        command_metadata: Sequence[Any] | None = None,
        command_names: Sequence[str] | None = None,
    ) -> None:
        """Indexes metadata into structured knowledge profiles, merging seed knowledge."""
        meta_dict: dict[str, Any] = {}
        alias_to_primary: dict[str, str] = {}
        if command_metadata:
            for meta in command_metadata:
                name = getattr(meta, "name", "").lower()
                if name:
                    meta_dict[name] = meta
                    for a in getattr(meta, "aliases", ()):
                        alias_to_primary[a.lower()] = name

        self._primary_names = set(meta_dict.keys())

        names_set = set(meta_dict.keys())
        if command_names:
            names_set.update(n.lower() for n in command_names)
        names_set.update(SEED_PROFILES.keys())

        for name in sorted(names_set):
            meta = meta_dict.get(name)
            primary_name = alias_to_primary.get(name, name)
            seed = SEED_PROFILES.get(name) or SEED_PROFILES.get(primary_name, {})

            aliases = getattr(meta, "aliases", ()) if meta else ()
            if not aliases and "aliases" in seed:
                aliases = seed["aliases"]

            description = getattr(meta, "description", "") if meta else ""
            if not description and "capabilities" in seed and seed["capabilities"]:
                description = seed["capabilities"][0]

            usage = getattr(meta, "usage", "") if meta else ""
            if not usage:
                usage = seed.get("controls", (name,))[0].split("->")[0].strip() if seed.get("controls") else name

            category = seed.get("category")
            if not category:
                if getattr(meta, "plugin", None):
                    category = "plugin"
                elif name in CORE_CATEGORY_MAP:
                    category = CORE_CATEGORY_MAP[name]
                elif primary_name in CORE_CATEGORY_MAP:
                    category = CORE_CATEGORY_MAP[primary_name]
                elif name.startswith("g") and len(name) > 2:
                    category = "git_vcs"
                else:
                    category = "general"
            capabilities = tuple(seed.get("capabilities", (description,) if description else ()))
            controls = tuple(seed.get("controls", (usage,) if usage else ()))
            examples = tuple(seed.get("examples", ()))
            notes = seed.get("notes", "")
            source = getattr(meta, "source", "core") if meta else "core"
            tags = tuple(seed.get("tags", (name,)))

            self._profiles[name] = CommandKnowledgeProfile(
                name=name,
                aliases=tuple(aliases),
                description=description,
                usage=usage,
                category=category,
                capabilities=capabilities,
                controls=controls,
                examples=examples,
                notes=notes,
                source=source,
                tags=tags,
            )

    def register_command(
        self,
        name: str,
        aliases: tuple[str, ...] = (),
        description: str = "",
        usage: str = "",
        category: str = "custom",
        capabilities: tuple[str, ...] = (),
        controls: tuple[str, ...] = (),
        examples: tuple[tuple[str, str], ...] = (),
        notes: str = "",
        source: str = "plugin",
        tags: tuple[str, ...] = (),
    ) -> None:
        """Dynamically add or update a command in the knowledge brain."""
        profile = CommandKnowledgeProfile(
            name=name.lower(),
            aliases=tuple(a.lower() for a in aliases),
            description=description,
            usage=usage or name,
            category=category,
            capabilities=capabilities or ((description,) if description else ()),
            controls=controls or ((usage,) if usage else (name,)),
            examples=examples,
            notes=notes,
            source=source,
            tags=tags or (name.lower(),),
        )
        self._profiles[name.lower()] = profile

    def sync_with_registry(self, registry: Any) -> None:
        """Syncs all commands and metadata dynamically from a CommandRegistry instance."""
        if hasattr(registry, "list_metadata"):
            self.index_commands(
                command_metadata=registry.list_metadata(),
                command_names=registry.all_names() if hasattr(registry, "all_names") else None,
            )

    def get_profile(self, name: str) -> CommandKnowledgeProfile | None:
        """Retrieve the knowledge profile for a specific command."""
        target = name.lower()
        if target in self._profiles:
            return self._profiles[target]
        for p in self._profiles.values():
            if target in p.aliases:
                return p
        return None

    def all_profiles(self) -> list[CommandKnowledgeProfile]:
        """List all registered command knowledge profiles."""
        return list(self._profiles.values())

    def _categorize_commands(self) -> dict[str, list[str]]:
        """Groups registered primary command names by category, falling back to all names."""
        categories: dict[str, list[str]] = {}
        for p in self._profiles.values():
            cat = p.category or "general"
            if cat not in categories:
                categories[cat] = []
            # Prefer primary commands in category listings
            if not self._primary_names or p.name in self._primary_names:
                if p.name not in categories[cat]:
                    categories[cat].append(p.name)

        # Fallback if primary set was empty
        if not any(categories.values()):
            for p in self._profiles.values():
                cat = p.category or "general"
                if cat not in categories:
                    categories[cat] = []
                if p.name not in categories[cat]:
                    categories[cat].append(p.name)

        for cat in categories:
            categories[cat].sort()
        return categories

    def is_command_count_query(self, query: str) -> bool:
        """Checks if the query asks for the count/number of available commands."""
        text = query.strip().lower()
        patterns = [
            r"\b(?:how\s+many|total|number\s+of|count\s+of)\s+commands?\b",
            r"\bhow\s+many\s+command\s+(?:we|do\s+we|are)\b",
            r"\bcommands?\s+(?:kitne|count|number|total|we\s+have)\b",
            r"\b(?:kitne|total)\s+commands?\b",
            r"\bcommand\s+count\b",
            r"\bkitne\s+(?:commands|tools|options)\s+hai\b",
        ]
        return any(re.search(pat, text, re.IGNORECASE) for pat in patterns)

    def is_command_list_query(self, query: str) -> bool:
        """Checks if the query asks to view or list all available commands or categories."""
        text = query.strip().lower()
        patterns = [
            r"\b(?:what|which)\s+commands?\s+(?:do\s+we\s+have|are\s+there|exist|are\s+available|can\s+i\s+use|do\s+you\s+have|we\s+got)\b",
            r"\b(?:list|show|view|see)\s+(?:all\s+)?(?:the\s+)?commands?\b",
            r"\bcommands?\s+(?:list|options|available|overview)\b",
            r"\b(?:kaun\s*se|kya)\s+commands?\s+hai\b",
            r"\bsaare\s+commands?\b",
            r"\ball\s+available\s+commands?\b",
        ]
        return any(re.search(pat, text, re.IGNORECASE) for pat in patterns)

    def get_command_count_summary(self, brief: bool = False) -> str:
        """Generates a brief, direct summary of command count and categories."""
        total = len(self._profiles)
        primary_count = len(self._primary_names) if self._primary_names else total
        categories = self._categorize_commands()

        category_labels = {
            "files_and_navigation": "Files & Navigation",
            "search_and_inspection": "Search & Inspection",
            "system_and_hardware": "System & Hardware",
            "system_and_apps": "System & Apps",
            "browser_and_web": "Browser & Web Automation",
            "network_and_connectivity": "Network & Connectivity",
            "network_and_web": "Network & Downloads",
            "git_vcs": "Git & Version Control",
            "files_and_archives": "Archives & Compression",
            "text_and_utilities": "Text & Utilities",
            "environment_and_shell": "Environment & Shell",
            "native_execution": "Native Execution",
            "plugin": "Plugins",
            "general": "General Utilities",
        }

        if brief:
            # Short answer for "how many commands" questions: count + a few category names.
            ranked = sorted(
                ((cat, names) for cat, names in categories.items() if names and cat != "general"),
                key=lambda item: len(item[1]),
                reverse=True,
            )
            top_labels = [category_labels.get(cat, cat.replace("_", " ").title()) for cat, _ in ranked[:4]]
            where = f" across categories like {', '.join(top_labels)}" if top_labels else ""
            return (
                f"RiftShell has **{primary_count} commands registered** (**{total} names including aliases**){where}.\n\n"
                "\U0001F4A1 Run `help` or press **Ctrl+K** to browse all commands."
            )

        # Build clean bulleted category list
        cat_lines = []
        for cat, names in sorted(categories.items()):
            if not names:
                continue
            label = category_labels.get(cat, cat.replace("_", " ").title())
            sample = ", ".join(f"`{n}`" for n in names[:5])
            more = f" *(+{len(names) - 5} more)*" if len(names) > 5 else ""
            cat_lines.append(f"- **{label}**: {sample}{more}")

        msg = (
            f"RiftShell currently has **{primary_count} commands** (and **{total} aliases**) registered across {len(categories)} categories:\n\n"
            + "\n".join(cat_lines)
            + "\n\n💡 *Tip: Run `help` in the terminal or press **Ctrl+K** to open the interactive Command Explorer.*"
        )
        return msg

    def get_command_list_summary(self, category: str | None = None) -> str:
        """Generates a structured category breakdown of available commands."""
        return self.get_command_count_summary()

    def is_task_feasibility_query(self, query: str) -> bool:
        """Determines if the user query is asking about capabilities, feasibility, count, or guidance."""
        if self.is_command_count_query(query) or self.is_command_list_query(query):
            return True
        text = query.strip().lower()
        patterns = [
            r"\bkya\b.*?(?:ho\s+sakta|ho\s+skta|kar\s+sakt|sakta\s+hu|sakte\s+hai|sakti\s+hai)",
            r"kya\s+(?:riftshell|ai|shell|terminal)\s+(?:me|mein|se)\b",
            r"\b(?:can\s+(?:i|we|riftshell)|is\s+it\s+possible\s+to|can\s+this\s+be\s+done)\b",
            r"\bcan\s+you\s+(?:run|open|execute|automate|download|compress|kill|launch|search|play|record)\b",
            r"\b(?:how\s+(?:can\s+i|do\s+i|to)|how\s+would\s+i)\b",
            r"\b(?:is\s+there\s+a\s+command|what\s+command\s+(?:can|should)|which\s+command)\b",
            r"\b(?:recommend|suggest)\s+(?:a\s+)?command\b",
            r"mujhe\s+.+?\s+(?:karna\s+hai|karni\s+hai|chahiye|dhundhna\s+hai|chalaana\s+hai)",
            r"\b(?:kaise\s+kare|kaise\s+hoga|kaise\s+karu)\b",
            r"\b(?:what\s+can\s+(?:you|riftshell)\s+do)\b",
            r"\b(?:capabilities|features|tools\s+available)\b",
            r"\b(?:what\s+tools|which\s+tools)\b",
        ]
        return any(re.search(pat, text, re.IGNORECASE) for pat in patterns)

    def search_capabilities(self, query: str, top_k: int = 4) -> list[tuple[CommandKnowledgeProfile, float, str]]:
        """Search commands matching a task description or capability request.

        Returns list of (profile, score, match_reason).
        """
        raw_text = query.lower()
        tokens = set(re.findall(r"\b[a-z0-9_-]+\b", raw_text))
        scored: list[tuple[CommandKnowledgeProfile, float, str]] = []

        # Check Hindi keyword triggers and semantic intent boosters
        bonus_commands: set[str] = set()
        for h_word, target_cmds in HINDI_TASK_KEYWORDS.items():
            if h_word in raw_text:
                bonus_commands.update(target_cmds)

        if re.search(r"\b(?:inside|content|text\s+in|grep)\b", raw_text):
            bonus_commands.add("findtext")
        if re.search(r"\b(?:compress|archive|backup|bundle)\b", raw_text):
            bonus_commands.add("zip")
        if re.search(r"\b(?:extract|uncompress|unpack)\b", raw_text):
            bonus_commands.add("unzip")
        if re.search(r"\b(?:listen|stream|youtube|gaana|song|lofi|play)\b", raw_text):
            bonus_commands.add("browser")

        for profile in self._profiles.values():
            score = 0.0
            reasons = []

            # 1. Exact name or alias
            if profile.name in tokens:
                if profile.name not in COMMON_STOPWORD_COMMANDS or re.search(rf"\b(?:command\s+{profile.name}|{profile.name}\s+command)\b", raw_text):
                    score += 8.0
                    reasons.append(f"Command name '{profile.name}' mentioned")
            for alias in profile.aliases:
                if alias in tokens and (alias not in COMMON_STOPWORD_COMMANDS or re.search(rf"\b(?:alias\s+{alias}|{alias}\s+alias)\b", raw_text)):
                    score += 6.0
                    reasons.append(f"Alias '{alias}' mentioned")

            # 2. Hindi keyword association
            if profile.name in bonus_commands:
                score += 5.0
                reasons.append("Matched natural intent keyword")

            # 3. Tags match
            matched_tags = tokens.intersection(set(profile.tags))
            if matched_tags:
                score += len(matched_tags) * 3.0
                reasons.append(f"Matched tags: {', '.join(matched_tags)}")

            # 4. Capability text substring / token match
            for cap in profile.capabilities:
                cap_lower = cap.lower()
                shared = tokens.intersection(set(re.findall(r"\b[a-z0-9_-]+\b", cap_lower)))
                if shared:
                    score += len(shared) * 1.5
                    reasons.append(f"Capability keyword: {', '.join(shared)}")

            # 5. Example phrase similarity
            for user_phrase, _ in profile.examples:
                phrase_tokens = set(re.findall(r"\b[a-z0-9_-]+\b", user_phrase.lower()))
                common = tokens.intersection(phrase_tokens)
                if len(common) >= 2:
                    score += len(common) * 2.0
                    reasons.append(f"Similar example query: '{user_phrase}'")

            # 6. Description match
            desc_tokens = set(re.findall(r"\b[a-z0-9_-]+\b", profile.description.lower()))
            desc_common = tokens.intersection(desc_tokens)
            if desc_common:
                score += len(desc_common) * 1.0

            if score > 0:
                scored.append((profile, score, "; ".join(reasons[:2])))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def get_prompt_knowledge_snippet(self, query: str, max_tokens: int = 400) -> str:
        """Formats matched capabilities into a concise snippet for dynamic prompt injection."""
        if self.is_command_count_query(query) or self.is_command_list_query(query):
            total = len(self._profiles)
            return (
                f"RiftShell Command Knowledge:\n"
                f"- Total commands and aliases: {total}\n"
                f"- Main categories: Files & Navigation (`files`, `cd`), System (`open`, `kill`), Browser (`browser`, `download`), Git (`gstatus`, `gadd`), Text & Utilities (`note`, `calc`, `hash`).\n"
                f"- INSTRUCTION: Provide a BRIEF, concise answer under 80 words. State total count and 3-4 key categories. Do NOT list all individual commands."
            )

        matches = self.search_capabilities(query, top_k=3)
        if not matches:
            # Fallback to key essential commands if search yielded no specific match
            essentials = [self.get_profile(name) for name in ("open", "browser", "files", "findtext") if self.get_profile(name)]
            matches = [(p, 1.0, "Core capability") for p in essentials if p]

        lines = ["Verified RiftShell Command Capabilities (Answer briefly, under 80 words):"]
        for profile, score, reason in matches:
            cap_text = profile.capabilities[0] if profile.capabilities else profile.description
            controls_text = " | ".join(profile.controls[:2]) if profile.controls else profile.usage
            lines.append(f"- Command: `{profile.name}` (Category: {profile.category})")
            lines.append(f"  • Usage: `{profile.usage}`")
            lines.append(f"  • Capability: {cap_text}")
            if len(profile.controls) > 1 or "->" in controls_text:
                lines.append(f"  • Controls: {controls_text}")
            if profile.notes:
                lines.append(f"  • Note: {profile.notes}")

        return "\n".join(lines)

    def formulate_guidance(self, query: str) -> str:
        """Formulates an offline conversational guide answering the user's task feasibility inquiry."""
        if self.is_command_count_query(query):
            return self.get_command_count_summary(brief=True)
        if self.is_command_list_query(query):
            return self.get_command_list_summary()

        matches = self.search_capabilities(query, top_k=2)
        if not matches:
            return (
                "Yes, RiftShell has comprehensive commands for system automation, web browsing, file management, "
                "and native execution. Run `help` in the terminal or press **Ctrl+K** to explore all commands, or specify your task details."
            )

        top_profile, score, reason = matches[0]
        cap_text = top_profile.capabilities[0] if top_profile.capabilities else top_profile.description
        lines = [
            f"Yes, this task can be accomplished directly in RiftShell using the `{top_profile.name}` command!\n",
            f"**Recommended Command**: `{top_profile.usage}`",
            f"**What it does**: {cap_text}",
        ]

        if top_profile.examples:
            ex_q, ex_cmd = top_profile.examples[0]
            lines.append(f"• **Example**: `{ex_cmd}`")

        if top_profile.notes:
            lines.append(f"• **Tip**: {top_profile.notes}")

        if len(matches) > 1 and matches[1][1] >= 5.0:
            second_profile = matches[1][0]
            lines.append(f"\n*Alternative*: `{second_profile.name}` (`{second_profile.usage}`)")

        lines.append("\n" + ACTION_OFFER)
        return "\n".join(lines)
