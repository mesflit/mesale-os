"""Install and remove features through mesale-feature."""
import pathlib
import re
import subprocess

from gi.repository import Adw, Gio, GLib, Gtk

FOLDER = pathlib.Path("/usr/lib/mesale/features")


def field(text, key):
    match = re.search(rf'^{key}="?([^"\n]*)', text, re.M)
    return match[1] if match else ""


def installed_features():
    done = subprocess.run(["mesale-feature", "list"], capture_output=True, text=True)
    return {line.split()[1] for line in done.stdout.splitlines() if line.startswith(" *")}


class FeatureButton(Gtk.Button):
    def __init__(self, feature, installed, toasts):
        super().__init__(valign=Gtk.Align.CENTER)
        self.feature, self.toasts = feature, toasts
        self.show_state(installed)
        self.connect("clicked", self.toggle)

    def show_state(self, installed):
        self.installed = installed
        self.set_label("Remove" if installed else "Install")
        self.set_css_classes([] if installed else ["suggested-action"])
        self.set_sensitive(True)

    def toggle(self, _button):
        self.set_sensitive(False)
        self.set_child(Adw.Spinner())
        action = "remove" if self.installed else "add"
        quiet = Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_SILENCE
        process = Gio.Subprocess.new(["pkexec", "/usr/bin/mesale-feature", action, self.feature], quiet)
        process.wait_check_async(None, self.finished)

    def finished(self, process, result):
        try:
            done = process.wait_check_finish(result)
        except GLib.Error:
            done = False
        self.show_state(self.installed ^ done)
        self.toasts.add_toast(Adw.Toast(title=f"{self.feature}: {'done' if done else 'failed'}"))


class FeaturesPage(Adw.PreferencesPage):
    def __init__(self, toasts):
        super().__init__()
        installed, groups = installed_features(), {}
        for path in sorted(FOLDER.iterdir()):
            text = path.read_text()
            row = Adw.ActionRow(title=GLib.markup_escape_text(field(text, "NAME")),
                                subtitle=GLib.markup_escape_text(field(text, "DESC")))
            row.add_suffix(FeatureButton(path.name, path.name in installed, toasts))
            key = field(text, "GROUP")
            if key not in groups:
                groups[key] = Adw.PreferencesGroup(title=key.capitalize())
            groups[key].add(row)
        for group in groups.values():
            self.add(group)
