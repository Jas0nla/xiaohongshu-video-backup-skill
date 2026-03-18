#!/usr/bin/env python3
import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT / "assets"
ICONSET_DIR = ASSETS_DIR / "AppIcon.iconset"
BASE_PNG = ASSETS_DIR / "app-icon-1024.png"
ICNS_PATH = ASSETS_DIR / "app-icon.icns"


def draw_icon(path: Path) -> None:
    size = 1024
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    for y in range(size):
        t = y / size
        color = (
            int(255 - 25 * t),
            int(123 + 55 * t),
            int(78 + 62 * t),
            255,
        )
        draw.line((0, y, size, y), fill=color)

    draw.rounded_rectangle(
        (72, 72, 952, 952),
        radius=220,
        outline=(255, 244, 230, 120),
        width=6,
    )

    draw.ellipse((130, 110, 890, 870), fill=(255, 244, 234, 34))
    draw.rounded_rectangle((196, 238, 828, 780), radius=126, fill=(255, 248, 241, 242))

    play_points = [(398, 350), (398, 666), (664, 508)]
    draw.polygon(play_points, fill=(233, 94, 51, 255))

    for idx, width in enumerate((224, 186, 148)):
        top = 372 + idx * 84
        left = 282 if idx == 0 else 304
        draw.rounded_rectangle(
            (left, top, left + width, top + 30),
            radius=15,
            fill=(51, 35, 28, 72),
        )

    for idx, width in enumerate((244, 210, 172)):
        top = 622 + idx * 58
        left = 268 if idx == 0 else 292
        draw.rounded_rectangle(
            (left, top, left + width, top + 22),
            radius=11,
            fill=(51, 35, 28, 60),
        )

    image.save(path)


def build_iconset(source: Path, iconset_dir: Path) -> None:
    if iconset_dir.exists():
        shutil.rmtree(iconset_dir)
    iconset_dir.mkdir(parents=True, exist_ok=True)

    sizes = [16, 32, 64, 128, 256, 512]
    for size in sizes:
        out1x = iconset_dir / f"icon_{size}x{size}.png"
        out2x = iconset_dir / f"icon_{size}x{size}@2x.png"
        subprocess.run(
            ["sips", "-z", str(size), str(size), str(source), "--out", str(out1x)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["sips", "-z", str(size * 2), str(size * 2), str(source), "--out", str(out2x)],
            check=True,
            capture_output=True,
        )


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    draw_icon(BASE_PNG)
    build_iconset(BASE_PNG, ICONSET_DIR)
    if ICNS_PATH.exists():
        ICNS_PATH.unlink()
    subprocess.run(["iconutil", "-c", "icns", str(ICONSET_DIR), "-o", str(ICNS_PATH)], check=True)
    print(ICNS_PATH)


if __name__ == "__main__":
    main()
