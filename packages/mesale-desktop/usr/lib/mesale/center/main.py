"""Mesale Center: look, features and system in one window."""
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk  # noqa: E402

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
        stack = Adw.ViewStack()
        toasts = Adw.ToastOverlay(child=stack)
        for page, title, icon in (
            (LookPage(), "Look", "applications-graphics-symbolic"),
            (FeaturesPage(toasts), "Features", "application-x-addon-symbolic"),
            (SystemPage(), "System", "computer-symbolic"),
        ):
            stack.add_titled_with_icon(page, title.lower(), title, icon)
        switcher = Adw.ViewSwitcher(stack=stack, policy=Adw.ViewSwitcherPolicy.WIDE)
        view = Adw.ToolbarView(content=toasts)
        view.add_top_bar(Adw.HeaderBar(title_widget=switcher))
        self.set_content(view)


class Application(Adw.Application):
    def do_activate(self):
        provider = Gtk.CssProvider()
        provider.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, 600)
        (self.get_active_window() or Window(self)).present()


sys.exit(Application(application_id="org.mesale.Center").run(sys.argv))
