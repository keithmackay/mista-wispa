"""
Build mista-wispa as a macOS .app bundle.

Usage: python setup_app.py py2app
"""
from setuptools import setup

APP = ["src/mista_wispa/app.py"]
DATA_FILES = [("resources", ["resources/menubar-icon.png", "resources/menubar-icon@2x.png"])]
OPTIONS = {
    "argv_emulation": False,
    "iconfile": "resources/mista-wispa.icns",
    "plist": {
        "CFBundleName": "mista-wispa",
        "CFBundleDisplayName": "mista-wispa",
        "CFBundleIdentifier": "com.mistawispa.app",
        "CFBundleVersion": "0.1.0",
        "CFBundleShortVersionString": "0.1.0",
        "LSUIElement": True,  # Menu bar app — no dock icon
        "NSMicrophoneUsageDescription": "mista-wispa needs microphone access for voice dictation.",
    },
    "packages": ["mista_wispa", "rumps", "mlx_whisper", "silero_vad", "torch", "numpy", "sounddevice", "openai"],
    "includes": [
        "AppKit",
        "ApplicationServices",
        "CoreFoundation",
        "Quartz",
    ],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
)
