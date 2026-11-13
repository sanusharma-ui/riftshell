"""command_hints.py - Single source of truth for command examples, notes, and AI awareness.

This module provides rich examples, disambiguation notes, and prompt catalog
formatting for all RiftShell commands so the AI recognizes and executes them.
"""
from __future__ import annotations

from typing import Any

# --------------------------------------------------------------------------
# Per-command hints:
#   examples = list of (user phrase, exact command line)
#   note = disambiguation text shown to the model
# --------------------------------------------------------------------------
HINTS: dict[str, dict[str, Any]] = {
    # ---------- Navigation ----------
    "where": {
        "examples": [("where am i", "where"), ("show current location", "where"), ("mai abhi kis jagah par hu?", "where"), ("current directory", "where")],
        "note": "Shows the CURRENT FOLDER only. To find where a program/exe is installed use 'which'.",
    },
    "files": {
        "examples": [("list files", "files"), ("show everything in this folder", "files"), ("yahan kya kya rakha hai?", "files"), ("show files and folders", "files")],
        "note": "Files AND folders. For folders only use 'folders'.",
    },
    "folders": {
        "examples": [("show folders", "folders"), ("list only folders", "folders"), ("sirf dibbe dikha, files nahi", "folders")],
        "note": "Lists subdirectories only (no files).",
    },
    "cd": {
        "examples": [("go to the d drive", "cd D:\\"), ("change directory to c drive", "cd C:\\"), ("go into the test folder", "cd test"), ("d drive me jaao", "cd D:\\")],
        "note": "Takes a plain path or drive (e.g. cd D:\\ or cd src). 'goto' is an alias of cd.",
    },
    "goto": {
        "examples": [("goto D:\\", "goto D:\\"), ("navigate to src", "goto src")],
        "note": "Alias of cd. Changes directory or drive.",
    },
    "up": {
        "examples": [("go up one folder", "up"), ("go to parent folder", "up"), ("ek level upar chal", "up")],
        "note": "Navigates to parent directory (equivalent to cd ..).",
    },
    "home": {
        "examples": [("go to home directory", "home"), ("take me home", "home"), ("mere user wale ghar folder me le chal", "home")],
        "note": "Navigates to the user's home profile directory.",
    },
    "drives": {
        "examples": [("list all drives", "drives"), ("show drives", "drives"), ("is PC me kaun kaun si drives lagi hain?", "drives")],
        "note": "Lists all storage drives attached to this computer.",
    },
    "tree": {
        "examples": [("show folder tree", "tree"), ("directory hierarchy", "tree"), ("poora folder ka structure ek nazar me dikha", "tree"), ("show folder tree, depth 2", "tree 2")],
        "note": "Visualizes directory hierarchy. Optional depth argument.",
    },

    # ---------- Files & folders ----------
    "makefolder": {
        "examples": [("create a folder named test", "makefolder test"), ("make a folder assignments", "makefolder assignments"), ("assignments rakhne ki jagah chahiye", "makefolder assignments")],
        "note": "Creates a new folder/directory.",
    },
    "makefile": {
        "examples": [("create empty file a.txt", "makefile a.txt"), ("make empty file notes.txt", "makefile notes.txt"), ("ek khali notes wali file chahiye, naam notes.txt", "makefile notes.txt")],
        "note": "Creates a blank/empty file.",
    },
    "read": {
        "examples": [("read file notes.txt", "read notes.txt"), ("show contents of notes.txt", "read notes.txt"), ("notes.txt me kya likha hai bata", "read notes.txt")],
        "note": "Prints the file text in the terminal. To open in GUI app use 'open'.",
    },
    "open": {
        "examples": [("open notes.txt", "open notes.txt"), ("launch this file in default app", "open notes.txt"), ("notes.txt ko apne aap khol de screen par", "open notes.txt")],
        "note": "Opens the file in the default Windows application (Notepad, browser, etc.).",
    },
    "duplicate": {
        "examples": [("copy notes.txt to backup.txt", "duplicate notes.txt backup.txt"), ("duplicate notes.txt backup.txt", "duplicate notes.txt backup.txt"), ("notes.txt ki ek nakal backup.txt naam se bana", "duplicate notes.txt backup.txt")],
        "note": "Copies a file or folder. Syntax: duplicate <source> <target>.",
    },
    "shift": {
        "examples": [("move backup.txt to Docs", "shift backup.txt Docs"), ("shift notes.txt archive", "shift notes.txt archive"), ("backup.txt ko Docs folder me daal de", "shift backup.txt Docs")],
        "note": "Moves a file or folder to a new location. Syntax: shift <source> <destination>.",
    },
    "rename": {
        "examples": [("rename notes.txt to todo.txt", "rename notes.txt todo.txt"), ("change filename a.txt to b.txt", "rename a.txt b.txt"), ("notes.txt ka naam badal ke todo.txt kar", "rename notes.txt todo.txt")],
        "note": "Renames a file or folder. Syntax: rename <old> <new>.",
    },
    "delete": {
        "examples": [("delete file todo.txt", "delete confirm todo.txt"), ("remove file test.txt", "delete confirm test.txt"), ("todo.txt ko hamesha ke liye hata de", "delete confirm todo.txt")],
        "note": "DESTRUCTIVE. Permanently removes files or folders. Use 'delete confirm <path>' after user confirms.",
    },
    "search": {
        "examples": [("search for files named report", "search report"), ("find file named config", "search config"), ("jis file ke naam me report hai wo dhundh", "search report")],
        "note": "Searches for file or folder NAMES. To search text inside files use 'findtext'.",
    },
    "findtext": {
        "examples": [("find text password in files", "findtext password"), ("grep password in files", "findtext password"), ("kis file ke andar 'password' likha hai?", "findtext password")],
        "note": "Searches for text content INSIDE files (grep equivalent).",
    },
    "head": {
        "examples": [("first 5 lines of a.txt", "head a.txt 5"), ("show top lines of file", "head a.txt 10"), ("file ki pehli 5 line dikha", "head a.txt 5")],
        "note": "Shows first N lines of a file (default 10). For piped output use 'take'.",
    },
    "tail": {
        "examples": [("last 20 lines of log.txt", "tail log.txt 20"), ("show end of log file", "tail log.txt 10"), ("file ke end ki 20 lines dikha", "tail log.txt 20")],
        "note": "Shows last N lines of a file (default 10).",
    },
    "wc": {
        "examples": [("count lines in a.txt", "wc a.txt"), ("word count of notes.txt", "wc notes.txt"), ("a.txt me kitne shabd hain", "wc a.txt")],
        "note": "Counts lines, words, and characters in a file. For piped output use 'count'.",
    },
    "zip": {
        "examples": [("compress Docs into docs.zip", "zip Docs docs.zip"), ("zip folder project project.zip", "zip project project.zip"), ("Docs folder ko chhota karke ek archive bana", "zip Docs docs.zip")],
        "note": "Compresses a file or directory into a zip archive. Syntax: zip <source> <target.zip>.",
    },
    "unzip": {
        "examples": [("unzip docs.zip", "unzip docs.zip"), ("extract archive project.zip", "unzip project.zip"), ("docs.zip ko khol ke andar ka saaman nikaal", "unzip docs.zip")],
        "note": "Extracts a zip archive. Syntax: unzip <archive> [<destination>].",
    },
    "save": {
        "examples": [("save last output to out.txt", "save out.txt"), ("save output result.txt", "save result.txt"), ("abhi jo output aaya use out.txt me rakh le", "save out.txt")],
        "note": "Saves the output of the previous command to a file.",
    },
    "last": {
        "examples": [("show previous output", "last"), ("print last output again", "last"), ("pichla output dobara dikha", "last")],
        "note": "Redisplays the output of the most recent terminal command.",
    },

    # ---------- System info ----------
    "today": {
        "examples": [("today's date", "today"), ("what is today's date", "today"), ("current date", "today"), ("aaj ki tareekh?", "today"), ("aaj kaun si date hai", "today")],
        "note": "Shows today's date. NEVER claim you don't have a clock — run 'today'.",
    },
    "now": {
        "examples": [("current time", "now"), ("what time is it", "now"), ("what is the time", "now"), ("abhi kitne baje hain?", "now"), ("time batao", "now")],
        "note": "Shows the current system time. NEVER claim you don't have a clock — run 'now'.",
    },
    "uptime": {
        "examples": [("system uptime", "uptime"), ("how long has the computer been running", "uptime"), ("PC kab se chalu hai?", "uptime")],
        "note": "Shows how long the system has been running since boot.",
    },
    "ip": {
        "examples": [("what is my ip address", "ip"), ("show ip", "ip"), ("mera IP address kya hai?", "ip"), ("show network config", "ip")],
        "note": "Shows the local IP address and network configuration.",
    },
    "network": {
        "examples": [("show network info", "network"), ("network details", "network"), ("network ki detail dikha", "network")],
        "note": "Shows detailed network adapter information.",
    },
    "netstat": {
        "examples": [("active connections", "netstat"), ("show open ports", "netstat"), ("kaun se ports khule hain?", "netstat"), ("network connections", "netstat")],
        "note": "Shows active TCP/UDP network connections and listening ports.",
    },
    "ping": {
        "examples": [("ping google.com", "ping google.com"), ("check if google is reachable", "ping google.com"), ("check kar google chal raha hai ya nahi", "ping google.com")],
        "note": "Tests network connectivity to a host or IP. Syntax: ping <host>.",
    },
    "processes": {
        "examples": [("list running processes", "processes"), ("show running tasks", "processes"), ("abhi kaun kaun se programs chal rahe hain?", "processes")],
        "note": "Lists active processes with CPU and memory usage.",
    },
    "system": {
        "examples": [("system info", "system"), ("full system info", "system"), ("computer specifications", "system"), ("PC ki poori detail (OS, build) bata", "system")],
        "note": "Shows detailed OS, architecture, processor, and system information.",
    },
    "me": {
        "examples": [("who am i", "me"), ("current user", "me"), ("what is my username", "me"), ("main kaun sa user hu?", "me")],
        "note": "Shows the currently signed-in user.",
    },
    "pc": {
        "examples": [("pc name", "pc"), ("show hostname", "pc"), ("computer name", "pc"), ("is computer ka naam kya hai?", "pc")],
        "note": "Shows the machine/computer hostname.",
    },
    "env": {
        "examples": [("show env vars", "env"), ("list environment variables", "env"), ("saare environment variables dikha", "env")],
        "note": "Lists all environment variables.",
    },
    "path": {
        "examples": [("show PATH", "path"), ("what is in PATH", "path"), ("PATH me kya kya set hai?", "path")],
        "note": "Shows the executable PATH entries line by line.",
    },
    "version": {
        "examples": [("shell version", "version"), ("which version of riftshell", "version"), ("ye shell ka konsa version hai?", "version")],
        "note": "Shows the RiftShell and Python versions.",
    },
    "update": {
        "examples": [("check for updates", "update"), ("RiftShell ka naya version check kar", "update"), ("update riftshell", "update")],
        "note": "Checks for a newer version of RiftShell and prompts to install it. 'upgrade' is an alias.",
    },
    "disk": {
        "examples": [("how much disk space is left", "disk"), ("disk usage of D:", "disk D:\\"), ("C drive me kitni jagah bachi?", "disk C:\\")],
        "note": "Shows free and used disk space for a drive or directory.",
    },
    "memory": {
        "examples": [("show RAM usage", "memory"), ("memory usage", "memory"), ("RAM kitni bachi hai?", "memory"), ("check memory", "memory")],
        "note": "Shows current RAM / physical memory consumption.",
    },
    "which": {
        "examples": [("where is python installed", "which python"), ("which chrome", "which chrome"), ("python ka exe kahan rakha hai?", "which python"), ("full path of python", "which python")],
        "note": "Finds the full executable path of a program. NOT 'where'.",
    },
    "kill": {
        "examples": [("kill process notepad.exe", "kill notepad.exe"), ("terminate chrome.exe", "kill chrome.exe"), ("notepad zabardasti band kar de", "kill notepad.exe")],
        "note": "DESTRUCTIVE. Terminates a running process. Syntax: kill <process.exe>.",
    },

    # ---------- Utilities ----------
    "calc": {
        "examples": [("calc 25*4+10", "calc 25*4+10"), ("calculate 2 to the power 10", "calc 2**10"), ("25 ko 4 se guna karke 10 jod de", "calc 25*4+10")],
        "note": "Evaluates math expressions safely. Use ** for exponent.",
    },
    "random": {
        "examples": [("roll a dice", "random 1 6"), ("pick a random number between 1 and 50", "random 1 50"), ("ek lucky number de 1 se 50 ke beech", "random 1 50")],
        "note": "Generates a random integer. Syntax: random <min> <max>.",
    },
    "hash": {
        "examples": [("sha256 of file a.txt", "hash file a.txt"), ("hash text hello", "hash text hello"), ("ye text 'hello' ka fingerprint nikaal", "hash text hello")],
        "note": "Calculates SHA256. Syntax: hash text <string> OR hash file <path>.",
    },
    "base64": {
        "examples": [("base64 encode hello", "base64 encode hello"), ("decode aGVsbG8=", "base64 decode aGVsbG8="), ("'hello' ko encode kar", "base64 encode hello")],
        "note": "Base64 encodes or decodes a string. Syntax: base64 [encode|decode] <text>.",
    },
    "download": {
        "examples": [("download https://example.com/a.zip", "download https://example.com/a.zip"), ("download https://example.com/a.zip as x.zip", "download https://example.com/a.zip x.zip")],
        "note": "Downloads a file from a URL. Syntax: download <url> [<filename>].",
    },
    "sleep": {
        "examples": [("wait 3 seconds", "sleep 3"), ("pause for 5 seconds", "sleep 5"), ("3 second ruk ja", "sleep 3")],
        "note": "Pauses execution for N seconds.",
    },
    "echo": {
        "examples": [("print hello world", "echo hello world"), ("echo test", "echo test"), ("screen par 'namaste' likh de", "echo namaste")],
        "note": "Prints text to the console, expanding shell variables like $name.",
    },
    "history": {
        "examples": [("show command history", "history"), ("command history", "history"), ("maine abhi tak kya kya chalaya?", "history")],
        "note": "Displays past commands executed in this session.",
    },
    "clear": {
        "examples": [("clear the terminal", "clear"), ("clear screen", "clear"), ("screen saaf kar", "clear")],
        "note": "Clears the active terminal panel.",
    },
    "help": {
        "examples": [("show all commands", "help"), ("what commands are available", "help"), ("mujhe kaun kaun se commands milte hain?", "help")],
        "note": "Lists all available commands and their descriptions.",
    },
    "theme": {
        "examples": [("list themes", "theme list"), ("change theme to cyber", "theme cyber"), ("colour scheme badal de", "theme list")],
        "note": "Lists or changes UI themes.",
    },
    "plugins": {
        "examples": [("show plugins", "plugins"), ("plugin status", "plugins"), ("kaun se plugins load hue?", "plugins")],
        "note": "Lists loaded plugins and their commands.",
    },
    "exit": {
        "examples": [("quit shell", "exit"), ("close terminal", "exit"), ("bas, band kar do shell", "exit")],
        "note": "Exits the RiftShell application.",
    },

    # ---------- Text pipeline (works on piped / last output) ----------
    "filter": {
        "examples": [("filter lines with txt", "filter txt"), ("keep only lines with error", "filter error"), ("is output me se sirf 'txt' wali lines rakh", "filter txt")],
        "note": "Filters lines containing a search term from piped or last output.",
    },
    "sort": {
        "examples": [("sort these lines", "sort"), ("sort lines alphabetically", "sort"), ("in lines ko A-Z order me laga", "sort")],
        "note": "Sorts lines alphabetically.",
    },
    "unique": {
        "examples": [("remove duplicate lines", "unique"), ("unique lines only", "unique"), ("repeat wali lines hata de", "unique")],
        "note": "Removes duplicate adjacent lines from output.",
    },
    "take": {
        "examples": [("keep only first 3 lines", "take 3"), ("take top 5 lines", "take 5"), ("sirf upar ki 3 lines chahiye", "take 3")],
        "note": "Keeps first N lines of piped/last output. For a file use 'head'.",
    },
    "skip": {
        "examples": [("skip first 2 lines", "skip 2"), ("omit first line", "skip 1"), ("pehli 2 lines chhod ke baaki dikha", "skip 2")],
        "note": "Skips first N lines of output and shows the rest.",
    },
    "count": {
        "examples": [("count lines in last output", "count"), ("how many lines in this output", "count"), ("is output me total kitni lines hain?", "count")],
        "note": "Counts lines of piped or last output. For a file use 'wc'.",
    },

    # ---------- Variables, alias, native ----------
    "setvar": {
        "examples": [("set variable city to Nagpur", "setvar city Nagpur"), ("setvar name Rahul", "setvar name Rahul")],
        "note": "Sets a shell session variable. Syntax: setvar <name> <value>.",
    },
    "vars": {
        "examples": [("show shell variables", "vars"), ("list variables", "vars"), ("jo variables set kiye wo dikha", "vars")],
        "note": "Lists all defined shell session variables.",
    },
    "unsetvar": {
        "examples": [("remove variable name", "unsetvar name"), ("unsetvar city", "unsetvar city")],
        "note": "Removes a shell session variable.",
    },
    "alias": {
        "examples": [("create alias ll for files", "alias ll files"), ("alias st gstatus", "alias st gstatus")],
        "note": "Creates a command alias / shortcut. Syntax: alias <alias_name> <command>.",
    },
    "unalias": {
        "examples": [("remove alias ll", "unalias ll"), ("unalias st", "unalias st")],
        "note": "Removes a command alias.",
    },
    "run": {
        "examples": [("run git status", "run git status"), ("run python main.py", "run python main.py"), ("git status chala (native command)", "run git status")],
        "note": "Runs an external CLI command or native program.",
    },

    # ---------- Git commands ----------
    "gstatus": {
        "examples": [("git status", "gstatus"), ("show git status", "gstatus"), ("git repository status", "gstatus")],
        "note": "Shows Git working tree status.",
    },
    "gbranch": {
        "examples": [("git branches", "gbranch"), ("list git branches", "gbranch"), ("which git branch am i on", "gbranch")],
        "note": "Lists Git branches.",
    },
    "glog": {
        "examples": [("git log", "glog"), ("show git commits", "glog"), ("recent commits", "glog")],
        "note": "Shows recent Git commit history.",
    },
    "gdiff": {
        "examples": [("git diff", "gdiff"), ("show unstaged changes", "gdiff"), ("git differences", "gdiff")],
        "note": "Shows unstaged Git differences.",
    },
    "gpull": {
        "examples": [("git pull", "gpull"), ("pull updates from remote", "gpull")],
        "note": "Pulls changes from remote Git repository.",
    },
    "gpush": {
        "examples": [("git push", "gpush"), ("push commits to remote", "gpush")],
        "note": "Pushes local commits to remote Git repository.",
    },
    "gremote": {
        "examples": [("git remotes", "gremote"), ("list git remotes", "gremote")],
        "note": "Lists configured Git remote repositories.",
    },
    "gadd": {
        "examples": [("git add all", "gadd ."), ("stage all files", "gadd ."), ("git add main.py", "gadd main.py")],
        "note": "Stages files in Git. Syntax: gadd <path>.",
    },
    "gcommit": {
        "examples": [("git commit -m initial commit", "gcommit initial commit"), ("commit changes", "gcommit update")],
        "note": "Commits staged Git changes. Syntax: gcommit <message>.",
    },
    "gcheckout": {
        "examples": [("git checkout main", "gcheckout main"), ("switch to branch dev", "gcheckout dev")],
        "note": "Switches Git branches. Syntax: gcheckout <branch>.",
    },
    "hello": {
        "examples": [("run hello plugin", "hello"), ("test hello plugin", "hello")],
        "note": "Sample plugin command.",
    },
}


def get_hint(command_name: str) -> dict[str, Any]:
    """Retrieve hint dictionary for a command, or empty dict if not defined."""
    return HINTS.get(command_name, {})


def format_command_catalog_entry(meta: Any) -> str:
    """Format a single command entry for the AI prompt catalog with examples and notes."""
    hint = get_hint(meta.name)
    aliases_str = f" (aliases: {', '.join(meta.aliases)})" if getattr(meta, "aliases", None) else ""
    usage_str = f" | usage: {meta.usage}" if getattr(meta, "usage", None) and meta.usage != meta.name else ""
    desc = getattr(meta, "description", "").strip()

    examples = hint.get("examples", [])
    ex_text = ""
    if examples:
        phrases = [f'"{p}"' for p, _ in examples[:2]]
        ex_text = f" | e.g. {', '.join(phrases)}"

    note = hint.get("note", "")
    note_text = f" | NOTE: {note}" if note else ""

    return f"- {meta.name}{aliases_str}{usage_str} - {desc}{ex_text}{note_text}".strip()
