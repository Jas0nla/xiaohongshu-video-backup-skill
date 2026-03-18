#!/usr/bin/env python3
import shutil
from pathlib import Path

import importlib.resources

if not hasattr(importlib.resources, "files"):
    import importlib_resources

    importlib.resources.files = importlib_resources.files

from setuptools import setup


ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "Xiaohongshu Video Backup"
APP_DIR = ROOT / "dist" / f"{APP_NAME}.app"
ICON_FILE = ROOT / "assets" / "app-icon.icns"


def collect_files(folder: Path) -> list:
    files = []
    for path in folder.rglob("*"):
        if path.is_dir():
            continue
        if path.name == ".DS_Store":
            continue
        if path.suffix == ".pyc":
            continue
        if "__pycache__" in path.parts:
            continue
        files.append(str(path))
    return files


def main() -> None:
    if APP_DIR.exists():
        shutil.rmtree(APP_DIR)

    setup(
        app=[str(ROOT / "mac_app" / "app.py")],
        name=APP_NAME,
        data_files=[
            ("app/skill", collect_files(ROOT / "skill")),
        ],
        options={
            "py2app": {
                "argv_emulation": False,
                "plist": {
                    "CFBundleName": APP_NAME,
                    "CFBundleDisplayName": APP_NAME,
                    "CFBundleIdentifier": "cc.greenvideo.xiaohongshu-backup",
                    "CFBundleShortVersionString": "1.0",
                    "CFBundleVersion": "1",
                    "LSMinimumSystemVersion": "13.0",
                },
                "packages": [],
                "includes": ["tkinter"],
                "iconfile": str(ICON_FILE) if ICON_FILE.exists() else None,
                "site_packages": True,
            }
        },
        setup_requires=["py2app"],
        script_args=["py2app"],
    )

    print(f"Built app bundle: {APP_DIR}")


if __name__ == "__main__":
    main()
