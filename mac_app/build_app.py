#!/usr/bin/env python3
import shutil
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "Xiaohongshu Video Backup"
APP_DIR = ROOT / "dist" / f"{APP_NAME}.app"
CONTENTS_DIR = APP_DIR / "Contents"
MACOS_DIR = CONTENTS_DIR / "MacOS"
RESOURCES_DIR = CONTENTS_DIR / "Resources"
PAYLOAD_DIR = RESOURCES_DIR / "app"


INFO_PLIST = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>en</string>
  <key>CFBundleDisplayName</key>
  <string>{APP_NAME}</string>
  <key>CFBundleExecutable</key>
  <string>xhs-backup</string>
  <key>CFBundleIdentifier</key>
  <string>cc.greenvideo.xiaohongshu-backup</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>{APP_NAME}</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>1.0</string>
  <key>CFBundleVersion</key>
  <string>1</string>
  <key>LSMinimumSystemVersion</key>
  <string>13.0</string>
  <key>LSUIElement</key>
  <false/>
</dict>
</plist>
"""


LAUNCHER = """#!/bin/zsh
set -e
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RESOURCES_DIR="$APP_DIR/Resources"
export XHS_BACKUP_APP_ROOT="$RESOURCES_DIR/app"
export XHS_BACKUP_WORKSPACE="${XHS_BACKUP_WORKSPACE:-$HOME/Documents/Xiaohongshu Video Backup}"
exec /usr/bin/env python3 "$RESOURCES_DIR/app/mac_app/app.py"
"""


def copy_tree(source: Path, target: Path) -> None:
    shutil.copytree(source, target, dirs_exist_ok=True)


def make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def main() -> None:
    if APP_DIR.exists():
        shutil.rmtree(APP_DIR)

    MACOS_DIR.mkdir(parents=True, exist_ok=True)
    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)

    copy_tree(ROOT / "skill", PAYLOAD_DIR / "skill")
    copy_tree(ROOT / "mac_app", PAYLOAD_DIR / "mac_app")

    (CONTENTS_DIR / "Info.plist").write_text(INFO_PLIST, encoding="utf-8")
    launcher_path = MACOS_DIR / "xhs-backup"
    launcher_path.write_text(LAUNCHER, encoding="utf-8")
    make_executable(launcher_path)

    print(f"Built app bundle: {APP_DIR}")


if __name__ == "__main__":
    main()
