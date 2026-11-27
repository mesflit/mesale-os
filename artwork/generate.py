#!/usr/bin/env python3
"""Generate every image Mesale OS ships.

usage: generate.py OUTPUT [WIDTH]     needs numpy, pillow and rsvg-convert
"""
import json
import pathlib
import subprocess
import sys

from PIL import Image, ImageFilter

import aero
import glass
import logo
from looks import LOOKS

RENDER = {"glass": glass.render, "aero": aero.render}

OUT = pathlib.Path(sys.argv[1])
WIDTH = int(sys.argv[2]) if len(sys.argv) > 2 else 3840
SHARE = OUT / "usr/share"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def write_png(path, svg, width=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    size = ["-w", str(width)] if width else []
    subprocess.run(["rsvg-convert", "-o", str(path), *size], input=svg.encode(), check=True)


def wallpapers():
    folder, previews = SHARE / "backgrounds/mesale", SHARE / "mesale/previews"
    folder.mkdir(parents=True, exist_ok=True)
    previews.mkdir(parents=True, exist_ok=True)
    entries = []
    for key, look in LOOKS.items():
        image = RENDER[look.style](look, (WIDTH, WIDTH * 9 // 16))   # drawn at full size, not upscaled
        image.save(folder / f"{key}.jpg", quality=93, subsampling=0)
        image.resize((640, 360), Image.LANCZOS).save(previews / f"{key}.png")
        if key == "night":
            dimmed = image.resize((1920, 1080), Image.LANCZOS).point(lambda p: int(p * .55))
            dimmed.save(SHARE / "mesale/grub.png")
            # Login screen: already blurred, so it costs nothing to draw
            greeter = image.resize((1920, 1080), Image.LANCZOS).filter(ImageFilter.GaussianBlur(14))
            greeter.save(SHARE / "mesale/greeter.jpg", quality=92)
        entries.append(
            f'<wallpaper deleted="false"><name>{look.name}</name>'
            f'<filename>/usr/share/backgrounds/mesale/{key}.jpg</filename><options>zoom</options>'
            f'<pcolor>{look.sky[0]}</pcolor><scolor>{look.sky[1]}</scolor></wallpaper>')
    write(SHARE / "gnome-background-properties/mesale.xml",
          '<?xml version="1.0"?><!DOCTYPE wallpapers SYSTEM "gnome-wp-list.dtd"><wallpapers>'
          + "".join(entries) + "</wallpapers>")
    write(SHARE / "mesale/looks.json", json.dumps({k: {"name": v.name, "dark": v.dark} for k, v in LOOKS.items()}))


def brand():
    write(SHARE / "icons/hicolor/scalable/apps/mesale-logo.svg", logo.mark())
    write(SHARE / "icons/hicolor/scalable/apps/mesale-flame.svg", logo.mark(tile=False))
    write_png(SHARE / "pixmaps/mesale-logo.png", logo.mark(), 256)
    write_png(SHARE / "mesale/gdm-logo.png", logo.wordmark())
    write_png(SHARE / "plymouth/themes/mesale/logo.png", logo.mark(tile=False), 200)
    write_png(SHARE / "plymouth/themes/mesale/dot.png", logo.DOT)
    write(SHARE / "mesale/fastfetch.txt", logo.terminal())


wallpapers()
brand()
