"""
Build mista-wispa as a macOS .app bundle using PyInstaller.

Usage: uv run python setup_app.py
"""
import subprocess
import sys
import os
import plistlib

APP_NAME = "mista-wispa"
ENTRY_POINT = "src/mista_wispa/app.py"
ICON_FILE = "resources/mista-wispa.icns"
RESOURCES = [
    ("resources/menubar-icon.png", "resources"),
    ("resources/menubar-icon@2x.png", "resources"),
]

# Additional Info.plist entries
PLIST_EXTRAS = {
    "LSUIElement": True,  # Menu bar app — no dock icon
    "NSMicrophoneUsageDescription": "mista-wispa needs microphone access for voice dictation.",
    "CFBundleIdentifier": "com.mistawispa.app",
}


def build():
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--windowed",  # .app bundle, no console window
        "--icon", ICON_FILE,
        "--noconfirm",  # overwrite previous build
        "--clean",
    ]

    # Add resource files
    for src, dst in RESOURCES:
        cmd.extend(["--add-data", f"{src}:{dst}"])

    # Add hidden imports that PyInstaller might miss
    for mod in ["rumps", "AppKit", "ApplicationServices", "CoreFoundation", "Quartz"]:
        cmd.extend(["--hidden-import", mod])

    cmd.append(ENTRY_POINT)

    print(f"Building {APP_NAME}.app...")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("Build failed.")
        sys.exit(1)

    # Patch Info.plist with extra entries
    plist_path = os.path.join("dist", f"{APP_NAME}.app", "Contents", "Info.plist")
    if os.path.exists(plist_path):
        with open(plist_path, "rb") as f:
            plist = plistlib.load(f)
        plist.update(PLIST_EXTRAS)
        with open(plist_path, "wb") as f:
            plistlib.dump(plist, f)
        print("Patched Info.plist with LSUIElement and NSMicrophoneUsageDescription.")

    print()
    print(f"Build complete: dist/{APP_NAME}.app")
    print()
    print("To install, copy to /Applications:")
    print(f"  cp -r dist/{APP_NAME}.app /Applications/")
    print()
    print("To run:")
    print(f"  open /Applications/{APP_NAME}.app")


if __name__ == "__main__":
    build()
