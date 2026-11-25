#!/usr/bin/env python3
"""Render the film frame by frame: render.py FOLDER FRAMES_PER_SECOND | ffmpeg -f image2pipe ..."""
import pathlib
import sys

from playwright.sync_api import sync_playwright

folder, fps = pathlib.Path(sys.argv[1]).resolve(), int(sys.argv[2])
times = [float(t) for t in sys.argv[3:]]   # optional: only these moments

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(args=["--no-sandbox", "--allow-file-access-from-files"])
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    page.goto(folder.joinpath("index.html").as_uri())
    page.evaluate("document.fonts.ready")
    page.evaluate("Promise.all([...document.images].map(i => i.decode()))")
    duration = page.evaluate("DURATION")
    for t in times or [frame / fps for frame in range(int(duration * fps))]:
        page.evaluate("t => seek(t)", t)
        sys.stdout.buffer.write(page.screenshot(type="jpeg", quality=94))
    browser.close()
