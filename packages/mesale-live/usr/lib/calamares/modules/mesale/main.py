"""Mesale OS install job: drop live packages, apply look and chosen features.
A feature that fails (e.g. no network) never breaks the install; it is retried on first boot."""
import json, os, re, subprocess
import libcalamares
from libcalamares.utils import debug, warning

status = "Preparing Mesale OS"
def pretty_name(): return "Mesale OS features"
def pretty_status_message(): return status

LIVE = ["mesale-live", "live-boot", "live-boot-initramfs-tools", "live-config", "live-config-systemd", "live-tools", "calamares"]

def run():
    global status
    gs = libcalamares.globalstorage
    root = gs.value("rootMountPoint")
    def ch(*k, **kw):
        c = ["chroot", root, "env", "DEBIAN_FRONTEND=noninteractive", "MESALE_INSTALL=1", "LC_ALL=C.UTF-8", "PATH=/usr/sbin:/usr/bin:/sbin:/bin", *k]
        with open(root + "/var/log/mesale-install.log", "a") as g:
            r = subprocess.run(c, stdin=subprocess.DEVNULL, stdout=g, stderr=subprocess.STDOUT, **kw).returncode
        debug(f"{k} -> {r}")
        return r
    def has(p): return subprocess.run(["chroot", root, "dpkg", "-s", p], capture_output=True).returncode == 0
    os.makedirs(root + "/var/lib/mesale", exist_ok=True)
    # DNS inside the target: /run is an empty tmpfs there
    d = root + "/run/systemd/resolve"; os.makedirs(d, exist_ok=True)
    with open("/etc/resolv.conf") as a, open(d + "/stub-resolv.conf", "w") as b: b.write(a.read())

    status = "Removing live packages"; libcalamares.job.setprogress(0.02)
    ch("apt-mark", "manual", "cryptsetup-initramfs", "cryptsetup", "btrfs-progs", "xfsprogs", "dosfstools", "e2fsprogs", "efibootmgr", "sudo", "pciutils", "mesale-desktop", "xwayland")
    if ch("apt-get", "-y", "purge", "--autoremove", *[p for p in LIVE if has(p)]) != 0:
        return ("Could not remove live packages", "See /var/log/mesale-install.log")

    look = gs.value("packagechooser_look") or "day"
    walls = json.load(open("/usr/share/mesale/looks.json"))
    if look in walls:
        dark = walls[look]["dark"]
        uri = f"'file:///usr/share/backgrounds/mesale/{look}.jpg'"
        with open(root + "/etc/dconf/db/local.d/90-install", "w") as f:
            f.write(f"[org/mesale/shell]\ntheme-mode='{'dark' if dark else 'light'}'\n\n[org/gnome/desktop/interface]\ncolor-scheme='prefer-{'dark' if dark else 'light'}'\n\n"
                    f"[org/gnome/desktop/background]\npicture-uri={uri}\npicture-uri-dark={uri}\n\n[org/gnome/desktop/screensaver]\npicture-uri={uri}\n")
        ch("dconf", "update")

    chosen = set()
    for op in gs.value("packageOperations") or []:
        for k in ("install", "try_install"):
            for p in op.get(k, []):
                chosen.add(p if isinstance(p, str) else p.get("package") or p.get("name"))
    info = {}
    for n in os.listdir(root + "/usr/lib/mesale/features"):
        t = open(f"{root}/usr/lib/mesale/features/{n}").read()
        m = lambda k: (re.search(rf'^{k}="?([^"\n]*)', t, re.M) or [0, ""])[1]
        info[n] = (m("GROUP"), m("PKGS").split())
    # Preinstalled apps the user unchecked
    drop = [p for n, (g, ps) in info.items() if g == "apps" and n not in chosen for p in ps if has(p)]
    if drop:
        status = "Removing unselected applications"
        ch("apt-get", "-y", "purge", "--autoremove", *drop)
    todo = sorted((n for n in chosen if n in info and info[n][0] != "apps"), key=lambda n: (["system", "drivers", "terminal", "gaming", "development", "more"].index(info[n][0]), n))
    failed = []
    for i, n in enumerate(todo):
        status = f"Installing {n} ({i + 1}/{len(todo)})"
        libcalamares.job.setprogress(0.1 + 0.88 * i / len(todo))
        try:
            if ch("mesale-feature", "add", n, timeout=3600) != 0: failed.append(n)
        except subprocess.TimeoutExpired:
            failed.append(n)
    if "firefox" in chosen:
        lang = ((gs.value("localeConf") or {}).get("LANG") or "").split("_")[0]
        if lang and lang != "en": ch("apt-get", "-y", "install", f"firefox-esr-l10n-{lang}")
    if failed:
        warning(f"Deferred to first boot: {failed}")
        ch("dpkg", "--configure", "-a")
        with open(root + "/var/lib/mesale/pending", "a") as f: f.write("\n".join(failed) + "\n")
        ch("systemctl", "enable", "mesale-pending.service")
    user = gs.value("username")
    if "fish" in todo and "fish" not in failed and user: ch("usermod", "-s", "/usr/bin/fish", user)
    ch("apt-get", "clean")
    return None
