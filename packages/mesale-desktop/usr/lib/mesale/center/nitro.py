"""Acer Nitro / Predator: thermal profile, fans, battery and keyboard light (Linuwu-Sense)."""
import glob
import os

from gi.repository import Adw, Gio, GLib, Gtk

DEVICE = "/sys/devices/platform/acer-wmi/nitro_sense"
PROFILE = "/sys/firmware/acpi/platform_profile"
PROFILES = {"low-power": "Eco", "quiet": "Quiet", "balanced": "Balanced",
            "balanced-performance": "Performance", "performance": "Turbo"}
USB = {"0": "Off", "10": "Until 10%", "20": "Until 20%", "30": "Until 30%"}


def available():
    return os.path.isdir(DEVICE)


def read(path, default=""):
    try:
        with open(path) as file:
            return file.read().strip()
    except OSError:
        return default


def setting(name):
    return read(f"{DEVICE}/{name}")


def fans():
    """CPU and GPU fan speed in RPM."""
    folder = next(iter(glob.glob("/sys/devices/platform/acer-wmi/hwmon/hwmon*")), "")
    return [read(f"{folder}/fan{n}_input", "0") for n in (1, 2)]


class NitroPage(Adw.PreferencesPage):
    def __init__(self, toasts):
        super().__init__()
        self.toasts, self.pending, self.busy = toasts, None, False
        for group in (self.profile_group(), self.fan_group(), self.battery_group(), self.keyboard_group()):
            self.add(group)
        GLib.timeout_add_seconds(2, self.refresh)

    # Writing goes through polkit: no password for the person at the computer.
    def run(self, *args):
        process = Gio.Subprocess.new(["pkexec", "/usr/bin/mesale-nitro", *args],
                                     Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_PIPE)
        process.wait_check_async(None, self.finished)

    def finished(self, process, result):
        try:
            process.wait_check_finish(result)
        except GLib.Error:
            self.toasts.add_toast(Adw.Toast(title="The laptop did not accept that setting"))

    def profile_group(self):
        group = Adw.PreferencesGroup(title="Thermal profile",
                                     description="The NitroSense key opens this page")
        box = Gtk.Box(css_classes=["linked"], halign=Gtk.Align.CENTER, margin_top=6, margin_bottom=6)
        current, first = read(PROFILE), None
        self.profile_buttons = {}
        for key in read(f"{PROFILE}_choices").split():
            button = Gtk.ToggleButton(label=PROFILES.get(key, key), active=key == current, group=first)
            first = first or button
            button.connect("toggled", self.profile_toggled, key)
            self.profile_buttons[key] = button
            box.append(button)
        group.add(box)
        return group

    def profile_toggled(self, button, key):
        if button.get_active() and not self.busy and read(PROFILE) != key:
            self.run("profile", key)

    def fan_group(self):
        group = Adw.PreferencesGroup(title="Fans")
        self.rpm = Adw.ActionRow(title="Speed", css_classes=["property"])
        group.add(self.rpm)
        cpu, gpu = (int(n) for n in (setting("fan_speed") or "0,0").split(","))
        self.auto = Adw.SwitchRow(title="Automatic", subtitle="Let the firmware follow the temperature",
                                  active=cpu == 0 and gpu == 0)
        self.auto.connect("notify::active", self.fan_changed)
        group.add(self.auto)
        self.sliders = []
        for title, value in (("CPU fan", cpu), ("GPU fan", gpu)):
            scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 10, 100, 5)
            scale.set_value(value or 60)
            scale.set_size_request(240, -1)
            scale.set_draw_value(True)
            scale.set_format_value_func(lambda _s, v: f"{int(v)}%")
            scale.connect("value-changed", self.fan_changed)
            row = Adw.ActionRow(title=title)
            row.add_suffix(scale)
            self.sliders.append((row, scale))
            group.add(row)
        self.show_sliders()
        self.refresh()
        return group

    def show_sliders(self):
        for row, _scale in self.sliders:
            row.set_visible(not self.auto.get_active())

    def fan_changed(self, *_args):
        self.show_sliders()
        if self.pending:
            GLib.source_remove(self.pending)
        self.pending = GLib.timeout_add(400, self.apply_fans)  # wait until the slider rests

    def apply_fans(self):
        self.pending = None
        if self.auto.get_active():
            self.run("fan", "auto")
        else:
            self.run("fan", ",".join(str(int(scale.get_value())) for _row, scale in self.sliders))
        return GLib.SOURCE_REMOVE

    def battery_group(self):
        group = Adw.PreferencesGroup(title="Battery")
        limit = Adw.SwitchRow(title="Stop charging at 80%", subtitle="Keeps the battery healthy when plugged in",
                              active=setting("battery_limiter") == "1")
        limit.connect("notify::active", lambda row, _p: self.run("charge", "on" if row.get_active() else "off"))
        group.add(limit)
        usb = Adw.ComboRow(title="USB charging when off", model=Gtk.StringList.new(list(USB.values())))
        keys = list(USB)
        usb.set_selected(keys.index(setting("usb_charging")) if setting("usb_charging") in keys else 0)
        usb.connect("notify::selected", lambda row, _p: self.run("usb", keys[row.get_selected()]))
        group.add(usb)
        return group

    def keyboard_group(self):
        group = Adw.PreferencesGroup(title="Keyboard")
        light = Adw.SwitchRow(title="Turn the light off when idle", subtitle="After 30 seconds without typing",
                              active=setting("backlight_timeout") == "1")
        light.connect("notify::active", lambda row, _p: self.run("light", "on" if row.get_active() else "off"))
        group.add(light)
        return group

    def refresh(self):
        cpu, gpu = fans()
        self.rpm.set_subtitle(f"CPU {cpu} RPM  ·  GPU {gpu} RPM")
        # The profile can also change elsewhere (power settings, the firmware on battery)
        button = getattr(self, "profile_buttons", {}).get(read(PROFILE))
        if button and not button.get_active():
            self.busy = True
            button.set_active(True)
            self.busy = False
        return GLib.SOURCE_CONTINUE
