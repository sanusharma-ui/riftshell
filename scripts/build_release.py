"""scripts/build_release.py - Automated release builder and packager for RiftShell.

Usage:
    python scripts/build_release.py [--skip-tests] [--onedir]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def get_python_exe() -> str:
    """Find a Python executable that has PyInstaller, pytest, and dependencies installed."""
    candidates = [
        ROOT / ".venv-build" / "Scripts" / "python.exe",
        ROOT / ".venv" / "Scripts" / "python.exe",
        Path(sys.executable),
    ]
    for candidate in candidates:
        if candidate.exists():
            try:
                res = subprocess.run(
                    [str(candidate), "-c", "import PyInstaller, pytest; print('ok')"],
                    capture_output=True,
                    text=True,
                )
                if res.returncode == 0 and "ok" in res.stdout:
                    return str(candidate)
            except Exception:
                pass

    return sys.executable


def get_version() -> str:
    version_file = ROOT / "version.py"
    content = version_file.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    if match:
        return match.group(1)
    return "1.1.0"


def run_tests(python_exe: str) -> bool:
    print(f"\n[1/5] Running tests with pytest (using: {python_exe})...")
    temp_dir = ROOT / ".pytest_temp"
    temp_dir.mkdir(exist_ok=True)
    res = subprocess.run(
        [python_exe, "-m", "pytest", "tests", f"--basetemp={temp_dir}"],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    return res.returncode == 0


def build_pyinstaller(python_exe: str, onefile: bool = True) -> Path:
    mode_str = "--onefile" if onefile else "--onedir"
    print(f"\n[2/5] Building executable with PyInstaller ({mode_str})...")

    # Verify PyInstaller is installed
    check = subprocess.run(
        [python_exe, "-m", "PyInstaller", "--version"],
        capture_output=True,
        text=True,
    )
    if check.returncode != 0:
        print("\n[ERROR] PyInstaller is not installed in the selected Python environment:")
        print(f"        {python_exe}")
        print("        Install it with: pip install pyinstaller")
        raise RuntimeError("PyInstaller not found.")

    if not onefile and (ROOT / "RiftShell.spec").exists():
        # Use existing production spec file for onedir
        cmd = [
            python_exe,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            str(ROOT / "RiftShell.spec"),
        ]
        exe_path = ROOT / "dist" / "RiftShell" / "RiftShell.exe"
    else:
        # CLI command with all flags
        sep = os.pathsep
        cmd = [
            python_exe,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            mode_str,
            "--windowed",
            "--name",
            "RiftShell",
            "--icon",
            "assets/icon.ico",
            "--collect-submodules",
            "keyring.backends",
            "--add-data",
            f"plugins{sep}plugins",
            "--add-data",
            f"assets/intent-model{sep}assets/intent-model",
            "--add-data",
            f"assets/icon.ico{sep}assets",
            "main.py",
        ]
        if onefile:
            exe_path = ROOT / "dist" / "RiftShell.exe"
        else:
            exe_path = ROOT / "dist" / "RiftShell" / "RiftShell.exe"

    print(f"Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=ROOT)
    if res.returncode != 0:
        raise RuntimeError(f"PyInstaller build failed with exit code {res.returncode}.")

    if not exe_path.exists():
        raise FileNotFoundError(f"Expected output binary not found at: {exe_path}")

    print(f"Binary built successfully: {exe_path} ({exe_path.stat().st_size / (1024*1024):.1f} MB)")
    return exe_path


def compute_sha256(file_path: Path) -> str:
    print(f"\n[3/5] Computing SHA-256 for {file_path.name}...")
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    digest = hasher.hexdigest().lower()
    print(f"SHA-256: {digest}")
    return digest


def update_manifest(version: str, sha256_hash: str) -> None:
    print("\n[4/5] Updating version.json...")
    manifest_path = ROOT / "version.json"
    manifest = {
        "version": version,
        "url": f"https://github.com/sanusharma-ui/riftshell/releases/download/v{version}/RiftShell.exe",
        "sha256": sha256_hash,
        "notes": f"RiftShell v{version} release with Auto-Updater, command hints and stability improvements.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {manifest_path} (version: {version})")


def create_zip_release(version: str, exe_path: Path, onefile: bool) -> Path:
    print("\n[5/5] Creating ZIP release archive...")
    zip_name = f"RiftShell-v{version}-windows.zip"
    zip_path = ROOT / zip_name

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if onefile:
            zf.write(exe_path, "RiftShell.exe")
            for extra in ["LICENSE", "README.md"]:
                extra_path = ROOT / extra
                if extra_path.exists():
                    zf.write(extra_path, extra)
        else:
            folder = exe_path.parent  # dist/RiftShell
            for file in folder.rglob("*"):
                if file.is_file():
                    arcname = file.relative_to(folder.parent)  # RiftShell/...
                    zf.write(file, arcname)
            for extra in ["LICENSE", "README.md"]:
                extra_path = ROOT / extra
                arc_extra = f"RiftShell/{extra}"
                if extra_path.exists() and arc_extra not in zf.namelist():
                    zf.write(extra_path, arc_extra)

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"Created ZIP: {zip_path} ({size_mb:.1f} MB)")
    return zip_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build RiftShell release.")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest test suite")
    parser.add_argument("--onedir", action="store_true", help="Build directory package instead of single-file exe")
    args = parser.parse_args()

    python_exe = get_python_exe()
    version = get_version()

    print("=" * 60)
    print(f" RiftShell v{version} — Release Builder")
    print(f" Using Python: {python_exe}")
    print("=" * 60)

    if not args.skip_tests:
        if not run_tests(python_exe):
            print("\n[ERROR] Tests failed! Aborting release build.")
            sys.exit(1)
    else:
        print("\n[1/5] Skipping tests as requested.")

    onefile = not args.onedir
    exe_path = build_pyinstaller(python_exe, onefile=onefile)
    sha = compute_sha256(exe_path)
    update_manifest(version, sha)
    create_zip_release(version, exe_path, onefile=onefile)

    print("\n" + "=" * 60)
    print(f"🎉 SUCCESS! RiftShell v{version} build complete.")
    print("Next steps:")
    print(f"1. Go to: https://github.com/sanusharma-ui/riftshell/releases/new")
    print(f"   - Tag: v{version}")
    print(f"   - Upload: {exe_path.name} AND RiftShell-v{version}-windows.zip")
    print("   - Click 'Publish release'")
    print("\n2. Once release is published, push the update manifest to git:")
    print("   git add updater.py version.json")
    print(f"   git commit -m \"Release v{version}\"")
    print("   git push origin main")
    print("=" * 60)


if __name__ == "__main__":
    main()
