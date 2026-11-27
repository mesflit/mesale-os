"""Mesale Center: look, features and system in one window.

usage: mesale-center [--nitro]     --nitro opens the Nitro page (the NitroSense key does this)
"""
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, Gtk  # noqa: E402

import nitro  # noqa: E402
from desktop import DesktopPage  # noqa: E402
from features import FeaturesPage  # noqa: E402
from look import ACCENTS, LookPage  # noqa: E402
from system import SystemPage  # noqa: E402

CSS = """
.accent { border-radius: 999px; min-width: 34px; min-height: 34px; padding: 0; }
.accent:checked { outline: 3px solid alpha(currentColor, .7); outline-offset: 3px; }
.wallpaper { padding: 0; border-radius: 14px; }
.wallpaper:checked { outline: 3px solid var(--accent-bg-color); outline-offset: 3px; }
""" + "".join(f".accent-{name} {{ background: {color}; }}" for name, color in ACCENTS.items())


class Window(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Mesale Center", default_width=780, default_height=680)
        self.stack = Adw.ViewStack()
        toasts = Adw.ToastOverlay(child=self.stack)
        pages = [
            (LookPage(), "Look", "applications-graphics-symbolic"),
            (DesktopPage(), "Desktop", "preferences-desktop-symbolic"),
            (FeaturesPage(toasts), "Features", "application-x-addon-symbolic"),
            (SystemPage(), "System", "computer-symbolic"),
        ]
        if nitro.available():
            pages.insert(2, (nitro.NitroPage(toasts), "Nitro", "power-profile-performance-symbolic"))
        for page, title, icon in pages:
            self.stack.add_titled_with_icon(page, title.lower(), title, icon)
        switcher = Adw.ViewSwitcher(stack=self.stack, policy=Adw.ViewSwitcherPolicy.WIDE)
        view = Adw.ToolbarView(content=toasts)
        view.add_top_bar(Adw.HeaderBar(title_widget=switcher))
        self.set_content(view)


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.mesale.Center", flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)

    def do_command_line(self, command_line):
        self.activate()
        window = self.get_active_window()
        if "--nitro" in command_line.get_arguments()[1:] and window.stack.get_child_by_name("nitro"):
            window.stack.set_visible_child_name("nitro")
        return 0

    def do_activate(self):
        if not self.get_active_window():
            provider = Gtk.CssProvider()
            provider.load_from_string(CSS)
            Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, 600)
            Window(self)
        self.get_active_window().present()


sys.exit(Application().run(sys.argv))
