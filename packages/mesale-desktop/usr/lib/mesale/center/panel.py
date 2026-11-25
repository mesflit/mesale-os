"""Read and write the bottom bar's settings (Dash to Panel, through dconf)."""
import subprocess

PATH = "/org/gnome/shell/extensions/dash-to-panel/"


def read(key, default):
    done = subprocess.run(["dconf", "read", PATH + key], capture_output=True, text=True)
    return done.stdout.strip() or default


def write(key, value):
    subprocess.run(["dconf", "write", PATH + key, value], check=False)
