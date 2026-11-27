"""Look: wallpaper, colours and theme switching, blur, text, pointer and icons."""
import json
import os
import re
import shutil

from gi.repository import Adw, Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango

import panel
from widgets import choice, group, has_key, link, settings, slider, spawn

SHARE = "/usr/share/mesale"
WALLPAPERS = "/usr/share/backgrounds/mesale"
MODES = ["light", "dark", "auto"]
ACCENTS = {"blue": "#3f7de0", "teal": "#1f9aa0", "green": "#2f9e63", "yellow": "#d39b16", "orange": "#e9792f",
           "red": "#dc3f4e", "pink": "#dd5a96", "purple": "#8b6cf0", "slate": "#6b7585"}
BLUR = "org.gnome.shell.extensions.blur-my-shell"
BLUR_PARTS = ["panel", "popup", "overview", "lockscreen", "applications"]
ICON_FOLDERS = ["/usr/share/icons", os.path.expanduser("~/.local/share/icons"), os.path.expanduser("~/.icons")]
NOT_ICON_THEMES = {"hicolor", "locolor", "default"}


# Blur My Shell keeps the blur strength inside its 'pipelines' value. Only the radius is
# changed; the rest of the value, and settings-version, stay exactly as they are.
PIPELINES = GLib.VariantType.new("a{sa{sv}}")
RADIUS = re.compile(r"('unscaled_radius': <)(?:int32 )?(\d+)(>)")


def blur_radius(pipelines):
    match = RADIUS.search(pipelines.print_(True))
    return int(match.group(2)) if match else None


def with_blur_radius(pipelines, radius):
    text = RADIUS.sub(lambda m: f"{m.group(1)}int32 {radius}{m.group(3)}", pipelines.print_(True))
    return GLib.Variant.parse(PIPELINES, text, None, None)


def themes(kind):
    """Installed cursor themes ('cursors') or icon themes ('icons'), sorted by name."""
    found = set()
    for folder in ICON_FOLDERS:
        if not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            has_cursors = os.path.isdir(os.path.join(path, "cursors"))
            if kind == "cursors" and has_cursors:
                found.add(name)
            elif kind == "icons" and name not in NOT_ICON_THEMES and os.path.exists(os.path.join(path, "index.theme")):
                # A theme with nothing but cursors is not an icon theme
                entries = set(os.listdir(path)) - {"index.theme", "cursors", "cursor.theme"}
                if entries:
                    found.add(name)
    return sorted(found, key=str.casefold)


class LookPage(Adw.PreferencesPage):
    def __init__(self):
        super().__init__()
        self.interface = settings("org.gnome.desktop.interface")
        self.background = settings("org.gnome.desktop.background")
        self.lock_screen = settings("org.gnome.desktop.screensaver")
        self.shell = settings("org.mesale.shell")
        for build in (self.wallpaper_group, self.color_group, self.blur_group, self.text_group, self.pointer_group):
            box = build()
            if box:
                self.add(box)

    # Wallpaper --------------------------------------------------------------------

    def wallpaper_group(self):
        if not self.background:
            return None
        box = Adw.PreferencesGroup(title="Wallpaper")
        self.light_grid = self.wallpaper_grid("picture-uri", self.set_wallpaper)
        box.add(self.light_grid)

        choose = Gtk.Button(label="Choose a picture…", halign=Gtk.Align.START, margin_top=12, css_classes=["pill"])
        choose.connect("clicked", self.choose_picture)
        box.add(choose)

        same = self.background.get_string("picture-uri") == self.background.get_string("picture-uri-dark")
        self.same = Adw.SwitchRow(title="Same wallpaper in dark style", active=same,
                                  subtitle="Turn off to pick another one for dark style")
        self.same.connect("notify::active", self.on_same_changed)
        dark_box = Adw.PreferencesGroup(margin_top=12)
        dark_box.add(self.same)
        self.dark_grid = self.wallpaper_grid("picture-uri-dark", self.set_dark_wallpaper)
        self.dark_grid.set_visible(not same)
        dark_box.add(self.dark_grid)
        box.add(dark_box)
        return box

    def wallpaper_grid(self, key, on_toggled):
        """Mesale's looks, plus the user's own picture when one is set."""
        grid = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, column_spacing=12, row_spacing=12,
                           max_children_per_line=4, min_children_per_line=2, homogeneous=True, margin_top=6)
        current, first = self.background.get_string(key), None
        try:
            with open(f"{SHARE}/looks.json") as file:
                looks = json.load(file)
        except OSError:
            looks = {}
        tiles = [(f"{SHARE}/previews/{name}.png", f"file://{WALLPAPERS}/{name}.jpg", look["name"])
                 for name, look in looks.items()]
        if current and not current.startswith(f"file://{WALLPAPERS}/"):
            path = Gio.File.new_for_uri(current).get_path()
            if path and os.path.exists(path):
                tiles.append((path, current, "Your picture"))
        for preview, uri, name in tiles:
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(preview, 150, 84, True)
                picture = Gtk.Picture.new_for_paintable(Gdk.Texture.new_for_pixbuf(pixbuf))
            except GLib.Error:
                picture = Gtk.Picture()
            picture.set_content_fit(Gtk.ContentFit.COVER)
            picture.set_size_request(150, 86)
            button = Gtk.ToggleButton(css_classes=["wallpaper", "flat"], group=first, child=picture,
                                      active=uri == current, tooltip_text=name, overflow=Gtk.Overflow.HIDDEN)
            first = first or button
            button.connect("toggled", on_toggled, uri)
            grid.append(button)
        return grid

    def set_wallpaper(self, button, uri):
        if button.get_active():
            self.background.set_string("picture-uri", uri)
            if self.same.get_active():
                self.background.set_string("picture-uri-dark", uri)
            if self.lock_screen:
                self.lock_screen.set_string("picture-uri", uri)

    def set_dark_wallpaper(self, button, uri):
        if button.get_active():
            self.background.set_string("picture-uri-dark", uri)

    def on_same_changed(self, row, _param):
        self.dark_grid.set_visible(not row.get_active())
        if row.get_active():
            self.background.set_string("picture-uri-dark", self.background.get_string("picture-uri"))

    def choose_picture(self, _button):
        dialog = Gtk.FileDialog(title="Choose a wallpaper")
        images = Gtk.FileFilter(name="Pictures")
        images.add_pixbuf_formats()
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(images)
        dialog.set_filters(filters)
        dialog.open(self.get_root(), None, self.on_picture_chosen)

    def on_picture_chosen(self, dialog, result):
        try:
            source = dialog.open_finish(result)
        except GLib.Error:
            return   # cancelled
        # A copy, so the wallpaper stays when the original is moved or deleted
        folder = os.path.join(GLib.get_user_data_dir(), "backgrounds")
        os.makedirs(folder, exist_ok=True)
        target = os.path.join(folder, source.get_basename())
        if os.path.abspath(source.get_path()) != os.path.abspath(target):
            shutil.copyfile(source.get_path(), target)
        uri = Gio.File.new_for_path(target).get_uri()
        self.background.set_string("picture-uri", uri)
        if self.same.get_active():
            self.background.set_string("picture-uri-dark", uri)
        if self.lock_screen:
            self.lock_screen.set_string("picture-uri", uri)
        self.rebuild_grid()

    def rebuild_grid(self):
        parent = self.light_grid.get_parent()
        replacement = self.wallpaper_grid("picture-uri", self.set_wallpaper)
        parent.insert_child_after(replacement, self.light_grid)
        parent.remove(self.light_grid)
        self.light_grid = replacement

    # Colours and theme switching -------------------------------------------------

    def color_group(self):
        rows = []
        if self.shell:
            theme = Adw.ComboRow(title="Style", model=Gtk.StringList.new(["Light", "Dark", "Auto"]))
            theme.set_selected(MODES.index(self.shell.get_string("theme-mode")))
            self.shell.connect("changed::theme-mode", lambda *_: theme.set_selected(
                MODES.index(self.shell.get_string("theme-mode"))))
            theme.connect("notify::selected", self.on_mode)
            rows.append(theme)

            self.switching = choice(
                "Auto switches", [("hours", "At set hours"), ("sun", "At sunrise and sunset")],
                self.shell.get_string("auto-switch"), self.on_switching,
                subtitle="Sunrise and sunset of your time zone, no location needed")
            self.light_hour = self.hour_row("Light from", "light-hour")
            self.dark_hour = self.hour_row("Dark from", "dark-hour")
            rows += [self.switching, self.light_hour, self.dark_hour]

        if self.interface:
            colors, first = Gtk.Box(spacing=10, valign=Gtk.Align.CENTER, margin_top=10, margin_bottom=10), None
            current = self.interface.get_string("accent-color") if has_key(self.interface, "accent-color") else ""
            for name in ACCENTS:
                button = Gtk.ToggleButton(css_classes=["accent", f"accent-{name}"], group=first, tooltip_text=name,
                                          active=name == current)
                first = first or button
                button.connect("toggled", self.set_accent, name)
                colors.append(button)
            accent = Adw.ActionRow(title="Accent")
            accent.add_suffix(colors)
            rows.append(accent)
        box = group("Colors", rows)
        self.update_switching()
        return box

    def hour_row(self, title, key):
        row = Adw.SpinRow.new_with_range(0, 23, 1)
        row.set_title(title)
        row.set_subtitle("Hour of the day, 0 to 23")
        row.set_value(self.shell.get_int(key))
        row.connect("notify::value", lambda r, _param: self.shell.set_int(key, int(r.get_value())))
        return row

    def on_mode(self, row, _param):
        self.shell.set_string("theme-mode", MODES[row.get_selected()])
        self.update_switching()

    def on_switching(self, value):
        self.shell.set_string("auto-switch", value)
        self.update_switching()

    def update_switching(self):
        if not self.shell:
            return
        auto = self.shell.get_string("theme-mode") == "auto"
        hours = self.shell.get_string("auto-switch") == "hours"
        self.switching.set_visible(auto)
        self.light_hour.set_visible(auto and hours)
        self.dark_hour.set_visible(auto and hours)

    def set_accent(self, button, name):
        if button.get_active():
            self.interface.set_string("accent-color", name)
            for dot in range(1, 5):
                panel.write(f"dot-color-{dot}", f"'{ACCENTS[name]}'")

    # Blur -------------------------------------------------------------------------

    def blur_group(self):
        main = settings(BLUR)
        if not has_key(main, "pipelines"):
            return None
        parts = [s for s in (settings(f"{BLUR}.{part}") for part in BLUR_PARTS) if has_key(s, "blur")]
        rows = []
        if parts:
            on = Adw.SwitchRow(title="Blur", subtitle="Bottom bar, menus, overview and lock screen",
                               active=any(p.get_boolean("blur") for p in parts))
            on.connect("notify::active", lambda r, _p: [p.set_boolean("blur", r.get_active()) for p in parts])
            rows.append(on)
        radius = blur_radius(main.get_value("pipelines"))
        if radius is not None:
            rows.append(slider("Strength", radius, 8, 80,
                               lambda value: main.set_value("pipelines", with_blur_radius(main.get_value("pipelines"), value))))
        return group("Blur", rows)

    # Text -------------------------------------------------------------------------

    def text_group(self):
        if not self.interface:
            return None
        rows = [self.font_row("Interface font", "font-name"), self.font_row("Monospace font", "monospace-font-name")]
        if has_key(self.interface, "text-scaling-factor"):
            size = Adw.SpinRow.new_with_range(0.75, 1.75, 0.05)
            size.set_title("Text size")
            size.set_subtitle("1.00 is normal")
            size.set_digits(2)
            self.interface.bind("text-scaling-factor", size, "value", Gio.SettingsBindFlags.DEFAULT)
            rows.append(size)
        rows.append(link("Screen scale", "In Settings, Displays",
                         lambda: spawn(["gnome-control-center", "display"])))
        return group("Text", rows)

    def font_row(self, title, key):
        if not has_key(self.interface, key):
            return None
        button = Gtk.FontDialogButton(dialog=Gtk.FontDialog(title=title), valign=Gtk.Align.CENTER)
        # Set after the dialog: given to the constructor, GTK reads the font list before it has one
        button.set_font_desc(Pango.FontDescription.from_string(self.interface.get_string(key)))
        button.connect("notify::font-desc", lambda b, _p: self.interface.set_string(key, b.get_font_desc().to_string()))
        row = Adw.ActionRow(title=title)
        row.add_suffix(button)
        return row

    # Pointer and icons ------------------------------------------------------------

    def pointer_group(self):
        if not self.interface:
            return None
        rows = []
        cursors = themes("cursors")
        if cursors and has_key(self.interface, "cursor-theme"):
            rows.append(choice("Pointer", [(name, name) for name in cursors], self.interface.get_string("cursor-theme"),
                               lambda value: self.interface.set_string("cursor-theme", value)))
        if has_key(self.interface, "cursor-size"):
            sizes = [(24, "Normal"), (32, "Large"), (48, "Larger"), (64, "Largest")]
            rows.append(choice("Pointer size", sizes, self.interface.get_int("cursor-size"),
                               lambda value: self.interface.set_int("cursor-size", value)))
        icons = themes("icons")
        if len(icons) > 1 and has_key(self.interface, "icon-theme"):
            rows.append(choice("Icons", [(name, name) for name in icons], self.interface.get_string("icon-theme"),
                               lambda value: self.interface.set_string("icon-theme", value),
                               subtitle="Icon themes you install show up here"))
        return group("Pointer and icons", rows)
