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
SHOW = r"(?:show|list|display)(?:\s+me)?\s+(?:all\s+(?:the\s+)?|the\s+)?"
HERE = r"(?:\s+(?:here|right\s+here|(?:in|inside|of)\s+(?:this|the\s+current|my\s+current|current)\s+(?:folder|directory)))?"
HSHOW = r"(?:dikhao|dikha\s+do|dikhaao|batao|show\s+karo|list\s+karo)"
# Listing nouns are shared by current-directory and literal-path grammars.
# A conjunction is allowed only between these nouns, never between actions.
FILE_ITEMS = r"(?:files(?:\s+and\s+(?:folders|directories))?|(?:folders|directories)\s+and\s+files)"
FOLDER_ITEMS = r"(?:only\s+)?(?:folders|directories)"
HLIST = r"(?:mujhe\s+)?(?:(?:is|current)\s+(?:folder|directory)\s+(?:ki|ke)\s+)?(?:sab\s+|saare\s+|saari\s+|sare\s+|sari\s+)?"
# Unquoted Hinglish "is" means "this", not a literal directory named "is".
HLIST_TARGET = rf"(?!is\s){TARGET}"


THEMES_REGEX = r"(?:vscode-dark-plus|github-dark|midnight-aurora|ember-grove|default|horizon|violet|dark\+|dark-plus|vscode|vs-code|gh-dark|modern-dark|aurora|midnight|cyan-dark|neon|ember|grove|forest|orange-dark|warm|list|current)"


def fixed(command, message, phrases=(), patterns=(), starts=()):
    return IntentRule(command, command, message, tuple(phrases), tuple(patterns), tuple(starts))


def target_rule(intent, command, message, patterns, starts=(), arguments=("{target}",)):
    return IntentRule(intent, command, message, patterns=tuple(patterns), starts=tuple(starts),
                      arguments=arguments, slots=(("target", "path"),))


BUILTIN_INTENTS = (
    fixed("where", "I will show the current workspace directory.", (
        "where am i", "where are we", "where we are", "where are we now", "where am i right now",
        "current directory", "current folder", "working directory", "present working directory", "pwd",
        "what folder am i in", "what directory am i in", "which folder am i in", "which directory am i in",
        "what folder is this", "which folder is this", "what directory is this", "which directory is this",
        "what is this folder", "what is this directory", "what is my current directory", "what is the current directory",
        "what's my current directory", "what's the current directory", "what is my current folder", "what is the current folder",
        "what's my current folder", "what's the current folder", "show my location", "show current location",
        "my location", "current location", "where is this", "where are we now",
        "hum kis folder mein hain", "hum kis folder me hai", "hum kis directory me hai", "abhi kis folder mein hain",
        "abhi kaunsa folder hai", "current folder batao", "current directory batao",
        "kaha hai hm", "kaha hain hum", "hum kaha hai", "hm kaha hai", "kaha hu mai", "kaha hoon main",
        "kaha par hai hum", "hum kaha par hai", "kaha par hu mai", "kaha pe hai",
        "konse folder me hai hm", "konse folder me hu", "kis folder me hu", "kis folder me hai",
    ), (
        r"where\s+(?:am\s+i|are\s+we|we\s+are)(?:\s+(?:now|right\s+now))?[?!.]?",
        r"(?:what|which)\s+(?:(?:current\s+)?(?:directory|folder)(?:\s+is\s+this)?|is\s+(?:(?:my|the|this)\s+)?(?:current\s+)?(?:directory|folder)|(?:folder|directory)\s+(?:am\s+i|are\s+we|we\s+are)\s+(?:in|on))[?!.]?",
        r"(?:what\'s|whats)\s+(?:(?:my|the|this)\s+)?(?:current\s+)?(?:directory|folder)[?!.]?",
        r"(?:show|display|tell|give)(?:\s+me)?\s+(?:(?:the|my|this)\s+)?(?:current|working)?\s*(?:directory|folder|location)[?!.]?",
        r"(?:(?:hum|hm|mai|main|ab|abhi)\s+)?kah[a-z]*(?:\s+par|\s+pe)?\s+(?:hai|hain|hu|hoon)(?:\s+(?:hum|hm|mai|main))?[?!.]?",
        r"(?:(?:hum|hm|mai|main|ab|abhi)\s+)?k(?:on|is|aun)(?:se|sa)?\s+(?:folder|directory)(?:\s+me(?:in)?)?(?:\s+(?:hai|hain|hu|hoon))?(?:\s+(?:hum|hm|mai|main))?[?!.]?",
        r"(?:current|working|abhi\s+ka)\s+(?:folder|directory)\s+(?:batao|dikhao)[?!.]?",
    ), ("*",)),
    fixed("files", "I will list the files and folders in the current directory.", (
        "what files are here", "what is in this folder", "what's in this folder",
        "show folder contents", "list folder contents", "files dikhao", "files dikha do",
        "saari files dikhao", "sab files dikhao", "is folder ki files dikhao",
        "current folder ki files dikhao", "mujhe files dikhao",
    ), (rf"{SHOW}{FILE_ITEMS}{HERE}[?!.]?",
        rf"{HLIST}files\s+{HSHOW}[?!.]?"),
       ("show", "list", "display", "mujhe", "is", "current", "sab", "saare", "saari", "sare", "sari", "files")),
    fixed("folders", "I will list the folders in the current directory.", (
        "only folders", "folders dikhao", "directories dikhao", "sirf folders dikhao",
    ), (rf"{SHOW}{FOLDER_ITEMS}{HERE}[?!.]?",
        rf"{HLIST}(?:sirf\s+)?(?:folders|directories)\s+{HSHOW}[?!.]?"),
       ("show", "list", "display", "mujhe", "is", "current", "sab", "saare", "saari", "sare", "sari", "sirf", "folders", "directories")),
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
    fixed("theme", "I will show the available RiftShell themes.", (
        "find new themes", "help me to find new themes", "help me find new themes", "new themes",
        "themes", "theme", "show themes", "list themes", "available themes", "what themes are available",
        "which themes are available", "all themes", "show all themes", "list all themes",
        "riftshell themes", "riftshell theme", "terminal themes", "terminal theme", "shell themes", "shell theme",
        "theme list", "themes list", "themes dikhao", "theme dikhao", "saare themes dikhao",
        "mujhe themes dikhao", "theme batao", "konsi theme hai", "konsi themes hai",
        "current theme", "what is the current theme", "theme current", "active theme",
        "theme badlo", "theme badal do", "theme change karo", "change theme", "switch theme", "change the theme", "switch the theme",
    ), (
        r"(?:find|show|list|display|get|see|discover|check)(?:\s+(?:me|us))?(?:\s+(?:all\s+the|all|the))?\s+(?:new\s+|available\s+|riftshell\s+)?themes?[?!.]?",
        r"(?:what|which)\s+(?:riftshell\s+)?themes?(?:\s+(?:are\s+available|exist|do\s+we\s+have|can\s+i\s+use))[?!.]?",
        r"(?:riftshell|terminal|shell)\s+themes?[?!.]?",
        r"themes?(?:\s+(?:dikhao|batao|list\s+karo|badlo|change\s+karo))[?!.]?",
        r"(?:change|switch)\s+(?:the\s+)?theme[?!.]?",
    ), ("find", "show", "list", "display", "get", "see", "themes", "theme", "riftshell", "what", "which", "change", "switch", "*")),
    IntentRule(
        "theme_set",
        "theme",
        "I will switch to the requested theme.",
        patterns=(
            rf"(?:change|switch|set|apply)\s+(?:the\s+)?theme\s+(?:to\s+)?(?P<target>{THEMES_REGEX})",
            rf"theme\s+(?P<target>{THEMES_REGEX})",
            rf"(?P<target>{THEMES_REGEX})\s+theme(?:\s+(?:lagao|set\s+karo|apply\s+karo|badlo))?",
        ),
        starts=("change", "switch", "set", "apply", "theme", "*"),
        arguments=("{target}",),
        slots=(("target", "theme"),),
    ),
    fixed("drives", "I will show the available drives and storage disks.", (
        "list all drives", "show drives", "all drives", "available drives", "which drives are available",
        "show all drives", "list all drives", "check drives", "drives list", "drives",
        "how many disks are installed on my computer", "how many disks are installed on your computer",
        "how many disks are installed on this computer", "how many disks are installed",
        "how many disks do i have", "how many disks are there", "how many hard drives are installed",
        "how many drives are installed", "how many drives do i have", "how many drives are there",
        "installed disks", "installed drives", "connected disks", "connected drives",
        "storage drives", "storage devices", "disk drives", "hard drives", "hard disks",
        "show disks", "list disks", "show all disks", "list all disks", "check disks",
        "show connected disks", "how many storage drives", "show storage devices", "storage drives list",
        "kitne disk hai", "kitne disks hai", "kitne disk hain", "kitne disks hain",
        "kitne drive hai", "kitne drives hai", "kitne drives hain",
        "computer me kitne disk hai", "pc me kitne disk hai", "is pc me kitne disk hai", "laptop me kitne disk hai",
        "disks dikhao", "drives dikhao", "saare disks dikhao", "saare drives dikhao", "sab disks dikhao", "sab drives dikhao",
        "kaun kaun si drives hai", "kaun kaun se disk hai", "disk batao", "drives batao", "hard disk batao",
        "is pc me kaun kaun si drives lagi hain",
    ), (
        r"(?:how\s+many\s+)?(?:disks?|drives?|hard\s*drives?)\s+(?:are\s+)?(?:installed|connected|available|there)(?:\s+(?:on|in)\s+(?:my|this|the|your)?\s*(?:pc|computer|system|machine|laptop))?[?!.]?",
        r"(?:show|list|display|check|get|tell|view)(?:\s+me)?\s+(?:all\s+(?:the\s+)?|the\s+)?(?:available\s+|installed\s+|connected\s+)?(?:drives?|disks?|volumes?|storage\s+devices?|hard\s*drives?)[?!.]?",
        r"(?:(?:is|my|this|apne)?\s*(?:pc|computer|system|laptop)\s*(?:me|mein)\s+)?(?:kitn[ei]\s+)?(?:disks?|drives?|hard\s*disks?)\s+(?:hai|hain|lage\s+hai|lagi\s+hai|installed\s+hai)[?!.]?",
        r"(?:saar[ei]|sab|all)\s+(?:disks?|drives?|storage\s+devices?)\s+(?:dikhao|batao|list\s+karo)[?!.]?",
        r"(?:disks?|drives?|storage\s+devices?)\s+(?:dikhao|batao|list\s+karo|check\s+karo)[?!.]?",
    ), ("show", "list", "display", "check", "get", "tell", "view", "how", "kitne", "disks", "drives", "storage", "*")),
    fixed("disk", "I will show disk space for the current directory.", (
        "disk space", "disk usage", "free disk space", "how much disk space is left", "check disk space",
        "free storage", "available storage", "storage space", "how much storage is left", "free space",
        "remaining space", "check storage", "storage kitni bachi hai", "disk space kitna hai",
        "free space kitna hai", "disk space batao", "space kitna hai", "disk space check karo",
    ), (
        r"(?:check|show|tell|display|get)(?:\s+me)?\s+(?:the\s+)?(?:free\s+|available\s+)?(?:disk\s+space|disk\s+usage|storage\s+space|storage\s+usage)[?!.]?",
        r"how\s+much\s+(?:disk\s+space|storage|free\s+space)\s+(?:is\s+)?(?:left|free|available)[?!.]?",
        r"(?:disk|storage)\s+(?:space|usage|kitna\s+hai)\s*(?:batao|dikhao|check\s+karo)?[?!.]?",
        r"(?:disk|free\s+disk)\s+(?:space|usage)[?!.]?",
    ), ("show", "list", "display", "check", "disk", "storage", "how", "free", "*")),
    target_rule("disk_path", "disk", "I will show disk space for the requested path.", (
        rf"(?:check\s+)?(?:disk|storage)\s+(?:space|usage)\s+(?:of|for|on|in)\s+{TARGET}",
    ), starts=("check", "disk", "storage", "*")),
    fixed("system", "I will show system and hardware information.", (
        "system info", "system information", "full system info", "computer specifications", "system specs",
        "computer specs", "pc specifications", "pc specs", "hardware specs", "hardware details",
        "system hardware", "pc hardware", "hardware information", "tell me about this computer",
        "tell me about my pc", "pc info", "pc ki detail", "pc ki poori detail bata", "computer ki detail",
        "system ki detail", "system details batao", "hardware details dikhao", "hardware batao",
        "system info dikha do", "system info dikhao",
        "cpu info", "processor info", "cpu details", "what processor do i have",
    ), (
        r"(?:show|display|get|tell|view)(?:\s+me)?\s+(?:the\s+)?(?:system|computer|pc|machine|hardware)\s+(?:info|information|specs|specifications|details)[?!.]?",
        r"(?:hardware|system|pc)\s+(?:specs|specifications|details|info|information)[?!.]?",
        rf"(?:system|pc|computer|hardware)\s+(?:ki\s+)?(?:detail|details|info|specs)(?:\s+{HSHOW})?[?!.]?",
        r"(?:processor|cpu)\s+(?:info|details|specs)[?!.]?",
    ), ("show", "list", "display", "get", "tell", "view", "system", "hardware", "pc", "computer", "cpu", "*")),
    fixed("memory", "I will show current memory and RAM usage.", (
        "ram usage", "memory usage", "ram kitni bachi hai", "check ram", "how much ram is being used",
        "total ram", "available ram", "how much ram do i have", "how much memory is free",
        "ram kitni hai", "ram check karo", "memory check karo", "kitna ram use ho raha hai",
        "ram batao", "memory batao",
    ), (
        r"(?:check|show|tell|display|get)(?:\s+me)?\s+(?:current\s+)?(?:ram|memory)\s+(?:usage|consumption|status|info)?[?!.]?",
        r"how\s+much\s+(?:ram|memory)\s+(?:is\s+)?(?:being\s+used|used|free|available|installed|left)[?!.]?",
        r"(?:ram|memory)\s+(?:usage|kitni\s+hai|kitna\s+hai)\s*(?:batao|dikhao|check\s+karo)?[?!.]?",
    ), ("show", "list", "display", "check", "ram", "memory", "how", "*")),
    fixed("ip", "I will show the IP address and configuration.", (
        "what is my ip address", "my ip", "what is my ip", "ip address", "ip config", "show ip",
        "mera ip address kya hai", "ip address batao", "ip dikhao", "my ip address", "show my ip",
        "ip address check karo", "check ip", "what is ip",
    ), (
        r"(?:what\s+is|show|tell|get|display|check)(?:\s+me)?\s+(?:my\s+)?ip(?:\s+(?:address|config|configuration))?[?!.]?",
        r"(?:mera\s+)?ip(?:\s+address)?\s+(?:kya\s+hai|batao|dikhao)[?!.]?",
    ), ("show", "list", "display", "what", "my", "ip", "check", "*")),
    fixed("uptime", "I will show the system uptime.", (
        "how long has the computer been on", "system uptime", "uptime", "how long has the machine been up",
        "pc kab se chalu hai", "system kab se on hai", "uptime batao", "kitni der se chalu hai",
    ), (
        rf"(?:{SHOW})?(?:system\s+)?uptime[?!.]?",
        r"(?:how\s+long\s+(?:has\s+)?(?:the\s+)?(?:computer|pc|system|machine)\s+been\s+(?:on|up|running)|(?:system\s+)?uptime)[?!.]?",
        r"(?:pc|system|computer)\s+kab\s+se\s+(?:chalu|on)\s+hai[?!.]?",
    ), ("show", "list", "display", "how", "system", "uptime", "pc", "*")),
    fixed("env", "I will show the environment variables.", (
        "show env", "show environment variables", "list env", "list environment variables",
        "environment variables", "env variables",
    )),
    fixed("vars", "I will show the shell variables.", (
        "show vars", "show variables", "list vars", "list variables", "shell variables",
    )),
    fixed("path", "I will show the PATH environment variable.", (
        "show path", "display path", "path variable", "path dikhao",
    )),
    *(
        fixed(command, message, phrases,
              (rf"(?:{SHOW})?(?:{english})[?!.]?", rf"(?:{hinglish})\s+{HSHOW}[?!.]?"), (*starts, "*"))
        for command, message, phrases, english, hinglish, starts in (
            ("processes", "I will show the running processes.", (
                "what is running", "running processes", "list running processes", "running tasks",
                "active processes", "abhi kaun kaun se programs chal rahe hain",
            ), r"(?:running\s+)?(?:processes|tasks)", r"(?:running\s+)?processes", ("show", "list", "display", "processes", "running")),
            ("network", "I will show network information.", (
                "network info", "network details", "network ki detail dikha",
            ), r"network\s+(?:info|information)", r"network\s+info", ("show", "list", "display", "network")),
            ("netstat", "I will show network connections.", (
                "active connections", "open ports", "network connections", "kaun se ports khule hain",
            ), r"(?:active|network)\s+connections", r"network\s+connections", ("show", "list", "display", "network")),
            ("history", "I will show this terminal's command history.", (
                "command history", "terminal history", "show history",
            ), r"(?:command\s+|terminal\s+)?history", r"(?:command\s+)?history", ("show", "list", "display", "command", "history")),
            ("now", "I will show the current time.", (
                "what time is it", "abhi kitne baje hain", "current time", "what is the time", "time batao", "tell me the time",
            ), r"(?:current\s+)?time", r"(?:current\s+)?time", ("show", "list", "display", "time", "current")),
            ("today", "I will show today's date.", (
                "what is today's date", "aaj ki date batao", "today's date", "today date", "current date",
                "aaj ki tareekh", "aaj ki date", "aaj kaun si date hai", "give me the date today", "tell me today's date",
            ), r"(?:current\s+|today's\s+)?date", r"date", ("show", "list", "display", "date")),
            ("me", "I will show the signed-in user.", (
                "who am i", "current user", "what is my username", "my username", "main kaun sa user hu",
            ), r"(?:current\s+user|my\s+username)", r"current\s+user", ("show", "list", "display", "current")),
            ("pc", "I will show the computer name.", (
                "pc name", "computer name", "machine name", "hostname", "is computer ka naam kya hai",
            ), r"(?:computer|pc|machine)\s+name", r"(?:computer|pc)\s+name", ("show", "list", "display", "computer", "pc")),
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
    IntentRule(
        "navigate_drive",
        "cd",
        "I will change this session to the requested drive.",
        patterns=(
            rf"(?:go|navigate|switch)\s+to\s+(?:the\s+)?(?P<drive>[a-zA-Z]):?(?:\s+drive)?",
            rf"change\s+(?:directory|folder)?\s*(?:to\s+)?(?:the\s+)?(?P<drive>[a-zA-Z]):?(?:\s+drive)",
            rf"(?P<drive>[a-zA-Z]):?(?:\s+drive)\s*(?:mein|me)?\s*(?:jao|chalo|switch\s+karo)",
        ),
        arguments=("{drive}:",),
        slots=(("drive", "path"),),
    ),
    target_rule("navigate", "cd", "I will change this session to the requested directory.", (
        rf"(?:go|navigate|switch)\s+to\s+(?:the\s+)?(?:folder\s+|directory\s+)?{TARGET}(?:\s+folder|\s+directory)?",
        rf"change\s+(?:directory|folder)\s+to\s+{TARGET}(?:\s+folder|\s+directory)?",
        rf"{TARGET}\s+(?:folder\s+|directory\s+)?(?:mein|me)\s+(?:jao|chalo)",
    )),
    target_rule("list_path", "files", "I will list files in the requested directory.", (
        rf"{SHOW}{FILE_ITEMS}\s+(?:in|inside)\s+(?:the\s+)?(?:folder\s+|directory\s+)?{TARGET}",
        rf"(?:mujhe\s+)?{HLIST_TARGET}\s+(?:(?:folder|directory)\s+)?(?:ki|ke)\s+files\s+{HSHOW}[?!.]?",
    )),
    target_rule("list_folders_path", "folders", "I will list folders in the requested directory.", (
        rf"{SHOW}{FOLDER_ITEMS}\s+(?:in|inside)\s+(?:the\s+)?(?:folder\s+|directory\s+)?{TARGET}",
        rf"(?:mujhe\s+)?{HLIST_TARGET}\s+(?:(?:folder|directory)\s+)?(?:ki|ke)\s+(?:sirf\s+)?(?:folders|directories)\s+{HSHOW}[?!.]?",
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
    IntentRule("delete_named_path", "delete", "I will delete the requested item after your approval.",
               patterns=(rf"(?:delete|remove)\s+{TARGET}",), starts=("delete", "remove"),
               arguments=("confirm", "{target}"), slots=(("target", "file_path"),)),
    IntentRule("open_named_path", "open", "I will open the requested app, URL, or file.",
               patterns=(rf"(?:open|launch)\s+{TARGET}",), starts=("open", "launch"),
               arguments=("{target}",), slots=(("target", "app_or_path"),)),
    fixed("windows", "I will show the list of active windows.", (
        "active windows", "windows list", "list windows", "open windows", "running apps",
        "show active windows", "show open windows", "show me active windows",
        "show me open windows", "show me the list of active windows",
        "show the list of active windows", "list of active windows",
        "active windows dikhao", "running apps batao", "open windows dikhao",
    ), (
        r"(?:show|list|display)(?:\s+me)?(?:\s+the\s+list\s+of)?\s+(?:active|open|running)?\s*windows[?!.]?",
        r"(?:active|open|running)\s+windows(?:\s+(?:dikhao|batao|list\s+karo))?[?!.]?",
    ), ("show", "list", "display", "windows", "*")),
    fixed("mouse", "I will click the mouse.", (
        "click on the centre of screen", "click on the center of screen",
        "click center", "click centre", "click middle", "click screen",
        "screen ke center pe click karo", "center click karo",
    ), (
        r"(?:mouse\s+)?click(?:\s+on)?(?:\s+the)?\s+(?:center|centre|middle)(?:\s+of\s+(?:the\s+)?screen)?[?!.]?",
    ), ("click", "mouse", "*")),
    fixed("keyboard", "I will press the requested key.", (
        "press enter", "hit enter", "enter dabao", "enter press karo",
        "press space", "press tab", "press escape",
    ), (
        r"(?:please\s+)?(?:press|hit)\s+(?:the\s+)?(?P<key>enter|tab|space|escape|esc|backspace)(?:\s+key)?[?!.]?",
    ), ("press", "hit", "*")),
    IntentRule(
        "browser_dom",
        "browser",
        "I will fetch the current browser page DOM structure and interactive elements.",
        phrases=(
            "dom", "browser dom", "show dom", "page dom", "show page dom",
            "page elements", "show page elements", "inspect page",
            "page ka dom dikhao", "dom dikhao", "dom access", "page ka dom",
            "show dom elements", "dom elements", "show buttons", "list buttons",
            "page ke buttons", "page ke buttons dikhao", "buttons dikhao", "buttons dikha do",
        ),
        patterns=(
            r"(?:show|get|display|read|inspect|list)(?:\s+me)?\s+(?:the\s+)?(?:page\s+)?(?:dom\s+)?(?:structure|elements|buttons|controls)[?!.]?",
            r"(?:page\s+)?(?:dom|buttons|elements)\s+(?:dikhao|batao|access)[?!.]?",
            r"(?:page\s+ke\s+)?(?:dom|buttons|elements)(?:\s+dikha\s+do|\s+dikhao)[?!.]?",
            r"(?:show|get|display|list)\s+(?:the\s+)?(?:interactive\s+)?page\s+elements[?!.]?",
        ),
        starts=("dom", "browser", "show", "page", "buttons", "list", "*"),
        arguments=("dom",),
    ),
    IntentRule(
        "browser_new_tab",
        "browser",
        "I will open a new browser tab.",
        phrases=(
            "new tab", "open new tab", "open a new tab", "naya tab", "naya tab kholo",
            "new tab kholo", "new tab open karo", "create new tab", "browser new tab",
        ),
        patterns=(
            r"(?:open|start|create)(?:\s+a)?\s+new\s+tab[?!.]?",
            r"new\s+tab(?:\s+(?:kholo|open\s+karo))?[?!.]?",
            r"naya\s+tab(?:\s+kholo)?[?!.]?",
        ),
        starts=("new", "open", "naya", "create", "browser", "*"),
        arguments=("new_tab",),
    ),
    IntentRule(
        "browser_click_button",
        "browser",
        "I will click the matching button or element on the browser page.",
        patterns=(
            r"(?:please\s+)?(?:click|tap)\s+(?:on\s+)?(?:the\s+)?(?P<target>(?!center|centre|middle|screen)[a-zA-Z0-9_\-\.]+)(?:\s+button|\s+link)?[?!.]?",
            r"(?P<target>(?!center|centre|middle|screen)[a-zA-Z0-9_\-\.]+)\s+(?:button|link)?\s*(?:pe|par)\s+click\s*(?:karo|kar\s+do)?[?!.]?",
        ),
        starts=("click", "tap", "*"),
        arguments=("click", "{target}"),
        slots=(("target", "text"),),
    ),
    IntentRule(
        "browser_search",
        "browser",
        "I will search the web.",
        patterns=(
            rf"(?:search|google|find)\s+(?:for\s+)?(?P<query>{ATOM})",
            rf"(?P<query>{ATOM})\s+(?:search\s+karo|ko\s+search\s+karo)",
        ),
        starts=("search", "google", "find", "*"),
        arguments=("search", "{query}"),
        slots=(("query", "text"),),
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
    IntentRule("which_program", "which", "I will locate the executable for the requested program.", patterns=(
        r"(?:which|whereis)\s+(?P<target>[a-zA-Z0-9_\-\.]+)",
        r"where\s+is\s+(?P<target>[a-zA-Z0-9_\-\.]+)\s+installed",
        r"full\s+path\s+of\s+(?P<target>[a-zA-Z0-9_\-\.]+)",
    ), starts=("which", "whereis", "where", "full", "*"), arguments=("{target}",), slots=(("target", "path"),)),
    fixed("random", "I will pick a random number.", (
        "roll a dice", "roll dice", "pick a random number", "ek lucky number do",
    )),
    IntentRule(
        "calc",
        "calc",
        "I will calculate the requested expression.",
        patterns=(
            rf"(?:calculate|compute|solve|evaluate|what\s+is|math)\s+(?P<expr>[0-9\.\+\-\*\/\(\)\^\%\s]+)",
            rf"(?P<expr>[0-9\.\+\-\*\/\(\)\^\%\s]+)\s+(?:calculate\s+karo|solve\s+karo|hisab\s+karo)",
        ),
        starts=("calculate", "compute", "solve", "evaluate", "what", "math", "*"),
        arguments=("{expr}",),
        slots=(("expr", "expression"),),
    ),
    IntentRule(
        "note",
        "note",
        "I will record the requested note.",
        patterns=(
            rf"(?:take\s+(?:a\s+)?note|make\s+(?:a\s+)?note|write\s+(?:a\s+)?note|note\s+down|add\s+note|save\s+note|note)\s+(?P<text>[^\r\n]+)",
            rf"(?P<text>[^\r\n]+)\s+(?:note\s+kar\s+lo|note\s+likho|likh\s+lo)",
        ),
        starts=("take", "make", "write", "note", "add", "save", "*"),
        arguments=("{text}",),
        slots=(("text", "text"),),
    ),
    IntentRule(
        "kill_process",
        "kill",
        "I will terminate the requested process.",
        patterns=(
            rf"(?:kill|terminate|stop)\s+(?:process|task|app|program)?\s*(?P<target>[a-zA-Z0-9_\-\.]+)",
            rf"(?P<target>[a-zA-Z0-9_\-\.]+)\s+(?:process|task|program)?\s*(?:ko\s+)?(?:kill\s+karo|band\s+karo|stop\s+karo)",
        ),
        starts=("kill", "terminate", "stop", "*"),
        arguments=("{target}",),
        slots=(("target", "app_or_path"),),
    ),
    target_rule("search_files", "search", "I will search for matching filenames.", (
        rf"(?:search|find)\s+(?:for\s+)?(?:files?\s+(?:named|called)\s+)?{TARGET}",
        rf"{TARGET}\s+(?:naam\s+ki\s+)?files?\s+(?:dhundho|khojo|search\s+karo)",
    ), starts=("search", "find", "*")),
    target_rule("find_text", "findtext", "I will search for matching text inside files.", (
        rf"(?:find|search)\s+text\s+{TARGET}(?:\s+in\s+files)?",
        rf"grep\s+{TARGET}",
        rf"files\s+(?:me|mein)\s+{TARGET}\s+(?:dhundho|search\s+karo)",
    ), starts=("find", "search", "grep", "files", "*")),
    IntentRule(
        "download_file",
        "download",
        "I will download the requested file.",
        patterns=(
            rf"(?:download|fetch)\s+(?P<url>https?://[^\s]+)",
            rf"(?P<url>https?://[^\s]+)\s+(?:download\s+karo|fetch\s+karo)",
        ),
        starts=("download", "fetch", "*"),
        arguments=("{url}",),
        slots=(("url", "url"),),
    ),
    IntentRule(
        "zip_folder",
        "zip",
        "I will compress the folder into a zip archive.",
        patterns=(
            rf"(?:zip|compress)\s+(?:folder\s+)?{SOURCE}\s+(?:to|into|as)\s+{DEST}",
        ),
        starts=("zip", "compress", "*"),
        arguments=("{source}", "{destination}"),
        slots=(("source", "path"), ("destination", "path")),
    ),
    target_rule("unzip_file", "unzip", "I will extract the zip archive.", (
        rf"(?:unzip|extract|unpack)\s+(?:archive\s+|file\s+)?{TARGET}",
        rf"{TARGET}\s+(?:unzip|extract)\s+karo",
    ), starts=("unzip", "extract", "unpack", "*")),
    IntentRule(
        "git_add",
        "gadd",
        "I will stage the requested files in Git.",
        patterns=(
            rf"git\s+add\s+(?P<target>[^\r\n]+)",
            rf"stage\s+(?:the\s+)?(?:files?\s+)?(?P<target>[^\r\n]+)",
        ),
        starts=("git", "stage", "*"),
        arguments=("{target}",),
        slots=(("target", "text"),),
    ),
    IntentRule(
        "git_commit",
        "gcommit",
        "I will commit the staged changes in Git.",
        patterns=(
            rf"git\s+commit(?:\s+-m)?\s+(?P<msg>[^\r\n]+)",
            rf"commit\s+(?:staged\s+changes\s+)?(?:with\s+message\s+)?(?P<msg>[^\r\n]+)",
        ),
        starts=("git", "commit", "*"),
        arguments=("-m", "{msg}"),
        slots=(("msg", "text"),),
    ),
    target_rule("git_checkout", "gcheckout", "I will switch to the requested Git branch.", (
        rf"git\s+checkout\s+{TARGET}",
        rf"(?:switch|change)\s+(?:to\s+)?(?:git\s+)?branch\s+{TARGET}",
    ), starts=("git", "switch", "change", "*")),
    fixed("gpull", "I will pull updates from the Git remote.", (
        "git pull", "pull from git", "pull git changes", "pull remote changes",
    )),
    fixed("gpush", "I will push commits to the Git remote.", (
        "git push", "push to git", "push git changes", "push remote changes",
    )),
)
