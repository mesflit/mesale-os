"""Version information and updates."""
import platform
import subprocess

from gi.repository import Adw, GLib, Gtk

TERMINAL_UPDATE = ["ptyxis", "--new-window", "--", "bash", "-c", "sudo apt update && sudo apt full-upgrade; read -r"]


def versions():
    shell = subprocess.run(["gnome-shell", "--version"], capture_output=True, text=True).stdout.strip()
    with open("/etc/debian_version") as file:
        debian = file.read().strip()
    return {"Mesale OS": platform.freedesktop_os_release().get("VERSION", ""), "Debian": debian,
            "Kernel": platform.release(), "Desktop": shell}


def open_updates(_row):
    has_store = GLib.find_program_in_path("gnome-software")
    subprocess.Popen(["gnome-software", "--mode=updates"] if has_store else TERMINAL_UPDATE)


class SystemPage(Adw.PreferencesPage):
    def __init__(self):
        super().__init__()
        info = Adw.PreferencesGroup()
        for title, value in versions().items():
            info.add(Adw.ActionRow(title=title, subtitle=value, css_classes=["property"]))
        updates = Adw.ActionRow(title="Updates", activatable=True)
        updates.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
        updates.connect("activated", open_updates)
        actions = Adw.PreferencesGroup()
        actions.add(updates)
        self.add(info)
        self.add(actions)
