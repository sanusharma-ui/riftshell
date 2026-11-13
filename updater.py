"""updater.py - Core RiftShell update checker, downloader, and installer.

Plain Python module: NO Qt imports.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from typing import Callable

from version import __version__

MANIFEST_URL = "https://raw.githubusercontent.com/sanusharma-ui/riftshell/main/version.json"


def parse_version(version_str: str) -> tuple[int, ...]:
    """Parse a version string like '1.1.0' into an integer tuple for comparison."""
    parts = re.findall(r"\d+", str(version_str))
    return tuple(int(p) for p in parts) if parts else (0,)


def check_update(timeout: int = 5) -> dict | None:
    """Fetch update manifest and return it if a newer version is available.

    Returns None on any network or parse error silently.
    """
    try:
        req = urllib.request.Request(
            MANIFEST_URL,
            headers={"User-Agent": f"RiftShell/{__version__}"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        if not isinstance(data, dict):
            return None
        remote_version = data.get("version")
        if not remote_version:
            return None
        if parse_version(remote_version) > parse_version(__version__):
            return data
        return None
    except Exception:
        return None


def download_update(
    manifest: dict,
    on_progress: Callable[[int], None] | None = None,
    is_cancelled: Callable[[], bool] | None = None,
) -> str:
    """Download the new executable to temp directory, reporting progress 0-100.

    Verifies SHA-256 against manifest['sha256'] (case-insensitive).
    On mismatch or failure, deletes the file and raises RuntimeError.
    """
    url = manifest.get("url")
    if not url:
        raise ValueError("Update manifest does not contain a download URL.")

    dest = os.path.join(tempfile.gettempdir(), "RiftShell_new.exe")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": f"RiftShell/{__version__}"},
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            hasher = hashlib.sha256()

            with open(dest, "wb") as f:
                while True:
                    if is_cancelled and is_cancelled():
                        raise RuntimeError("Update download cancelled by user.")
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    hasher.update(chunk)
                    downloaded += len(chunk)
                    if total > 0 and on_progress:
                        pct = min(100, int((downloaded / total) * 100))
                        on_progress(pct)

            if on_progress:
                on_progress(100)

        expected_sha = manifest.get("sha256", "").strip().lower()
        actual_sha = hasher.hexdigest().lower()
        if expected_sha and actual_sha != expected_sha:
            if os.path.exists(dest):
                try:
                    os.remove(dest)
                except OSError:
                    pass
            raise RuntimeError("Checksum mismatch, update cancelled.")

        return dest
    except Exception:
        if os.path.exists(dest):
            try:
                os.remove(dest)
            except OSError:
                pass
        raise


def apply_update(new_exe: str) -> None:
    """Apply the downloaded executable over the current executable via a helper batch script.

    Only valid when running as a frozen executable (sys.frozen == True).
    Does NOT call sys.exit(); the caller is responsible for quitting the application.
    """
    if not getattr(sys, "frozen", False):
        raise RuntimeError("Updates work only in the built exe.")

    bat_path = os.path.join(tempfile.gettempdir(), "riftshell_update.bat")
    current_exe = sys.executable

    bat_content = f"""@echo off
set "TARGET={current_exe}"
set "NEW={new_exe}"
set "COUNT=0"

:retry
timeout /t 1 /nobreak >nul 2>&1 || ping 127.0.0.1 -n 2 >nul 2>&1
move /y "%NEW%" "%TARGET%" >nul 2>&1
if errorlevel 1 (
    set /a COUNT+=1
    if %COUNT% lss 15 goto retry
    del "%~f0"
    exit /b 1
)

start "" "%TARGET%"
del "%~f0"
"""

    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)

    flags = 0x08000000  # CREATE_NO_WINDOW
    subprocess.Popen(["cmd", "/c", bat_path], creationflags=flags)
