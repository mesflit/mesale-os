"""Installed games from Steam, Heroic (Epic, GOG, Amazon, sideloaded) and Lutris.

Only local files are read: no accounts, no network. Native and Flatpak installs both
count. Every reader fails on its own: a broken library never hides the others.
"""
import glob
import json
import os
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Game:
    key: str              # unique across sources, e.g. "steam:620"
    title: str
    source: str           # Steam, Epic, GOG, Amazon, Heroic, Lutris
    launch: str           # URI that starts the game through its launcher
    cover: str = ""       # local file or https URL, portrait
    hero: str = ""        # local file, wide background
    last_played: int = 0  # Unix time, 0 when never
    extra: dict = field(default_factory=dict)


# Steam ---------------------------------------------------------------------------

STEAM_ROOTS = [
    "~/.local/share/Steam",
    "~/.steam/steam",
    "~/.var/app/com.valvesoftware.Steam/.local/share/Steam",
    "~/.var/app/com.valvesoftware.Steam/data/Steam",
]
# Proton, runtimes and redistributables are installed like games but are not games
STEAM_TOOLS = re.compile(r"^(Proton|Steam Linux Runtime|Steamworks Common|SteamVR|Steam Audio)", re.I)
STEAM_INSTALLED = 4   # StateFlags bit: fully installed


def parse_vdf(text):
    """Valve's text KeyValues format into nested dicts. Keys are kept as written."""
    tokens = re.findall(r'"((?:[^"\\]|\\.)*)"|([{}])', text)
    root, stack, key = {}, [], None
    current = root
    for string, brace in tokens:
        if brace == "{":
            child = {}
            current[key] = child
            stack.append(current)
            current, key = child, None
        elif brace == "}":
            current = stack.pop() if stack else root
            key = None
        elif key is None:
            key = string
        else:
            current[key] = string.replace('\\"', '"').replace("\\\\", "\\")
            key = None
    return root


def lower_keys(tree):
    return {k.lower(): lower_keys(v) if isinstance(v, dict) else v for k, v in tree.items()}


def read_vdf(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return lower_keys(parse_vdf(f.read()))


def steam_libraries(root):
    folders = {os.path.join(root, "steamapps")}
    for name in ("steamapps/libraryfolders.vdf", "config/libraryfolders.vdf"):
        path = os.path.join(root, name)
        if not os.path.exists(path):
            continue
        for entry in read_vdf(path).get("libraryfolders", {}).values():
            if isinstance(entry, dict) and entry.get("path"):
                folders.add(os.path.join(entry["path"], "steamapps"))
    return sorted(f for f in folders if os.path.isdir(f))


def steam_last_played(root):
    """{appid: time} from every user's localconfig.vdf."""
    played = {}
    for path in glob.glob(os.path.join(root, "userdata", "*", "config", "localconfig.vdf")):
        try:
            apps = (read_vdf(path).get("userlocalconfigstore", {}).get("software", {})
                    .get("valve", {}).get("steam", {}).get("apps", {}))
        except OSError:
            continue
        for appid, values in apps.items():
            if isinstance(values, dict) and values.get("lastplayed", "").isdigit():
                played[appid] = max(played.get(appid, 0), int(values["lastplayed"]))
    return played


def steam_art(root, appid, name):
    """Library artwork: the old flat cache and the newer per-app folders."""
    cache = os.path.join(root, "appcache", "librarycache")
    found = glob.glob(os.path.join(cache, f"{appid}_{name}.jpg"))
    found += glob.glob(os.path.join(cache, appid, f"{name}.jpg"))
    found += glob.glob(os.path.join(cache, appid, "*", f"{name}.jpg"))
    return found[0] if found else ""


def steam_games():
    games, seen_roots = {}, set()
    for root in (os.path.expanduser(r) for r in STEAM_ROOTS):
        real = os.path.realpath(root)
        if not os.path.isdir(root) or real in seen_roots:
            continue
        seen_roots.add(real)
        played = steam_last_played(root)
        for library in steam_libraries(root):
            for manifest in glob.glob(os.path.join(library, "appmanifest_*.acf")):
                try:
                    state = read_vdf(manifest).get("appstate", {})
                except OSError:
                    continue
                appid, name = state.get("appid", ""), state.get("name", "")
                flags = int(state.get("stateflags", "0") or 0)
                if not appid or not name or STEAM_TOOLS.match(name) or appid == "228980" or not flags & STEAM_INSTALLED:
                    continue
                last = max(played.get(appid, 0), int(state.get("lastplayed", "0") or 0))
                games[appid] = Game(
                    key=f"steam:{appid}", title=name, source="Steam", launch=f"steam://rungameid/{appid}",
                    cover=steam_art(root, appid, "library_600x900"), hero=steam_art(root, appid, "library_hero"),
                    last_played=last)
    return list(games.values())


# Heroic --------------------------------------------------------------------------

HEROIC_ROOTS = ["~/.config/heroic", "~/.var/app/com.heroicgameslauncher.hgl/config/heroic"]


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def heroic_store(root, *names):
    """{app_name: entry} from Heroic's cached store libraries: titles and artwork URLs."""
    entries = {}
    for name in names:
        data = load_json(os.path.join(root, name), {})
        items = (data.get("library") or data.get("games") or []) if isinstance(data, dict) else data
        for item in items or []:
            if isinstance(item, dict) and item.get("app_name"):
                entries[item["app_name"]] = item
    return entries


def heroic_played(root):
    """{app_name: time} from Heroic's play time records (milliseconds or ISO dates)."""
    played = {}
    data = load_json(os.path.join(root, "store", "timestamp.json"), {})
    for app, record in (data or {}).items():
        value = record.get("lastPlayed") if isinstance(record, dict) else None
        if isinstance(value, (int, float)):
            played[app] = int(value / 1000 if value > 1e11 else value)
        elif isinstance(value, str):
            try:
                played[app] = int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
            except ValueError:
                pass
    return played


def heroic_game(runner, source, app, title, store, played):
    info = store.get(app, {})
    cover = info.get("art_square") or info.get("art_cover") or ""
    return Game(key=f"heroic:{runner}:{app}", title=title or info.get("title") or app, source=source,
                launch=f"heroic://launch/{runner}/{app}", cover=cover, last_played=played.get(app, 0))


def heroic_games():
    games = {}
    for root in (os.path.expanduser(r) for r in HEROIC_ROOTS):
        if not os.path.isdir(root):
            continue
        played = heroic_played(root)

        epic = heroic_store(root, "store_cache/legendary_library.json", "lib-cache/library.json")
        installed = load_json(os.path.join(root, "legendaryConfig/legendary/installed.json"), {}) or {}
        for app, entry in installed.items():
            if isinstance(entry, dict) and not entry.get("is_dlc"):
                game = heroic_game("legendary", "Epic", app, entry.get("title"), epic, played)
                games[game.key] = game

        gog = heroic_store(root, "store_cache/gog_library.json", "gog_store/library.json")
        for entry in (load_json(os.path.join(root, "gog_store/installed.json"), {}) or {}).get("installed", []):
            app = str(entry.get("appName", ""))
            if app and not entry.get("is_dlc"):
                game = heroic_game("gog", "GOG", app, entry.get("title"), gog, played)
                games[game.key] = game

        amazon = heroic_store(root, "store_cache/nile_library.json")
        for entry in load_json(os.path.join(root, "nile_config/nile/installed.json"), []) or []:
            app = entry.get("id", "") if isinstance(entry, dict) else ""
            if app:
                game = heroic_game("nile", "Amazon", app, None, amazon, played)
                games[game.key] = game

        side = heroic_store(root, "sideload_apps/library.json")
        for app, entry in side.items():
            if entry.get("is_installed", True):
                game = heroic_game("sideload", "Heroic", app, entry.get("title"), side, played)
                games[game.key] = game
    return list(games.values())


# Lutris --------------------------------------------------------------------------

LUTRIS_ROOTS = ["~/.local/share/lutris", "~/.var/app/net.lutris.Lutris/data/lutris"]
LUTRIS_CACHES = ["~/.cache/lutris", "~/.var/app/net.lutris.Lutris/cache/lutris"]


def lutris_cover(root, slug):
    folders = [os.path.join(root, "coverart"), os.path.join(root, "banners")]
    folders += [os.path.join(os.path.expanduser(c), "coverart") for c in LUTRIS_CACHES]
    for folder in folders:
        for ext in ("jpg", "png", "webp"):
            path = os.path.join(folder, f"{slug}.{ext}")
            if os.path.exists(path):
                return path
    return ""


def lutris_games():
    games = {}
    for root in (os.path.expanduser(r) for r in LUTRIS_ROOTS):
        path = os.path.join(root, "pga.db")
        if not os.path.exists(path):
            continue
        try:
            # Read only, so a running Lutris is never disturbed
            db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
            db.row_factory = sqlite3.Row
            columns = {row[1] for row in db.execute("PRAGMA table_info(games)")}
            hidden = "AND (hidden IS NULL OR hidden = 0)" if "hidden" in columns else ""
            rows = db.execute(f"SELECT * FROM games WHERE installed = 1 {hidden}").fetchall()
            db.close()
        except sqlite3.Error:
            continue
        for row in rows:
            # Steam games Lutris imported are already listed from Steam itself
            if (row["runner"] or "") == "steam" or not row["name"]:
                continue
            slug = row["slug"] or ""
            games[f"lutris:{row['id']}"] = Game(
                key=f"lutris:{row['id']}", title=row["name"], source="Lutris",
                launch=f"lutris:rungameid/{row['id']}", cover=lutris_cover(root, slug),
                last_played=int(row["lastplayed"] or 0) if "lastplayed" in columns else 0)
    return list(games.values())


# All -----------------------------------------------------------------------------

READERS = [steam_games, heroic_games, lutris_games]
SOURCES = ["Steam", "Epic", "GOG", "Amazon", "Heroic", "Lutris"]


def load():
    """Every installed game, recently played first, then by title."""
    games = []
    for reader in READERS:
        try:
            games += reader()
        except Exception as error:   # one broken launcher must not hide the rest
            print(f"Mesale Play: {reader.__name__}: {error}")
    return sorted(games, key=lambda g: (-g.last_played, g.title.casefold()))
