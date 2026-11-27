"""Cover images. Steam and Lutris keep theirs on disk; Heroic lists web addresses, which
are downloaded once in the background into ~/.cache/mesale-play/covers."""
import hashlib
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from gi.repository import GLib

CACHE = os.path.join(GLib.get_user_cache_dir(), "mesale-play", "covers")
pool = ThreadPoolExecutor(max_workers=4)


def cached(url):
    name = hashlib.sha1(url.encode()).hexdigest() + os.path.splitext(url.split("?")[0])[1][:5]
    return os.path.join(CACHE, name)


def download(url, path):
    request = urllib.request.Request(url, headers={"User-Agent": "Mesale Play"})
    with urllib.request.urlopen(request, timeout=15) as response:
        data = response.read(8 * 1024 * 1024)
    os.makedirs(CACHE, exist_ok=True)
    temporary = path + ".part"
    with open(temporary, "wb") as f:
        f.write(data)
    os.replace(temporary, path)
    return path


def get(source, on_ready):
    """Call on_ready(path) in the main loop once the cover is on disk; never for no cover."""
    if not source:
        return
    if not source.startswith(("http://", "https://")):
        if os.path.exists(source):
            on_ready(source)
        return
    path = cached(source)
    if os.path.exists(path):
        on_ready(path)
        return

    def work():
        try:
            GLib.idle_add(on_ready, download(source, path))
        except Exception as error:
            print(f"Mesale Play: cover {source}: {error}")
    pool.submit(work)
