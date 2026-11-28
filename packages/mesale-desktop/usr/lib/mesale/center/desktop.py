"""Desktop: the bottom bar, clock, command bar and windows."""
import json
import re

from gi.repository import Adw, Gtk

import panel
from widgets import choice, group, has_key, link, settings, slider, spawn, string_choice, switch

MONITORS = range(4)
TILING = "tiling-assistant@leleat-on-github"
ICON_SIZES = [(9, "Small"), (6, "Medium"), (3, "Large")]   # Dash to Panel's padding around each icon
INDICATORS = [("DASHES", "Line"), ("DOTS", "Dots"), ("SQUARES", "Squares"), ("SOLID", "Bar"), ("METRO", "Underline")]
SHORTCUTS = [("<Super>space", "Super+Space"), ("<Super>r", "Super+R"), ("<Control><Alt>space", "Ctrl+Alt+Space")]
ENGINES = [("duckduckgo", "DuckDuckGo"), ("google", "Google"), ("startpage", "Startpage"),
           ("brave", "Brave Search"), ("ecosia", "Ecosia")]
BUTTONS = [(":minimize,maximize,close", "Right, all three"), (":close", "Right, close only"),
           ("close,minimize,maximize:", "Left, all three"), ("close:", "Left, close only")]
# Shortcuts Mesale sets up, shown so they can be found
SHORTCUTS_LIST = [
    ("Super+Q", "Close the window"),
    ("Super+F", "Fullscreen"),
    ("Super+1 … 9", "Go to a workspace"),
    ("Super+Shift+1 … 9", "Move the window to a workspace"),
    ("Super+Return", "Terminal"),
]
WORKSPACES = [(0, "As many as needed"), (1, "One"), (2, "Two"), (3, "Three"), (4, "Four"), (6, "Six")]


def unquote(value):
    """Dash to Panel keeps JSON in dconf strings: "'{...}'" -> "{...}"."""
    return value[1:-1] if len(value) > 1 and value[0] == value[-1] == "'" else value


def nearest(options, value):
    return min((v for v, _label in options), key=lambda v: abs(v - value))


class DesktopPage(Adw.PreferencesPage):
    def __init__(self):
        super().__init__()
        self.interface = settings("org.gnome.desktop.interface")
        self.shell = settings("org.mesale.shell")
        self.gnome_shell = settings("org.gnome.shell")
        self.mutter = settings("org.gnome.mutter")
        self.wm = settings("org.gnome.desktop.wm.preferences")
        for build in (self.bar_group, self.clock_group, self.command_group, self.windows_group, self.shortcuts_group):
            box = build()
            if box:
                self.add(box)

    # Bottom bar (Dash to Panel, through dconf) ------------------------------------

    def bar_group(self):
        size = re.search(r'"0":\s*(\d+)', panel.read("panel-sizes", ""))
        opacity = round(float(panel.read("trans-panel-opacity", "0.42")) * 100)
        padding = int(panel.read("appicon-padding", "6"))
        hide = Adw.SwitchRow(title="Hide behind windows", active=panel.read("intellihide", "false") == "true")
        hide.connect("notify::active", self.set_hiding)
        titles = Adw.SwitchRow(title="Window titles", subtitle="Show each window with its name",
                               active=panel.read("group-apps", "true") == "false")
        titles.connect("notify::active", lambda r, _p: panel.write("group-apps", str(not r.get_active()).lower()))
        return group("Bottom bar", [
            slider("Height", int(size[1]) if size else 52, 36, 72, self.set_height),
            choice("Icon size", ICON_SIZES, nearest(ICON_SIZES, padding),
                   lambda value: panel.write("appicon-padding", str(value))),
            choice("Apps", [("centerMonitor", "In the middle"), ("stackedTL", "On the left")],
                   self.taskbar_position(), self.set_taskbar_position),
            choice("Open app marker", INDICATORS, unquote(panel.read("dot-style-focused", "'DASHES'")),
                   self.set_indicator),
            titles,
            slider("Opacity (%)", opacity, 10, 100, lambda v: panel.write("trans-panel-opacity", str(v / 100))),
            slider("Margin", int(panel.read("panel-side-margins", "10")), 0, 60,
                   lambda v: panel.write("panel-side-margins", str(v))),
            hide,
        ])

    def set_height(self, value):
        panel.write("panel-sizes", "'" + json.dumps({str(m): value for m in MONITORS}) + "'")

    def set_hiding(self, row, _param):
        panel.write("intellihide-hide-from-windows", "true")
        panel.write("intellihide", str(row.get_active()).lower())

    def positions(self):
        try:
            return json.loads(unquote(panel.read("panel-element-positions", "")))
        except ValueError:
            return {}

    def taskbar_position(self):
        for element in self.positions().get("0", []):
            if element.get("element") == "taskbar":
                return element.get("position", "centerMonitor")
        return "centerMonitor"

    def set_taskbar_position(self, position):
        layout = self.positions()
        for elements in layout.values():
            for element in elements:
                if element.get("element") == "taskbar":
                    element["position"] = position
        if layout:
            panel.write("panel-element-positions", "'" + json.dumps(layout, separators=(",", ":")) + "'")

    def set_indicator(self, style):
        # The focused app gets the chosen marker; the others the same, or dots next to a line
        panel.write("dot-style-focused", f"'{style}'")
        panel.write("dot-style-unfocused", f"'{'DOTS' if style == 'DASHES' else style}'")

    # Clock and battery ------------------------------------------------------------

    def clock_group(self):
        i = self.interface
        rows = [
            string_choice("Clock", [("24h", "24-hour"), ("12h", "12-hour")], i, "clock-format"),
            switch("Seconds", i, "clock-show-seconds"),
            switch("Weekday", i, "clock-show-weekday"),
            switch("Date", i, "clock-show-date"),
            switch("Battery percentage", i, "show-battery-percentage"),
        ]
        return group("Clock and battery", rows)

    # Command bar ------------------------------------------------------------------

    def command_group(self):
        s = self.shell
        rows = []
        if has_key(s, "command-bar"):
            current = (s.get_strv("command-bar") or ["<Super>space"])[0]
            rows.append(choice("Shortcut", SHORTCUTS, current, lambda value: s.set_strv("command-bar", [value])))
        rows += [
            string_choice("Web search", ENGINES, s, "search-engine", subtitle="For ? and when nothing else matches"),
            switch("Files", s, "search-files", subtitle="Recent files and your folders"),
            switch("Web search suggestion", s, "search-web", subtitle="Offered when nothing else matches"),
            switch("Clipboard history", s, "clipboard-history",
                   subtitle="Copied text, in memory only, until you log out. Turning it off forgets it."),
        ]
        return group("Command bar", rows)

    # Windows ----------------------------------------------------------------------

    def windows_group(self):
        rows = [string_choice("Title bar buttons", BUTTONS, self.wm, "button-layout")]
        if self.gnome_shell and has_key(self.mutter, "edge-tiling"):
            rows.append(choice("Tiling", [("mesale", "Layouts and gaps"), ("gnome", "Drag to the edges"), ("off", "Off")],
                               self.tiling(), self.set_tiling))
        if has_key(self.mutter, "dynamic-workspaces") and has_key(self.wm, "num-workspaces"):
            count = 0 if self.mutter.get_boolean("dynamic-workspaces") else self.wm.get_int("num-workspaces")
            rows.append(choice("Workspaces", WORKSPACES, count, self.set_workspaces))
        rows += [
            switch("Hot corner", self.interface, "enable-hot-corners", subtitle="Top left corner opens the overview"),
            switch("Animations", self.interface, "enable-animations"),
            switch("New windows in the middle", self.mutter, "center-new-windows"),
        ]
        return group("Windows", rows)

    def tiling(self):
        if TILING in self.gnome_shell.get_strv("enabled-extensions"):
            return "mesale"
        return "gnome" if self.mutter.get_boolean("edge-tiling") else "off"

    def set_tiling(self, mode):
        enabled = [e for e in self.gnome_shell.get_strv("enabled-extensions") if e != TILING]
        disabled = [e for e in self.gnome_shell.get_strv("disabled-extensions") if e != TILING]
        if mode == "mesale":
            enabled.append(TILING)
        else:
            disabled.append(TILING)
        self.gnome_shell.set_strv("enabled-extensions", enabled)
        self.gnome_shell.set_strv("disabled-extensions", disabled)
        # GNOME's own edge snapping would fight the tiling extension
        self.mutter.set_boolean("edge-tiling", mode == "gnome")

    def set_workspaces(self, count):
        self.mutter.set_boolean("dynamic-workspaces", count == 0)
        if count:
            self.wm.set_int("num-workspaces", count)

    # Shortcuts --------------------------------------------------------------------

    def shortcuts_group(self):
        rows = []
        for keys, what in SHORTCUTS_LIST:
            row = Adw.ActionRow(title=what)
            row.add_suffix(Gtk.Label(label=keys, css_classes=["dim-label", "monospace"]))
            rows.append(row)
        rows.append(link("All shortcuts", "In Settings, Keyboard", lambda: spawn(["gnome-control-center", "keyboard"])))
        return group("Shortcuts", rows, description="The command bar shortcut is set above")
