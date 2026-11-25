"""Wallpaper, theme, accent and bottom bar."""
import json
import re

from gi.repository import Adw, Gdk, GdkPixbuf, Gio, Gtk

import panel

SHARE = "/usr/share/mesale"
MODES = ["light", "dark", "auto"]
MONITORS = range(4)
ACCENTS = {"blue": "#3f7de0", "teal": "#1f9aa0", "green": "#2f9e63", "yellow": "#d39b16", "orange": "#e9792f",
           "red": "#dc3f4e", "pink": "#dd5a96", "purple": "#8b6cf0", "slate": "#6b7585"}


def slider(title, value, low, high, on_change):
    scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, low, high, 1)
    scale.set_value(value)
    scale.set_size_request(240, -1)
    scale.set_draw_value(True)
    scale.set_value_pos(Gtk.PositionType.LEFT)
    scale.connect("value-changed", lambda s: on_change(int(s.get_value())))
    row = Adw.ActionRow(title=title)
    row.add_suffix(scale)
    return row


class LookPage(Adw.PreferencesPage):
    def __init__(self):
        super().__init__()
        self.interface = Gio.Settings.new("org.gnome.desktop.interface")
        self.background = Gio.Settings.new("org.gnome.desktop.background")
        self.lock_screen = Gio.Settings.new("org.gnome.desktop.screensaver")
        self.shell = Gio.Settings.new("org.mesale.shell")
        for group in (self.wallpaper_group(), self.color_group(), self.bar_group()):
            self.add(group)

    def wallpaper_group(self):
        grid = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, column_spacing=12, row_spacing=12,
                           max_children_per_line=4, min_children_per_line=2, homogeneous=True, margin_top=6)
        current, first = self.background.get_string("picture-uri"), None
        with open(f"{SHARE}/looks.json") as file:
            looks = json.load(file)
        for key, look in looks.items():
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(f"{SHARE}/previews/{key}.png", 150, 84, True)
            picture = Gtk.Picture.new_for_paintable(Gdk.Texture.new_for_pixbuf(pixbuf))
            picture.set_content_fit(Gtk.ContentFit.COVER)
            picture.set_size_request(150, 86)
            uri = f"file:///usr/share/backgrounds/mesale/{key}.jpg"
            button = Gtk.ToggleButton(css_classes=["wallpaper", "flat"], group=first, child=picture,
                                      active=uri == current, tooltip_text=look["name"], overflow=Gtk.Overflow.HIDDEN)
            first = first or button
            button.connect("toggled", self.set_wallpaper, uri)
            grid.append(button)
        group = Adw.PreferencesGroup(title="Wallpaper")
        group.add(grid)
        return group

    def set_wallpaper(self, button, uri):
        if button.get_active():
            for key in ("picture-uri", "picture-uri-dark"):
                self.background.set_string(key, uri)
            self.lock_screen.set_string("picture-uri", uri)

    def color_group(self):
        group = Adw.PreferencesGroup(title="Colors")
        theme = Adw.ComboRow(title="Theme", subtitle="Auto is light from 07 to 19",
                             model=Gtk.StringList.new(["Light", "Dark", "Auto"]))
        theme.set_selected(MODES.index(self.shell.get_string("theme-mode")))
        theme.connect("notify::selected", lambda r, _: self.shell.set_string("theme-mode", MODES[r.get_selected()]))
        group.add(theme)

        box, first = Gtk.Box(spacing=10, valign=Gtk.Align.CENTER, margin_top=10, margin_bottom=10), None
        current = self.interface.get_string("accent-color")
        for name in ACCENTS:
            button = Gtk.ToggleButton(css_classes=["accent", f"accent-{name}"], group=first, tooltip_text=name,
                                      active=name == current)
            first = first or button
            button.connect("toggled", self.set_accent, name)
            box.append(button)
        accent = Adw.ActionRow(title="Accent")
        accent.add_suffix(box)
        group.add(accent)
        return group

    def set_accent(self, button, name):
        if button.get_active():
            self.interface.set_string("accent-color", name)
            for dot in range(1, 5):
                panel.write(f"dot-color-{dot}", f"'{ACCENTS[name]}'")

    def bar_group(self):
        size = re.search(r'"0":\s*(\d+)', panel.read("panel-sizes", ""))
        opacity = round(float(panel.read("trans-panel-opacity", "0.42")) * 100)
        hide = Adw.SwitchRow(title="Hide behind windows", active=panel.read("intellihide", "false") == "true")
        hide.connect("notify::active", self.set_hiding)
        group = Adw.PreferencesGroup(title="Bottom bar")
        group.add(slider("Height", int(size[1]) if size else 52, 36, 72, self.set_height))
        group.add(slider("Opacity (%)", opacity, 10, 100, lambda v: panel.write("trans-panel-opacity", str(v / 100))))
        group.add(slider("Margin", int(panel.read("panel-side-margins", "10")), 0, 60,
                         lambda v: panel.write("panel-side-margins", str(v))))
        group.add(hide)
        return group

    def set_height(self, value):
        panel.write("panel-sizes", "'" + json.dumps({str(m): value for m in MONITORS}) + "'")

    def set_hiding(self, row, _param):
        panel.write("intellihide-hide-from-windows", "true")
        panel.write("intellihide", str(row.get_active()).lower())
