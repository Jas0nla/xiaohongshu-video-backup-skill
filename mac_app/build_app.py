#!/usr/bin/env python3
import subprocess
import shutil
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "Xiaohongshu Video Backup"
APP_DIR = ROOT / "dist" / f"{APP_NAME}.app"
CONTENTS_DIR = APP_DIR / "Contents"
RESOURCES_DIR = CONTENTS_DIR / "Resources"
PAYLOAD_DIR = RESOURCES_DIR / "app"
APPLESCRIPT = """
on run
  set appRoot to POSIX path of ((path to me as text) & "Contents:Resources:app:")
  set workspacePath to POSIX path of ((path to documents folder as text) & "Xiaohongshu Video Backup")
  set shellCommand to "export XHS_BACKUP_APP_ROOT=" & quoted form of appRoot & "; export XHS_BACKUP_WORKSPACE=" & quoted form of workspacePath & "; /usr/bin/env python3 " & quoted form of (appRoot & "mac_app/app.py")
  tell application "Terminal"
    activate
    do script shellCommand
  end tell
end run
"""


def copy_tree(source: Path, target: Path) -> None:
    shutil.copytree(
        source,
        target,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )
def build_launcher_app(target: Path) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".applescript", delete=False) as handle:
        handle.write(APPLESCRIPT)
        script_path = Path(handle.name)
    try:
        subprocess.run(
            ["osacompile", "-o", str(target), str(script_path)],
            check=True,
        )
    finally:
        script_path.unlink(missing_ok=True)


def main() -> None:
    if APP_DIR.exists():
        shutil.rmtree(APP_DIR)

    build_launcher_app(APP_DIR)
    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)

    copy_tree(ROOT / "skill", PAYLOAD_DIR / "skill")
    copy_tree(ROOT / "mac_app", PAYLOAD_DIR / "mac_app")

    print(f"Built app bundle: {APP_DIR}")


if __name__ == "__main__":
    main()
