"""Mesale Play's library readers against small copies of each launcher's real files.

Run: python3 -m unittest discover tests/play
"""
import json
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../packages/mesale-play/usr/lib/mesale/play"))
import library  # noqa: E402


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def touch(path):
    write(path, "")


def manifest(appid, name, flags=4, last=0):
    return f'''"AppState"
{{
\t"appid"\t\t"{appid}"
\t"Universe"\t\t"1"
\t"name"\t\t"{name}"
\t"StateFlags"\t\t"{flags}"
\t"LastPlayed"\t\t"{last}"
\t"installdir"\t\t"{name}"
}}
'''


class LibraryTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.old_home = os.environ.get("HOME")
        os.environ["HOME"] = self.home

    def tearDown(self):
        os.environ["HOME"] = self.old_home

    def path(self, *parts):
        return os.path.join(self.home, *parts)

    def test_vdf(self):
        tree = library.parse_vdf('"a" { "b" "1" "c" { "d" "x \\"y\\"" } } ')
        self.assertEqual(tree, {"a": {"b": "1", "c": {"d": 'x "y"'}}})

    def test_steam(self):
        root = self.path(".var/app/com.valvesoftware.Steam/.local/share/Steam")
        other = self.path("Games/SteamLibrary")
        write(f"{root}/steamapps/libraryfolders.vdf", f'''"libraryfolders"
{{
\t"0" {{ "path" "{root}" "apps" {{ "620" "1" }} }}
\t"1" {{ "path" "{other}" }}
}}''')
        write(f"{root}/steamapps/appmanifest_620.acf", manifest(620, "Portal 2", last=1700000000))
        write(f"{other}/steamapps/appmanifest_1091500.acf", manifest(1091500, "Cyberpunk 2077"))
        write(f"{root}/steamapps/appmanifest_2348590.acf", manifest(2348590, "Proton 9.0"))
        write(f"{root}/steamapps/appmanifest_228980.acf", manifest(228980, "Steamworks Common Redistributables"))
        write(f"{root}/steamapps/appmanifest_400.acf", manifest(400, "Portal", flags=1026))   # still downloading
        write(f"{root}/userdata/123/config/localconfig.vdf", '''"UserLocalConfigStore" { "Software" { "Valve" {
            "Steam" { "apps" { "1091500" { "LastPlayed" "1710000000" } } } } } }''')
        touch(f"{root}/appcache/librarycache/620_library_600x900.jpg")
        touch(f"{root}/appcache/librarycache/1091500/a1b2c3/library_600x900.jpg")
        touch(f"{root}/appcache/librarycache/1091500/library_hero.jpg")

        games = {g.title: g for g in library.steam_games()}
        self.assertEqual(set(games), {"Portal 2", "Cyberpunk 2077"})
        self.assertEqual(games["Portal 2"].launch, "steam://rungameid/620")
        self.assertTrue(games["Portal 2"].cover.endswith("620_library_600x900.jpg"))
        self.assertTrue(games["Cyberpunk 2077"].cover.endswith("a1b2c3/library_600x900.jpg"))
        self.assertTrue(games["Cyberpunk 2077"].hero.endswith("library_hero.jpg"))
        self.assertEqual(games["Cyberpunk 2077"].last_played, 1710000000)
        self.assertEqual(games["Portal 2"].last_played, 1700000000)

    def test_heroic(self):
        root = self.path(".config/heroic")
        write(f"{root}/legendaryConfig/legendary/installed.json", json.dumps({
            "Fortnite": {"app_name": "Fortnite", "title": "Fortnite", "is_dlc": False},
            "SomeDLC": {"app_name": "SomeDLC", "title": "A DLC", "is_dlc": True}}))
        write(f"{root}/store_cache/legendary_library.json", json.dumps({"library": [
            {"app_name": "Fortnite", "title": "Fortnite", "art_square": "https://cdn.example/fn.jpg"}]}))
        write(f"{root}/gog_store/installed.json", json.dumps({"installed": [
            {"appName": "1207658924", "platform": "linux", "install_path": "/games/witcher"}]}))
        write(f"{root}/store_cache/gog_library.json", json.dumps({"games": [
            {"app_name": "1207658924", "title": "The Witcher: Enhanced Edition", "art_cover": "https://cdn.example/w.jpg"}]}))
        write(f"{root}/nile_config/nile/installed.json", json.dumps([{"id": "amzn1.adg", "path": "/games/x"}]))
        write(f"{root}/store_cache/nile_library.json", json.dumps({"library": [
            {"app_name": "amzn1.adg", "title": "Amazon Game"}]}))
        write(f"{root}/sideload_apps/library.json", json.dumps({"games": [
            {"app_name": "abc", "title": "My Emulator", "is_installed": True}]}))
        write(f"{root}/store/timestamp.json", json.dumps({"Fortnite": {"lastPlayed": "2024-05-01T10:00:00.000Z"}}))

        games = {g.title: g for g in library.heroic_games()}
        self.assertEqual(set(games), {"Fortnite", "The Witcher: Enhanced Edition", "Amazon Game", "My Emulator"})
        self.assertEqual(games["Fortnite"].launch, "heroic://launch/legendary/Fortnite")
        self.assertEqual(games["Fortnite"].cover, "https://cdn.example/fn.jpg")
        self.assertGreater(games["Fortnite"].last_played, 1700000000)
        self.assertEqual(games["The Witcher: Enhanced Edition"].source, "GOG")
        self.assertEqual(games["Amazon Game"].launch, "heroic://launch/nile/amzn1.adg")

    def test_lutris(self):
        root = self.path(".local/share/lutris")
        os.makedirs(root)
        db = sqlite3.connect(f"{root}/pga.db")
        db.execute("CREATE TABLE games (id INTEGER PRIMARY KEY, name TEXT, slug TEXT, runner TEXT, "
                   "installed INTEGER, lastplayed INTEGER, hidden INTEGER)")
        db.executemany("INSERT INTO games VALUES (?, ?, ?, ?, ?, ?, ?)", [
            (1, "Diablo II", "diablo-ii", "wine", 1, 1720000000, 0),
            (2, "Portal 2", "portal-2", "steam", 1, 0, 0),        # imported from Steam: skipped
            (3, "Not installed", "not-installed", "wine", 0, 0, 0),
            (4, "Hidden", "hidden", "wine", 1, 0, 1),
        ])
        db.commit()
        db.close()
        touch(f"{root}/coverart/diablo-ii.jpg")

        games = library.lutris_games()
        self.assertEqual([g.title for g in games], ["Diablo II"])
        self.assertEqual(games[0].launch, "lutris:rungameid/1")
        self.assertTrue(games[0].cover.endswith("coverart/diablo-ii.jpg"))

    def test_load_sorts_and_survives_errors(self):
        def broken():
            raise RuntimeError("bad library")
        readers = library.READERS
        library.READERS = [broken, lambda: [library.Game("b", "Beta", "Steam", "x"),
                                            library.Game("a", "alpha", "Steam", "x"),
                                            library.Game("c", "Recent", "Steam", "x", last_played=5)]]
        try:
            self.assertEqual([g.title for g in library.load()], ["Recent", "alpha", "Beta"])
        finally:
            library.READERS = readers

    def test_nothing_installed(self):
        self.assertEqual(library.load(), [])


if __name__ == "__main__":
    unittest.main()
