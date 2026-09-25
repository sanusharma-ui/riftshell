"""Reviewed command capabilities, slot schemas and semantic examples.

Examples are embedded by a pretrained model, NOT used as exact-match patterns.
Slot layouts describe syntax/argument order; they never decide the command.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SemanticIntent:
    key: str
    command: str
    examples: tuple[str, ...]
    layout: str = "none"
    kinds: tuple[str, ...] = ()
    arguments: tuple[str, ...] = ()


def intent(command, *examples, layout="none", kinds=(), arguments=(), key=""):
    return SemanticIntent(key or command, command, tuple(examples), layout, tuple(kinds), tuple(arguments))


# Equivalent commands deliberately share a canonical result (goto -> cd,
# take -> head, count -> wc when a file is supplied), avoiding false ambiguity.
EQUIVALENTS = {"goto": "cd", "take": "head", "count": "wc"}

SEMANTIC_INTENTS = (
    *(intent(command, *examples) for command, examples in (
        ("help", ("List the available shell commands", "Which commands can this terminal execute?")),
        ("plugins", ("Check installed plugins and their load status", "Which extensions are loaded in this shell?")),
        ("exit", ("Close this shell session", "Exit the terminal application")),
        ("clear", ("Wipe the terminal screen", "Clear everything displayed in the console")),
        ("where", ("Tell me the current working directory", "Which directory am I currently in?")),
        ("files", ("Show everything in the current directory", "What files and folders are here?", "Display the contents of this location")),
        ("folders", ("What directories are here?", "Let me see the folders in this location", "List only the subdirectories")),
        ("up", ("Navigate to the parent directory", "Take me one directory level higher")),
        ("home", ("Return to my home directory", "Navigate to the user home folder")),
        ("network", ("Inspect my network configuration", "Show the network adapter information")),
        ("processes", ("Which processes are currently running?", "List the active processes on this computer")),
        ("system", ("Give me this computer's system information", "Check my machine specifications")),
        ("me", ("Which user is currently signed in?", "Tell me my login username")),
        ("pc", ("What is this computer called?", "Tell me the machine hostname")),
        ("today", ("Tell me today's date", "Which date is it today?")),
        ("now", ("Tell me the current time", "What time is it right now?")),
        ("history", ("Show the commands I previously ran", "Display this terminal's command history")),
        ("env", ("List the environment variables", "Display the environment settings for this process")),
        ("tree", ("Visualize this directory's folder hierarchy", "Show the directory structure as a tree")),
        ("version", ("Which version of RiftShell is installed?", "Tell me the shell's version number")),
        ("drives", ("Which drives are available on this PC?", "List the Windows disk drives")),
        ("disk", ("How much disk space is available here?", "Check the used and free storage space")),
        ("ip", ("Tell me my computer's IP address", "Display my IP configuration")),
        ("netstat", ("Which network connections are active?", "List established connections and listening ports")),
        ("path", ("Display the PATH environment variable", "List the executable search directories in PATH")),
        ("random", ("Pick a random number", "Generate a random integer")),
        ("memory", ("How much RAM is being used?", "Check current memory consumption")),
        ("uptime", ("How long has this computer been running?", "Report the time since the system booted")),
        ("vars", ("List the shell variables I have defined", "Display RiftShell session variables")),
        ("alias", ("List the command aliases", "Show my shell command shortcuts")),
        ("last", ("Print the previous command's output again", "Redisplay the last terminal result")),
        ("gstatus", ("Check the Git repository status", "Which files have changed in this repository?")),
        ("gbranch", ("List Git branches", "Which branches exist in this repository?")),
        ("glog", ("Show the Git commit history", "List recent repository commits")),
        ("gdiff", ("Show unstaged changes in Git", "Display the current uncommitted diff")),
        ("gpull", ("Pull updates from the Git remote", "Bring remote repository changes into this branch")),
        ("gpush", ("Push my commits to the Git remote", "Upload this branch's commits to the remote repository")),
        ("gremote", ("List configured Git remotes", "Which remote repositories are configured?")),
        ("hello", ("Run the hello plugin test command", "Execute the hello extension's test")),
    )),
    intent("theme", "List the available interface themes", "Which colour themes are available?", key="theme_list", arguments=("list",)),
    intent("theme", "Tell me the current interface theme", "Which colour theme am I using?", key="theme_current", arguments=("current",)),
    *(intent(command, *examples, layout=layout, kinds=(kind,), arguments=args or ("{0}",), key=key)
      for command, key, layout, kind, args, examples in (
        ("theme", "theme_set", "one", "theme", (), ("Change the interface theme to target", "Use the target colour theme")),
        ("files", "files_path", "location", "path", (), ("Show the contents of folder target", "What files and folders are in target?")),
        ("folders", "folders_path", "location", "path", (), ("List the subdirectories inside target", "Which folders exist in target?")),
        ("cd", "navigate", "one", "path", (), ("Take me to directory target", "Switch my working location to target")),
        ("makefolder", "create_folder", "one", "path", (), ("Create a new directory called target", "Make a folder named target")),
        ("makefile", "create_file", "one", "file", (), ("Create an empty file named target", "Make a blank file target")),
        ("read", "print_file", "one", "file", (), ("Print the raw contents of file target in the terminal", "Display file target verbatim")),
        ("open", "open_path", "one", "path", (), ("Launch file target with its default application", "Open folder target in the file manager")),
        ("delete", "delete_path", "one", "path", ("confirm", "{0}"), ("Delete the file target", "Erase the directory target", "Remove file target from disk")),
        ("search", "search_names", "one", "text", (), ("Find files with names containing target", "Search filenames for target")),
        ("findtext", "search_content", "one", "text", (), ("Search inside files for the text target", "Find file contents containing target")),
        ("calc", "calculate", "one", "expression", (), ("Calculate the expression target", "Evaluate this arithmetic target")),
        ("tree", "tree_path", "location", "path", (), ("Show the directory tree of target", "Display the folder hierarchy under target")),
        ("echo", "print_text", "one", "text", (), ("Print this text in the terminal target", "Echo the literal string target")),
        ("disk", "disk_path", "location", "path", (), ("Check disk space for target", "How much storage is available on target?")),
        ("ping", "ping_host", "one", "host", (), ("Check whether host target is reachable", "Ping target", "Test connectivity to target")),
        ("sleep", "sleep_seconds", "one", "seconds", (), ("Pause the shell for target seconds", "Wait target seconds")),
        ("random", "random_max", "one", "integer", (), ("Pick a random integer up to target", "Generate a random number below target")),
        ("hash", "hash_file", "one", "file", ("file", "{0}"), ("Calculate the SHA256 hash of file target", "Get a SHA256 checksum for file target")),
        ("hash", "hash_text", "one", "text", ("text", "{0}"), ("Calculate the SHA256 hash of text target", "Hash the literal string target with SHA256")),
        ("base64", "base64_encode", "one", "text", ("encode", "{0}"), ("Encode text target as base64", "Convert string target to base64")),
        ("base64", "base64_decode", "one", "text", ("decode", "{0}"), ("Decode the base64 string target", "Convert base64 target back to text")),
        ("download", "download_url", "one", "url", (), ("Download a file from target", "Fetch the URL target onto disk")),
        ("unzip", "unzip_here", "one", "file", (), ("Extract the zip archive target", "Unpack archive target here")),
        ("head", "head_default", "one", "file", (), ("Display the beginning of file target", "Print the first lines of target")),
        ("tail", "tail_default", "one", "file", (), ("Display the end of file target", "Print the last lines of target")),
        ("kill", "kill_process", "one", "process", (), ("Terminate process target", "Stop the process named target")),
        ("wc", "count_file", "one", "file", (), ("Count lines words and characters in target", "Give me the word and line counts of target")),
        ("which", "which_program", "one", "name", (), ("Locate the executable target", "Find the installation path of command target")),
        ("run", "run_literal", "one", "argv", ("*0",), ("Execute the native command target", "Run the program target")),
        ("unsetvar", "unset_variable", "one", "name", (), ("Remove shell variable target", "Unset the session variable target")),
        ("unalias", "remove_alias", "one", "name", (), ("Delete command alias target", "Remove the shell shortcut target")),
        ("filter", "filter_output", "one", "text", (), ("Filter the previous output for text target", "Keep output lines containing target")),
        ("sort", "sort_file", "one", "file", (), ("Sort the lines in file target alphabetically", "Order file target lines")),
        ("unique", "unique_file", "one", "file", (), ("Display unique lines from file target", "Remove duplicate lines in the displayed contents of target")),
        ("take", "take_output", "one", "integer", (), ("Take the first target lines of the previous output", "Display the first target lines of piped input")),
        ("skip", "skip_output", "one", "integer", (), ("Skip the first target lines of the previous output", "Drop target lines from the start of piped input")),
        ("save", "save_output", "one", "file", (), ("Save the last terminal output into file target", "Write the previous command result to target")),
        ("gadd", "git_stage", "one", "path", (), ("Stage file target in Git", "Add file target to the Git staging area")),
        ("gcommit", "git_commit", "one", "text", ("-m", "{0}"), ("Create a Git commit with message target", "Commit staged changes with the message target")),
        ("gcheckout", "git_checkout", "one", "branch", (), ("Switch to Git branch target", "Check out the branch target")),
    )),
    *(intent(command, *examples, key=key, layout=layout, kinds=kinds, arguments=args)
      for command, key, layout, kinds, args, examples in (
        ("duplicate", "copy_path", "pair", ("path", "path"), ("{0}", "{1}"), ("Copy source to destination", "Duplicate file source into destination")),
        ("shift", "move_path", "pair", ("path", "path"), ("{0}", "{1}"), ("Move source into destination", "Relocate file source to destination")),
        ("rename", "rename_path", "pair", ("path", "path"), ("{0}", "{1}"), ("Rename source to destination", "Change the name of source to destination")),
        ("zip", "zip_folder", "pair", ("path", "file"), ("{0}", "{1}"), ("Compress folder source into zip archive destination", "Package directory source as destination")),
        ("unzip", "unzip_to", "pair", ("file", "path"), ("{0}", "{1}"), ("Extract archive source into destination", "Unpack zip source to folder destination")),
        ("download", "download_to", "pair", ("url", "file"), ("{0}", "{1}"), ("Download source to file destination", "Fetch URL source and save as destination")),
        ("setvar", "set_variable", "pair", ("name", "text"), ("{0}", "{1}"), ("Set shell variable source to destination", "Assign value destination to variable source")),
        ("alias", "define_alias", "pair", ("name", "argv"), ("{0}", "*1"), ("Define alias source for command destination", "Create shell shortcut source for destination")),
        ("search", "search_names_in", "search", ("text", "path"), ("{0}", "{1}"), ("Find filenames containing source in directory destination", "Search file names for source under destination")),
        ("findtext", "search_content_in", "search", ("text", "path"), ("{0}", "{1}"), ("Find text source inside files under destination", "Search file contents for source in destination")),
        ("filter", "filter_file", "search", ("text", "file"), ("{0}", "{1}"), ("Filter lines containing source in file destination", "Find matching lines for source in destination")),
        ("head", "head_lines", "lines", ("integer", "file"), ("{1}", "{0}"), ("Show the first source lines of destination", "Print the top source lines from destination")),
        ("tail", "tail_lines", "lines", ("integer", "file"), ("{1}", "{0}"), ("Show the last source lines of destination", "Print the bottom source lines from destination")),
        ("skip", "skip_lines", "lines", ("integer", "file"), ("{0}", "{1}"), ("Skip the first source lines of destination", "Omit the initial source lines from file destination")),
        ("tree", "tree_depth", "depth", ("path", "integer"), ("{0}", "{1}"), ("Show the directory tree of source to depth destination", "Display folder source hierarchy destination levels deep")),
        ("random", "random_range", "range", ("integer", "integer"), ("{0}", "{1}"), ("Pick a random number between source and destination", "Generate a random integer from source to destination")),
    )),
    intent("sort", "Sort the previous output alphabetically", "Order piped input lines", key="sort_output"),
    intent("unique", "Remove duplicate lines from the previous output", "Display distinct lines of piped input", key="unique_output"),
    intent("count", "Count lines words and characters in the previous output", "Count the piped input", key="count_output"),
)

# Competing non-command examples help reject conversational lookalikes. These
# are semantic negatives, not a blacklist of all possible ordinary questions.
CHAT_EXAMPLES = (
    "Explain how a file system works", "What is a directory?", "Tell me about memory management",
    "How do I delete a file?", "Should I stop this process?", "What does this command mean?",
    "I deleted a folder yesterday", "I cannot open my files", "Why is my network slow?",
    "Help me decide which files to remove", "Write code for a calculator app",
    "Read this document and explain it", "Summarize the contents of this file",
    "Hi how are you?", "Tell me a joke", "Who invented the computer?",
    "Describe the history of computers", "Explain what a Git commit does",
)
