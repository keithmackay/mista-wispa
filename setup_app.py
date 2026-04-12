"""
Build mista-wispa as a macOS .app bundle.

Creates a lightweight .app wrapper that launches the uv-managed Python
environment. This avoids the complexity of bundling ML libraries (MLX,
torch) with PyInstaller/py2app.

Usage: uv run python setup_app.py
"""
import os
import plistlib
import shutil
import stat
import sys

APP_NAME = "mista-wispa"
BUNDLE_ID = "com.mistawispa.app"
VERSION = "0.1.0"


def build():
    # Resolve paths
    project_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(project_dir, ".venv", "bin", "python3")
    app_module = "mista_wispa.app"

    if not os.path.exists(venv_python):
        print(f"Error: {venv_python} not found. Run 'uv venv && uv pip install -e .' first.")
        sys.exit(1)

    # Build .app structure
    app_dir = os.path.join(project_dir, "dist", f"{APP_NAME}.app")
    contents = os.path.join(app_dir, "Contents")
    macos = os.path.join(contents, "MacOS")
    resources = os.path.join(contents, "Resources")

    # Clean previous build
    if os.path.exists(app_dir):
        shutil.rmtree(app_dir)

    os.makedirs(macos)
    os.makedirs(resources)

    # Create launcher script
    launcher_path = os.path.join(macos, APP_NAME)
    with open(launcher_path, "w") as f:
        f.write(f"""#!/bin/bash
# Launch mista-wispa from its project virtualenv
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd "{project_dir}"
exec "{venv_python}" -m {app_module}
""")
    os.chmod(launcher_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    # Create Info.plist
    plist = {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleVersion": VERSION,
        "CFBundleShortVersionString": VERSION,
        "CFBundleExecutable": APP_NAME,
        "CFBundleIconFile": "AppIcon",
        "CFBundlePackageType": "APPL",
        "LSUIElement": True,
        "NSMicrophoneUsageDescription": "mista-wispa needs microphone access for voice dictation.",
    }
    plist_path = os.path.join(contents, "Info.plist")
    with open(plist_path, "wb") as f:
        plistlib.dump(plist, f)

    # Copy icon
    icns_src = os.path.join(project_dir, "resources", "mista-wispa.icns")
    icns_dst = os.path.join(resources, "AppIcon.icns")
    if os.path.exists(icns_src):
        shutil.copy2(icns_src, icns_dst)

    print(f"Built: {app_dir}")
    print()
    print("To install:")
    print(f"  cp -r dist/{APP_NAME}.app /Applications/")
    print()
    print("To run:")
    print(f"  open /Applications/{APP_NAME}.app")


if __name__ == "__main__":
    build()
