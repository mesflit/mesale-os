#!/usr/bin/env python3
"""Fill template.html with the real features, looks and release data."""
import argparse
import html
import json
import pathlib
import re

REPO = "https://github.com/mesflit/mesaleos"
GROUPS = {"apps": "Applications", "system": "System", "drivers": "Drivers", "terminal": "Terminal",
          "gaming": "Gaming", "development": "Development", "more": "More apps"}
SCREENSHOTS = {"desktop": "The desktop", "command-bar": "Command bar", "center": "Mesale Center",
               "installer": "Installer", "dark": "Night look"}

parser = argparse.ArgumentParser()
parser.add_argument("--film-features")
for option in ("features", "looks", "screenshots", "version", "codename", "template"):
    parser.add_argument(f"--{option}", default="")
args = parser.parse_args()
esc = html.escape


def field(text, key):
    match = re.search(rf'^{key}="?([^"\n]*)', text, re.M)
    return match[1] if match else ""


def features():
    groups = {}
    for path in sorted(pathlib.Path(args.features).iterdir()):
        text = path.read_text()
        groups.setdefault(field(text, "GROUP"), []).append((path.name, field(text, "NAME"), field(text, "DESC")))
    return groups


def feature_html(groups):
    out = []
    for key, title in GROUPS.items():
        checked = " checked" if key == "apps" else ""
        items = "".join(
            f'<li><label><input type="checkbox" id="f-{esc(i)}" value="{esc(i)}" data-group="{key}"{checked}>'
            f'<span><b>{esc(name)}</b> {esc(desc)}</span></label></li>'
            for i, name, desc in groups.get(key, []))
        out.append(f'<fieldset><legend>{title}</legend><ul>{items}</ul></fieldset>')
    return "\n".join(out)


def look_html(looks):
    return "".join(
        f'<button type="button" class="look" data-look="{k}" data-dark="{str(v["dark"]).lower()}" aria-pressed="{str(k == "day").lower()}">'
        f'<img src="img/{k}-thumb.webp" width="480" height="270" alt="" loading="lazy"><span>{esc(v["name"])}</span></button>'
        for k, v in looks.items())


def screenshot_html():
    figures = [f'<figure><img src="img/{k}.webp" width="1600" height="900" alt="{title} of Mesale OS" loading="lazy">'
               f'<figcaption>{title}</figcaption></figure>'
               for k, title in SCREENSHOTS.items() if (pathlib.Path(args.screenshots) / f"{k}.png").exists()]
    return f'<section class="shots wrap" id="screenshots"><h2>What it looks like</h2><div>{"".join(figures)}</div></section>' if figures else ""


if args.film_features:
    # A sample for the film: the first features of every group
    args.features = args.film_features
    names = [name for items in features().values() for _, name, _ in items[:4]]
    print(f"const FEATURES = {json.dumps(names[:28])};")
    raise SystemExit

groups = features()
values = {
    "VERSION": esc(args.version), "CODENAME": esc(args.codename), "REPO": REPO,
    "FEATURES": feature_html(groups), "FEATURE_COUNT": str(sum(map(len, groups.values()))),
    "LOOKS": look_html(json.loads(pathlib.Path(args.looks).read_text())), "SCREENSHOTS": screenshot_html(),
    "SEARCH": json.dumps([[n, d] for items in groups.values() for _, n, d in items]).replace("</", "<\\/"),
}
print(re.sub(r"\{\{(\w+)\}\}", lambda m: values[m[1]], pathlib.Path(args.template).read_text()))
