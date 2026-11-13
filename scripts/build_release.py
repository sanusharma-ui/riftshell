"""scripts/build_release.py - Build RiftShell release and update version.json manifest.

Usage:
    python scripts/build_release.py [--skip-tests] [--onedir]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def get_version() -> str:
    version_file = ROOT / "version.py"
    namespace = {}
    exec(version_file.read_text(encoding="utf-8"), namespace)
    return namespace.get("__version__", "1.0.0")


def run_tests() -> bool:
    print("\n[1/5] Running tests with pytest...")
    res = subprocess.run(
        [sys.executable, "-m", "pytest", "tests"],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    return res.returncode == 0


def build_pyinstaller(onefile: bool = True) -> Path:
    print(f"\n[2/5] Building executable with PyInstaller (mode: {'--onefile' if onefile else '--onedir'})...")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile" if onefile else "--onedir",
        "--windowed",
        "--name",
        "RiftShell",
        "--icon",
        str(ROOT / "assets" / "icon.ico"),
        "--collect-submodules",
        "keyring.backends",
        "--add-data",
        f"{ROOT / 'plugins'};plugins",
        "--add-data",
        f"{ROOT / 'assets' / 'intent-model'};assets/intent-model",
        "--add-data",
        f"{ROOT / 'assets' / 'icon.ico'};assets",
        str(ROOT / "main.py"),
    ]
    res = subprocess.run(cmd, cwd=ROOT)
    if res.returncode != 0:
        raise RuntimeError("PyInstaller build failed.")

    if onefile:
        exe_path = ROOT / "dist" / "RiftShell.exe"
    else:
        exe_path = ROOT / "dist" / "RiftShell" / "RiftShell.exe"

    if not exe_path.exists():
        raise FileNotFoundError(f"Expected output binary not found: {exe_path}")
    return exe_path


def compute_sha256(file_path: Path) -> str:
    print(f"\n[3/5] Computing SHA-256 for {file_path.name}...")
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    digest = hasher.hexdigest()
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
    print(f"Updated {manifest_path} with version {version} and hash.")


def create_zip_release(version: str, exe_path: Path, onefile: bool) -> Path:
    print("\n[5/5] Creating ZIP release archive...")
    zip_name = f"RiftShell-v{version}-windows.zip"
    zip_path = ROOT / zip_name

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if onefile:
            zf.write(exe_path, "RiftShell.exe")
            license_path = ROOT / "LICENSE"
            if license_path.exists():
                zf.write(license_path, "LICENSE")
            readme_path = ROOT / "README.md"
            if readme_path.exists():
                zf.write(readme_path, "README.md")
        else:
            folder = exe_path.parent
            for file in folder.rglob("*"):
                arcname = file.relative_to(folder.parent)
                zf.write(file, arcname)

    print(f"Created ZIP: {zip_path} ({zip_path.stat().st_size / (1024*1024):.1f} MB)")
    return zip_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build RiftShell release.")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest test suite")
    parser.add_argument("--onedir", action="store_true", help="Build as onedir instead of onefile")
    args = parser.parse_args()

    version = get_version()
    print(f"=== Preparing RiftShell v{version} Release ===")

    if not args.skip_tests:
        if not run_tests():
            print("\n[ERROR] Tests failed! Aborting release build.")
            sys.exit(1)
    else:
        print("\n[1/5] Skipping tests as requested.")

    onefile = not args.onedir
    exe_path = build_pyinstaller(onefile=onefile)
    sha = compute_sha256(exe_path)
    update_manifest(version, sha)
    create_zip_release(version, exe_path, onefile=onefile)

    print("\n" + "=" * 50)
    print(f"SUCCESS! RiftShell v{version} is ready for release.")
    print("Next Steps:")
    print("1. git add updater.py version.json")
    print(f"2. git commit -m \"Release v{version}\"")
    print("3. git push origin main")
    print(f"4. Go to https://github.com/sanusharma-ui/riftshell/releases/new")
    print(f"   - Tag: v{version}")
    print(f"   - Upload: dist/RiftShell.exe AND/OR RiftShell-v{version}-windows.zip")
    print("   - Click 'Publish release'")
    print("=" * 50)


if __name__ == "__main__":
    main()
