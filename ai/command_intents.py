"""English-first, opt-in command grammars with common Romanized Hindi forms.

Add declarations here (or to registry metadata); keep inference in
command_intent.py. Full matches deliberately leave unfamiliar wording to Orbit.
"""
from ai.command_intent import IntentRule


# One literal argument. Multiword targets must be quoted to avoid swallowing
# extra instructions or silently choosing the first word as a filename.
ATOM = r'''(?:"[^"\r\n]+"|'[^'\r\n]+'|[^\s"']+)'''
TARGET = rf"(?P<target>{ATOM})"
SOURCE = rf"(?P<source>{ATOM})"
DEST = rf"(?P<destination>{ATOM})"
SHOW = r"(?:show|list|display)(?:\s+me)?\s+(?:the\s+|all\s+)?"
HERE = r"(?:\s+(?:in|of)\s+(?:this|the current|my current|current)\s+(?:folder|directory))?"
HSHOW = r"(?:dikhao|dikha\s+do|dikhaao|batao|show\s+karo|list\s+karo)"


def fixed(command, message, phrases=(), patterns=(), starts=()):
    return IntentRule(command, command, message, tuple(phrases), tuple(patterns), tuple(starts))


def target_rule(intent, command, message, patterns, starts=(), arguments=("{target}",)):
    return IntentRule(intent, command, message, patterns=tuple(patterns), starts=tuple(starts),
                      arguments=arguments, slots=(("target", "path"),))


BUILTIN_INTENTS = (
    fixed("where", "I will show the current workspace directory.", (
        "where am i", "where are we", "where we are", "current directory", "current folder",
        "working directory", "what folder am i in", "what directory am i in",
        "what is my current directory", "what is the current directory", "show my location",
        "hum kis folder mein hain", "hum kis folder me hai", "abhi kis folder mein hain",
        "abhi kaunsa folder hai", "current folder batao", "current directory batao",
    ), (r"(?:show|display|tell)(?:\s+me)?\s+(?:(?:the|my)\s+)?(?:current|working)\s+(?:directory|folder|location)[?!.]?",),
       ("show", "display", "tell")),
    fixed("files", "I will list the files and folders in the current directory.", (
        "what files are here", "what is in this folder", "what's in this folder",
        "show folder contents", "list folder contents", "files dikhao", "files dikha do",
        "saari files dikhao", "sab files dikhao", "is folder ki files dikhao",
        "current folder ki files dikhao", "mujhe files dikhao",
    ), (rf"{SHOW}files{HERE}[?!.]?",), ("show", "list", "display")),
    fixed("folders", "I will list the folders in the current directory.", (
        "only folders", "folders dikhao", "directories dikhao", "sirf folders dikhao",
    ), (rf"{SHOW}(?:folders|directories){HERE}[?!.]?",), ("show", "list", "display")),
    fixed("up", "I will move to the parent directory.", (
        "go up", "go up one level", "go to the parent folder", "go to parent folder",
        "go to the parent directory", "move up one directory", "ek folder upar jao",
        "parent folder mein jao", "parent folder me jao",
    )),
    fixed("home", "I will change this session to your home directory.", (
        "go home", "go to home folder", "go to my home folder", "go to my home directory",
        "home folder mein jao", "home folder me jao",
    )),
    fixed("clear", "I will clear the active terminal.", (
        "clear terminal", "clear the terminal", "clear the screen", "clear screen",
        "clear the console", "terminal saaf karo", "screen saaf karo", "terminal clear karo",
    )),
    fixed("help", "I will show the available RiftShell commands.", (
        "show commands", "list commands", "show all commands", "list available commands",
        "show available commands", "commands dikhao", "saare commands dikhao",
    )),
    fixed("tree", "I will show the directory tree.", (
        "show directory tree", "show the directory tree", "show folder tree",
        "show the folder tree", "folder tree dikhao",
    )),
    *(
        fixed(command, message, phrases,
              (rf"{SHOW}(?:{english})[?!.]?", rf"(?:{hinglish})\s+{HSHOW}[?!.]?"), starts)
        for command, message, phrases, english, hinglish, starts in (
            ("processes", "I will show the running processes.", ("what is running",),
             r"(?:running\s+)?(?:processes|tasks)", r"(?:running\s+)?processes", ("show", "list", "display", "processes", "running")),
            ("system", "I will show system information.", ("system info", "system information"),
             r"system\s+(?:info|information|details)", r"system\s+(?:info|details)", ("show", "list", "display", "system")),
            ("memory", "I will show current memory usage.", ("ram usage", "memory usage"),
             r"(?:ram|memory)\s+usage", r"(?:ram|memory)(?:\s+usage)?", ("show", "list", "display", "ram", "memory")),
            ("disk", "I will show disk space for the current directory.", ("disk space", "disk usage"),
             r"(?:disk|free\s+disk)\s+(?:space|usage)", r"disk\s+(?:space|usage)", ("show", "list", "display", "disk")),
            ("drives", "I will show the available drives.", (), r"(?:available\s+)?drives", r"drives", ("show", "list", "display", "drives")),
            ("ip", "I will show the IP configuration.", ("what is my ip address",),
             r"(?:my\s+)?ip(?:\s+(?:address|configuration))?", r"ip(?:\s+address)?", ("show", "list", "display", "ip")),
            ("network", "I will show network information.", (), r"network\s+(?:info|information)", r"network\s+info", ("show", "list", "display", "network")),
            ("netstat", "I will show network connections.", (), r"(?:active|network)\s+connections", r"network\s+connections", ("show", "list", "display", "network")),
            ("history", "I will show this terminal's command history.", (), r"(?:command\s+|terminal\s+)?history", r"(?:command\s+)?history", ("show", "list", "display", "command", "history")),
            ("now", "I will show the current time.", ("what time is it", "abhi kitne baje hain"), r"(?:current\s+)?time", r"(?:current\s+)?time", ("show", "list", "display", "time", "current")),
            ("today", "I will show today's date.", ("what is today's date", "aaj ki date batao"), r"(?:current\s+|today's\s+)?date", r"date", ("show", "list", "display", "date")),
            ("me", "I will show the signed-in user.", ("who am i",), r"(?:current\s+user|my\s+username)", r"current\s+user", ("show", "list", "display", "current")),
            ("pc", "I will show the computer name.", (), r"(?:computer|pc|machine)\s+name", r"(?:computer|pc)\s+name", ("show", "list", "display", "computer", "pc")),
            ("uptime", "I will show the system uptime.", ("how long has the computer been on",), r"(?:system\s+)?uptime", r"uptime", ("show", "list", "display", "uptime")),
            ("plugins", "I will show the installed plugin status.", (), r"(?:installed\s+)?plugins", r"plugins", ("show", "list", "display", "plugins")),
            ("version", "I will show the RiftShell version.", (), r"(?:shell\s+|riftshell\s+)?version", r"(?:shell\s+)?version", ("show", "list", "display", "shell", "version")),
        )
    ),
    *(
        fixed(command, message, (f"git {noun}", f"show git {noun}", f"show the git {noun}",
                                 f"git {noun} dikhao", f"git {noun} batao"))
        for command, noun, message in (
            ("gstatus", "status", "I will show the Git working tree status."),
            ("gbranch", "branches", "I will show the Git branches."),
            ("glog", "log", "I will show the recent Git commit history."),
            ("gdiff", "diff", "I will show the unstaged Git changes."),
            ("gremote", "remotes", "I will show the Git remotes."),
        )
    ),
    target_rule("navigate", "cd", "I will change this session to the requested directory.", (
        rf"(?:go|navigate|switch)\s+to\s+(?:the\s+)?(?:folder\s+|directory\s+)?{TARGET}",
        rf"change\s+(?:directory|folder)\s+to\s+{TARGET}",
        rf"{TARGET}\s+(?:folder\s+)?(?:mein|me)\s+(?:jao|chalo)",
    )),
    target_rule("list_path", "files", "I will list files in the requested directory.", (
        rf"{SHOW}files\s+(?:in|inside)\s+(?:the\s+)?(?:folder\s+|directory\s+)?{TARGET}",
        rf"{TARGET}\s+(?:folder\s+)?ki\s+files\s+{HSHOW}",
    )),
    target_rule("create_folder", "makefolder", "I will create the requested folder.", (
        rf"(?:create|make)\s+(?:a\s+|the\s+)?(?:folder|directory)\s+(?:(?:named|called)\s+)?{TARGET}",
        rf"{TARGET}\s+(?:naam\s+ka\s+)?folder\s+(?:banao|bana\s+do|create\s+karo)",
    )),
    target_rule("create_empty_file", "makefile", "I will create the requested empty file.", (
        rf"(?:create|make)\s+(?:an?\s+|the\s+)?(?:empty\s+|blank\s+)?file\s+(?:(?:named|called)\s+)?{TARGET}",
        rf"{TARGET}\s+(?:naam\s+ki\s+)?(?:empty\s+|khali\s+)?file\s+(?:banao|bana\s+do)",
    )),
    target_rule("delete_path", "delete", "I will delete the requested item after your approval.", (
        rf"(?:delete|remove)\s+(?:the\s+)?(?:file|folder|directory)\s+{TARGET}",
        rf"{TARGET}\s+(?:file|folder)\s+(?:delete\s+karo|delete\s+kar\s+do|hata\s+do)",
    ), arguments=("confirm", "{target}")),
    *(
        IntentRule(intent, command, message, patterns=(rf"{verb}\s+{TARGET}",),
                   starts=starts, arguments=arguments, slots=(("target", "file_path"),))
        for intent, command, verb, starts, arguments, message in (
            ("delete_named_path", "delete", r"(?:delete|remove)", ("delete", "remove"), ("confirm", "{target}"),
             "I will delete the requested item after your approval."),
            ("open_named_path", "open", r"(?:open|launch)", ("open", "launch"), ("{target}",),
             "I will open the requested file or folder."),
        )
    ),
    *(
        IntentRule(intent, command, message, patterns=(
            rf"{verb}\s+(?:the\s+)?(?:file\s+|folder\s+)?{SOURCE}\s+{prep}\s+{DEST}",
            rf"{SOURCE}\s+ko\s+{DEST}\s+(?:mein\s+|me\s+)?{hverb}\s+karo",
        ), arguments=("{source}", "{destination}"), slots=(("source", "path"), ("destination", "path")))
        for intent, command, verb, prep, hverb, message in (
            ("copy_path", "duplicate", r"(?:copy|duplicate)", r"(?:to|into)", "copy", "I will copy the requested item."),
            ("move_path", "shift", r"(?:move|shift)", r"(?:to|into)", "move", "I will move the requested item after your approval."),
            ("rename_path", "rename", "rename", r"(?:to|as)", "rename", "I will rename the requested item after your approval."),
        )
    ),
    *(
        IntentRule(f"{command}_lines", command, message, patterns=(
            rf"(?:show|display)\s+(?:the\s+)?{which}\s+(?P<lines>\d{{1,5}})\s+lines?\s+(?:of|from)\s+(?:file\s+)?{TARGET}",
        ), starts=("show", "display"), arguments=("{target}", "{lines}"), slots=(("target", "path"), ("lines", "integer")))
        for command, which, message in (
            ("head", "first", "I will show the first requested lines."),
            ("tail", "last", "I will show the last requested lines."),
        )
    ),
    IntentRule("ping_host", "ping", "I will ping the requested host.", patterns=(
        r"ping\s+(?P<host>[a-zA-Z0-9][a-zA-Z0-9.-]{0,252})",
    ), starts=("ping",), arguments=("{host}",), slots=(("host", "host"),)),
)
