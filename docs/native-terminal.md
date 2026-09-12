# Native desktop terminal

Desktop tabs now offer **PowerShell** and **RiftShell commands**. PowerShell is
the default when the native dependencies are installed. Existing built-ins and
plugins remain in RiftShell commands; selecting a command in the command palette
selects that mode automatically. The command-line and Telegram execution engines
retain their previous behavior.

Each desktop tab owns a persistent PowerShell process hosted through Windows
ConPTY. PowerShell 7 (`pwsh.exe`) is preferred when installed; otherwise the tab
uses Windows PowerShell. The tab inherits the environment of the RiftShell app,
loads normal PowerShell profiles, and preserves directory, variables, functions,
and activated environments across native commands. No machine-wide PATH or
execution-policy changes are made. `npm`/`npx` use their installed `.cmd` launchers
when available, avoiding the corresponding `.ps1` launcher policy problem.

Type system commands directly in the bottom command field. `run` is optional in
PowerShell mode. Output streams into the terminal, including ANSI colors and
progress redraws. While a program is running, click the terminal to enter input,
answer prompts, or use arrows, Tab and Ctrl+C. Command entry at the outer prompt
uses the bottom field and its local Up/Down history; native PSReadLine completion
in that field is not implemented. Multiple-line interactive pastes ask before
submitting. Copy output copies the screen and retained scrollback; selecting text
and pressing Ctrl+C copies the selection instead of interrupting a process.

Native commands have no fixed runtime timeout. Cancel sends Ctrl+C; it does not
pretend the command finished. If a program ignores interruption, closing its tab
offers to terminate the shell and its process tree. App shutdown waits for the
transport cleanup before closing. Programs launched independently through a
service manager or another elevation context may outlive the terminal.

Orbit remains a conversational helper. Its existing built-ins, reviewed file
writes, approvals, original-tab binding and result-driven continuation remain in
place. Its `run <command>` actions use the same desktop PowerShell session even
when the selected display mode is RiftShell commands. A legacy navigation action
is synchronized into PowerShell before the next native command. Native navigation
updates the workspace path used by Orbit. In a PowerShell registry/provider
location, workspace actions pause until the user returns to a filesystem folder.

The prompt reports a sequence number, directory, environment label and exit
status using a session-specific console title message. The renderer consumes this
message without displaying it. Completion requires a new prompt report; text that
merely resembles `PS ...>` does not complete a command. Observations sent to Orbit
are bounded and stripped of terminal control sequences. This bookkeeping is not
a security boundary against programs executing inside the shell. The existing
approval system is also not an operating-system sandbox.

## Manual setup and verification

These commands are provided for manual use; they were **not run** during the
implementation. Use the same Python interpreter/environment that launches
RiftShell. From `D:\riftshell`, in your existing external terminal:

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p "test_*.py"
python main.py
```

The new tests mock transport and exercise prompt framing, command completion,
interruption, directory synchronization, safety classification, Orbit routing,
dependency fallback and rendering. They do not establish live ConPTY compatibility
or actual package installation. The following desktop checks are still required:

1. Open a PowerShell tab. Check `python --version`, `python -m pip --version`,
   `node --version`, `npm --version`, and `git --version` for tools installed on
   your PC. A missing executable should produce PowerShell's diagnostic rather
   than RiftShell's `Unknown command`.
2. Navigate to a disposable scratch folder, including a path with spaces and a
   non-ASCII name. Run `pwd` separately. The header and Orbit's current-directory
   answer should agree. Open another tab and verify directory/environment state
   is independent.
3. In the scratch folder run `python -m venv .venv`, then activate it with
   `.\.venv\Scripts\Activate.ps1` if your existing policy permits that script.
   Run `python -m pip --version` and check that it points into this environment.
   Install a small package there, such as `python -m pip install packaging`.
   If activation is policy-blocked, use `.\.venv\Scripts\python.exe -m pip ...`
   explicitly; RiftShell does not silently weaken the policy.
4. In the disposable folder run `npm init -y`, then `npm install is-number`.
   Confirm progress appears during installation, the command completes, and
   `node_modules` and the lockfile exist in that folder.
5. Run `python -m http.server 8765`. Leave it running for more than 60 seconds,
   then use Cancel or Ctrl+C. Verify the port is released. In your configured
   backend project, also check `python -m uvicorn backend.main:app --reload --port 8000`
   and confirm interruption stops its reload child. Check `npm run dev` in a
   configured frontend project.
6. Run `python` interactively, enter `print('hello')`, use its editing keys, then
   `exit()`. Check `Read-Host 'Your name'` and respond in the terminal surface.
7. Check `python -c "import sys; sys.exit(7)"` and an invalid command. Ask Orbit
   about the last result; neither should be presented as successful execution.
8. Check PowerShell pipelines and redirection in the scratch folder, for example
   `Get-ChildItem | Select-Object -First 2` and `'hello' > sample.txt`. `&&`/`||`
   require PowerShell 7; Windows PowerShell's normal syntax limits still apply.
9. Resize the tab while output is flowing; verify colors, progress redraws,
   scrollback, selection/copy, and an interactive application's screen restore.
10. Switch to RiftShell commands and check `files`, `read README.md`, `where`,
    themes and installed plugins. Ask Orbit a general question, request a native
    command, reject an approval, and review a file-write proposal. General chat
    must remain conversational and rejected actions must not execute.
11. Ask Orbit to change directory, then execute a native command. Verify the
    real working directory agrees. Cancel a running Orbit-native task; confirm
    it does not auto-continue or report successful completion.
12. Close a running native tab after accepting its termination prompt. Confirm
    its server and reload children are gone and other tabs remain usable.

## Compatibility boundaries

This change targets Windows desktop PowerShell sessions. CMD, WSL and SSH can be
launched as nested interactive programs; Orbit cannot track their inner working
directory or completion until they exit back to the outer PowerShell prompt.
Separate selectable profiles for these shells are not implemented.

Tools still require their own installation, credentials, network access and
permissions. Restart RiftShell after external PATH changes. A program that replaces
the PowerShell `prompt` function without chaining to it removes completion tracking;
close that tab and open another. Status follows the prompt's PowerShell success
flag and native exit code, not proof of every side effect of a compound command.
Custom prompt frameworks and environment activation scripts need live verification.

The renderer supports text/ANSI, keyboard interaction, scrollback and an alternate
screen, but is not a complete xterm implementation: terminal graphics, mouse
reporting, advanced keyboard protocols and every full-screen application's
behavior are not guaranteed. Validate the tools you actually use before relying
on the new terminal for important work.

Implementation references: [Microsoft ConPTY](https://learn.microsoft.com/en-us/windows/console/pseudoconsoles),
[PyWinPTY](https://github.com/andfoy/pywinpty),
and [pyte](https://pyte.readthedocs.io/en/latest/api.html).
