"""Persistent Windows terminal transport. No application commands are parsed here.

All process IO stays off the Qt thread. Consumers drain ordered events; only a
PowerShell prompt marker confirms that a submitted command has finished.
"""
from __future__ import annotations

import base64
import json
import os
import queue
import re
import shutil
import subprocess
import threading
import uuid
from pathlib import Path


def native_dependency_error() -> str:
    if os.name != "nt":
        return "Native terminal sessions currently require Windows 10/11. RiftShell commands remain available."
    try:
        import winpty  # noqa: F401
        import pyte  # noqa: F401
    except (ImportError, OSError):
        return "Native terminal dependencies are unavailable. Install requirements.txt using the Python that launches RiftShell, then restart."
    return ""


def powershell_startup(token: str) -> str:
    """Use an encoded startup script; never interpolate a directory or command."""
    if not re.fullmatch(r"[0-9a-f]{32}", token):
        raise ValueError("Invalid session token")
    script = r"""
$global:__RiftSequence = 0
$global:__RiftInvocationFailed = $false
function global:Invoke-RiftNative {
    if ($args.Count -eq 0) { Write-Error 'Usage: run <program> [args...]'; return }
    $riftProgram = $args[0]
    $riftArgs = @($args | Select-Object -Skip 1)
    & $riftProgram @riftArgs
    $global:__RiftInvocationFailed = -not $?
}
Set-Alias -Name run -Value Invoke-RiftNative -Scope Global
Set-Alias -Name exec -Value Invoke-RiftNative -Scope Global
Set-Alias -Name native -Value Invoke-RiftNative -Scope Global
# Node's Windows installer provides .cmd launchers alongside .ps1 launchers.
# Prefer the former without changing the user's PowerShell execution policy.
foreach ($riftName in @('npm', 'npx')) {
    $riftLauncher = Get-Command ($riftName + '.cmd') -ErrorAction SilentlyContinue
    if ($riftLauncher) { Set-Alias -Name $riftName -Value $riftLauncher.Source -Scope Global }
}
function global:prompt {
    $riftOK = $global:?
    Set-StrictMode -Off
    $riftExit = 0
    if (-not $riftOK -or $global:__RiftInvocationFailed) {
        $riftExit = 1
        if ($global:LASTEXITCODE) { $riftExit = [int]$global:LASTEXITCODE }
    }
    $global:__RiftSequence += 1
    $riftLocation = Get-Location
    $riftState = @{
        sequence = $global:__RiftSequence
        exit_code = $riftExit
        cwd = $(if ($riftLocation.Provider.Name -eq 'FileSystem') { $riftLocation.ProviderPath } else { $riftLocation.Path })
        filesystem = ($riftLocation.Provider.Name -eq 'FileSystem')
        virtual_env = $env:VIRTUAL_ENV
    } | ConvertTo-Json -Compress
    $riftPayload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($riftState))
    # The console title channel is supported even by older Windows ConPTY
    # versions that consume unknown OSC extensions. RiftShell intercepts this
    # session-specific title instead of displaying it as a window title.
    [Console]::Title = 'rift;TOKEN;' + $riftPayload
    $global:__RiftInvocationFailed = $false
    'PS ' + $riftLocation.Path + '> '
}
""".replace("TOKEN", token)
    return base64.b64encode(script.encode("utf-16-le")).decode("ascii")


class PromptDecoder:
    """Extract only our OSC messages, including messages split across reads.

    This is completion bookkeeping, not a security boundary: a shell process
    can inspect its own prompt. Never interpret a marker as action approval.
    """
    def __init__(self, token: str):
        self.prefixes = (f"\x1b]0;rift;{token};", f"\x1b]2;rift;{token};")
        self.pending = ""

    def feed(self, text: str) -> list[tuple[str, object]]:
        self.pending += text
        events = []
        while self.pending:
            matches = [(self.pending.find(prefix), prefix) for prefix in self.prefixes if prefix in self.pending]
            start, prefix = min(matches) if matches else (-1, "")
            if start < 0:
                keep = 0
                for candidate in self.prefixes:
                    for length in range(1, min(len(candidate), len(self.pending) + 1)):
                        if self.pending.endswith(candidate[:length]):
                            keep = max(keep, length)
                visible = self.pending[:-keep] if keep else self.pending
                if visible:
                    events.append(("output", visible))
                self.pending = self.pending[-keep:] if keep else ""
                break
            if start:
                events.append(("output", self.pending[:start]))
                self.pending = self.pending[start:]
            endings = [(self.pending.find(end, len(prefix)), len(end)) for end in ("\x07", "\x1b\\") if self.pending.find(end, len(prefix)) >= 0]
            if not endings:
                if len(self.pending) > 65536:
                    events.append(("output", self.pending))
                    self.pending = ""
                break
            end, end_length = min(endings)
            packet, terminator, self.pending = self.pending[:end], self.pending[end:end + end_length], self.pending[end + end_length:]
            try:
                state = json.loads(base64.b64decode(packet[len(prefix):], validate=True).decode("utf-8"))
                if (not isinstance(state, dict)
                        or type(state.get("sequence")) is not int
                        or type(state.get("exit_code")) is not int
                        or not isinstance(state.get("cwd"), str)
                        or type(state.get("filesystem")) is not bool):
                    raise ValueError("Invalid prompt state")
                events.append(("prompt", state))
            except (ValueError, UnicodeError, TypeError):
                events.append(("output", packet + terminator))
        return events


def output_excerpt(text: str) -> str:
    # Keep observations bounded, and remove terminal control sequences before
    # sending an execution result to Orbit. Raw VT data belongs only in the UI.
    text = re.sub(r"\x1b\].*?(?:\x07|\x1b\\)", "", text, flags=re.S)
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
    text = re.sub(r"\x1b[@-_]", "", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()[-16000:]


class NativeTerminal:
    def __init__(self, cwd: Path, rows: int = 24, columns: int = 100):
        self.events: queue.Queue = queue.Queue(maxsize=256)
        self.token = uuid.uuid4().hex
        self.cwd = cwd
        self.dimensions = (rows, columns)
        self.shell_name = "PowerShell"
        self._process = None
        self._closing = threading.Event()
        self._requests: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True, name="rift-pty")

    def start(self):
        self._thread.start()

    def _emit(self, kind: str, payload):
        while not self._closing.is_set():
            try:
                self.events.put((kind, payload), timeout=0.1)
                return
            except queue.Full:
                continue

    def write(self, text: str):
        if not self._closing.is_set():
            self._requests.put(("write", text))

    def resize(self, rows: int, columns: int):
        self.dimensions = (max(2, rows), max(10, columns))
        self._requests.put(("resize", self.dimensions))

    def close(self):
        # Destruction happens in the worker; closing a tab never waits for IO.
        self._closing.set()

    @property
    def stopped(self) -> bool:
        return not self._thread.is_alive()

    def _run(self):
        process = None
        try:
            from winpty import PTY
            shell = shutil.which("pwsh.exe") or shutil.which("powershell.exe")
            if not shell:
                raise RuntimeError("PowerShell was not found on PATH.")
            self.shell_name = Path(shell).stem
            rows, columns = self.dimensions
            process = PTY(columns, rows, backend=0)
            process.spawn(
                shell, cwd=str(self.cwd),
                env="\0".join(f"{key}={value}" for key, value in os.environ.items()) + "\0",
                cmdline=" " + subprocess.list2cmdline(["-NoLogo", "-NoExit", "-EncodedCommand", powershell_startup(self.token)]),
            )
            self._process = process
            decoder = PromptDecoder(self.token)
            while not self._closing.is_set():
                # A single transport owner avoids read/close races and avoids
                # PtyProcess's extra loopback-socket reader thread entirely.
                for _ in range(64):
                    try:
                        kind, payload = self._requests.get_nowait()
                    except queue.Empty:
                        break
                    if kind == "write":
                        process.write(payload)
                    elif kind == "resize":
                        process.set_size(payload[1], payload[0])
                try:
                    chunk = process.read(8192, blocking=False)
                except EOFError:
                    break
                if chunk:
                    for event in decoder.feed(chunk):
                        self._emit(*event)
                elif not process.isalive() or process.iseof():
                    break
                else:
                    self._closing.wait(0.016)
        except Exception as exc:
            self._emit("error", f"Native terminal failed: {exc}")
        finally:
            if process is not None:
                try:
                    # Terminate the complete tree, including dev-server reload
                    # children, before releasing the pseudoconsole handles.
                    if process.isalive():
                        subprocess.run(
                            ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            creationflags=subprocess.CREATE_NO_WINDOW, timeout=10,
                        )
                except Exception:
                    self._emit("error", "Could not terminate the terminal process tree. Check running processes before restarting the task.")
            self._emit("exit", None)
            self._process = None
            # Dropping the last PTY reference closes the ConPTY handles.
            process = None
