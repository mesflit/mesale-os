"""Mesale Play: every installed game from Steam, Heroic and Lutris in one fullscreen
library, played with a gamepad or the keyboard."""
import os
import sys
import threading
import time

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covers  # noqa: E402
import library  # noqa: E402
from gamepad import Gamepads  # noqa: E402

FILTERS = ["All"] + library.SOURCES
SORTS = ["Recent", "A–Z"]
CARD_WIDTH, CARD_HEIGHT = 200, 300
REFRESH_AFTER_S = 5


def played(game):
    if not game.last_played:
        return "Not played yet"
    days = int((time.time() - game.last_played) // 86400)
    if days <= 0:
        return "Played today"
    if days == 1:
        return "Played yesterday"
    if days < 30:
        return f"Played {days} days ago"
    return "Played " + time.strftime("%-d %b %Y", time.localtime(game.last_played))


class Card(Gtk.FlowBoxChild):
    """A cover, or the title on a soft gradient when there is no cover."""

    def __init__(self, game):
        super().__init__(css_classes=["card"], focusable=True)
        self.game = game
        overlay = Gtk.Overlay(width_request=CARD_WIDTH, height_request=CARD_HEIGHT, overflow=Gtk.Overflow.HIDDEN,
                              css_classes=["cover", f"source-{game.source.lower()}"])
        overlay.set_child(Gtk.Label(label=game.title, wrap=True, justify=Gtk.Justification.CENTER,
                                    max_width_chars=14, css_classes=["cover-title"], margin_start=14, margin_end=14))
        self.picture = Gtk.Picture(content_fit=Gtk.ContentFit.COVER, can_shrink=True, visible=False)
        overlay.add_overlay(self.picture)
        badge = Gtk.Label(label=game.source, css_classes=["badge"], halign=Gtk.Align.START, valign=Gtk.Align.END,
                          margin_start=10, margin_bottom=10)
        overlay.add_overlay(badge)
        self.set_child(overlay)
        covers.get(game.cover, self.show_cover)

    def show_cover(self, path):
        self.picture.set_filename(path)
        self.picture.set_visible(True)


class Window(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Mesale Play", default_width=1600, default_height=900)
        self.games, self.filter, self.sort, self.loaded_at = [], 0, 0, 0
        self.toasts = Adw.ToastOverlay()
        self.set_content(self.toasts)

        root = Gtk.Overlay(css_classes=["play"])
        self.toasts.set_child(root)
        self.backdrop = Gtk.Picture(content_fit=Gtk.ContentFit.COVER, can_shrink=True, css_classes=["backdrop"])
        root.set_child(self.backdrop)
        root.add_overlay(Gtk.Box(css_classes=["shade"]))

        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, css_classes=["page"])
        root.add_overlay(page)
        page.append(self.header())

        self.title = Gtk.Label(xalign=0, css_classes=["game-title"], ellipsize=3)
        self.subtitle = Gtk.Label(xalign=0, css_classes=["game-subtitle"])
        page.append(self.title)
        page.append(self.subtitle)

        self.grid = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.SINGLE, homogeneous=True, valign=Gtk.Align.START,
                                max_children_per_line=12, min_children_per_line=3, column_spacing=0,
                                row_spacing=0, activate_on_single_click=True, css_classes=["grid"])
        self.grid.set_filter_func(self.visible_game)
        self.grid.set_sort_func(self.compare)
        self.grid.connect("child-activated", lambda _grid, card: self.launch(card.game))
        self.grid.connect("selected-children-changed", lambda *_: self.show_selected())
        self.scroller = Gtk.ScrolledWindow(child=self.grid, vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER,
                                           css_classes=["scroller"])
        self.grid.set_vadjustment(self.scroller.get_vadjustment())

        self.empty = Adw.StatusPage(icon_name="input-gaming-symbolic", title="No games yet", vexpand=True,
                                    description="Install Steam, Heroic or Lutris from Mesale Center, then "
                                                "install a game there. It shows up here by itself.")
        center = Gtk.Button(label="Open Mesale Center", halign=Gtk.Align.CENTER, css_classes=["pill", "suggested-action"])
        center.connect("clicked", lambda *_: self.spawn(["mesale-center"]))
        self.empty.set_child(center)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, vexpand=True)
        self.stack.add_named(self.scroller, "games")
        self.stack.add_named(self.empty, "empty")
        page.append(self.stack)

        self.hints = Gtk.Label(halign=Gtk.Align.CENTER, css_classes=["hints"])
        page.append(self.hints)

        # Before the grid, which would otherwise take the arrow keys for its own cursor
        keys = Gtk.EventControllerKey(propagation_phase=Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self.on_key)
        self.add_controller(keys)
        self.connect("notify::is-active", lambda *_: self.on_active())

        self.pads = Gamepads(self.on_action, lambda: self.is_active())
        self.pads.listeners.append(self.update_hints)
        GLib.timeout_add_seconds(20, self.tick)
        self.tick()
        self.reload()

    # Layout

    def header(self):
        bar = Gtk.Box(spacing=10, css_classes=["header"])
        bar.append(Gtk.Label(label="Mesale Play", css_classes=["brand"]))
        self.chips = []
        chips = Gtk.Box(spacing=8, margin_start=24)
        for name in FILTERS:
            chip = Gtk.Label(label=name, css_classes=["chip"])
            self.chips.append(chip)
            chips.append(chip)
        bar.append(chips)
        bar.append(Gtk.Box(hexpand=True))
        self.clock = Gtk.Label(css_classes=["clock"])
        bar.append(self.clock)
        return bar

    def tick(self):
        self.clock.set_label(GLib.DateTime.new_now_local().format("%H:%M"))
        return GLib.SOURCE_CONTINUE

    def update_hints(self):
        if self.pads.connected:
            text = "Ⓐ Play     Ⓑ Back     Ⓧ Sort: {sort}     Ⓨ Filter     LB RB Store     ☰ Menu"
        else:
            text = "Enter Play     Esc Back     S Sort: {sort}     F Filter     M Menu     F5 Refresh"
        self.hints.set_label(text.format(sort=SORTS[self.sort]))

    def update_chips(self):
        available = {g.source for g in self.games}
        for index, (name, chip) in enumerate(zip(FILTERS, self.chips)):
            chip.set_visible(name == "All" or name in available)
            if index == self.filter:
                chip.add_css_class("active")
            else:
                chip.remove_css_class("active")

    # Library

    def reload(self):
        def work():
            games = library.load()
            GLib.idle_add(self.fill, games)
        self.loaded_at = time.monotonic()
        threading.Thread(target=work, daemon=True).start()

    def fill(self, games):
        selected = self.selected()
        keep = selected.game.key if selected else None
        self.games = games
        self.grid.remove_all()
        for game in games:
            self.grid.append(Card(game))
        self.update_chips()
        self.update_hints()
        self.refilter(keep)

    def visible_game(self, card):
        return self.filter == 0 or card.game.source == FILTERS[self.filter]

    def compare(self, a, b):
        if self.sort == 0 and a.game.last_played != b.game.last_played:
            return -1 if a.game.last_played > b.game.last_played else 1
        x, y = a.game.title.casefold(), b.game.title.casefold()
        return (x > y) - (x < y)

    def cards(self):
        cards, child = [], self.grid.get_first_child()
        while child:
            if isinstance(child, Card) and child.get_child_visible():
                cards.append(child)
            child = child.get_next_sibling()
        return cards

    def refilter(self, keep=None):
        self.grid.invalidate_filter()
        self.grid.invalidate_sort()
        cards = self.cards()
        self.stack.set_visible_child_name("games" if cards else "empty")
        if not cards:
            self.title.set_label("")
            self.subtitle.set_label("")
            self.backdrop.set_paintable(None)
            return
        target = next((c for c in cards if c.game.key == keep), cards[0])
        self.select(target)

    # Selection and movement

    def selected(self):
        chosen = self.grid.get_selected_children()
        return chosen[0] if chosen else None

    def select(self, card):
        self.grid.select_child(card)
        card.grab_focus()

    def show_selected(self):
        card = self.selected()
        if not card:
            return
        game = card.game
        self.title.set_label(game.title)
        self.subtitle.set_label(f"{game.source}  ·  {played(game)}")
        background = game.hero or (card.picture.get_file().get_path() if card.picture.get_file() else "")
        if background:
            self.backdrop.set_filename(background)
        else:
            self.backdrop.set_paintable(None)

    def move(self, direction):
        cards = self.cards()
        current = self.selected()
        if not cards:
            return
        if current not in cards:
            self.select(cards[0])
            return
        index = cards.index(current)
        top = cards[0].compute_point(self.grid, _point())[1].y if len(cards) > 1 else 0
        columns = sum(1 for c in cards if c.compute_point(self.grid, _point())[1].y == top) or 1
        target = index + {"left": -1, "right": 1, "up": -columns, "down": columns}[direction]
        if 0 <= target < len(cards):
            self.select(cards[target])
        elif direction == "down" and index // columns < (len(cards) - 1) // columns:
            self.select(cards[-1])   # the last row is shorter: go to its last game

    # Actions

    def on_action(self, action):
        self.set_focus_visible(True)   # show which button a pad user is on
        dialog = self.get_visible_dialog()
        if dialog:
            if action in ("up", "down", "left", "right"):
                direction = {"up": Gtk.DirectionType.UP, "down": Gtk.DirectionType.DOWN,
                             "left": Gtk.DirectionType.LEFT, "right": Gtk.DirectionType.RIGHT}[action]
                dialog.child_focus(direction)
            elif action == "accept":
                focus = self.get_focus()
                if focus:
                    focus.activate()
            elif action in ("back", "menu"):
                dialog.close()
            return
        if action in ("up", "down", "left", "right"):
            self.move(action)
        elif action == "accept":
            card = self.selected()
            if card:
                self.launch(card.game)
        elif action == "back":
            if self.filter:
                self.set_filter(0)
        elif action == "filter":
            self.set_filter(self.next_filter(1))
        elif action in ("previous", "next"):
            self.set_filter(self.next_filter(-1 if action == "previous" else 1))
        elif action == "sort":
            self.sort = (self.sort + 1) % len(SORTS)
            self.update_hints()
            self.refilter(self.selected().game.key if self.selected() else None)
        elif action == "menu":
            self.menu()
        elif action == "refresh":
            self.reload()

    def next_filter(self, step):
        available = [i for i, chip in enumerate(self.chips) if chip.get_visible()]
        position = available.index(self.filter) if self.filter in available else 0
        return available[(position + step) % len(available)]

    def set_filter(self, index):
        self.filter = index
        self.update_chips()
        self.refilter(self.selected().game.key if self.selected() else None)

    def on_key(self, _controller, key, _code, state):
        if state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.ALT_MASK):
            return False
        action = {Gdk.KEY_Up: "up", Gdk.KEY_Down: "down", Gdk.KEY_Left: "left", Gdk.KEY_Right: "right",
                  Gdk.KEY_Return: "accept", Gdk.KEY_KP_Enter: "accept", Gdk.KEY_space: "accept",
                  Gdk.KEY_Escape: "back", Gdk.KEY_BackSpace: "back", Gdk.KEY_s: "sort", Gdk.KEY_f: "filter",
                  Gdk.KEY_m: "menu", Gdk.KEY_Menu: "menu", Gdk.KEY_F5: "refresh", Gdk.KEY_Tab: "next",
                  Gdk.KEY_ISO_Left_Tab: "previous"}.get(key)
        if self.get_visible_dialog():
            return False   # the dialog handles its own keys
        if action:
            self.on_action(action)
            return True
        return False

    def on_active(self):
        # Back from a game: pick up new play times and installs
        if self.is_active() and time.monotonic() - self.loaded_at > REFRESH_AFTER_S:
            self.reload()

    def launch(self, game):
        try:
            Gio.AppInfo.launch_default_for_uri(game.launch, None)
            self.toasts.add_toast(Adw.Toast(title=f"Starting {game.title}…", timeout=4))
        except GLib.Error:
            self.toasts.add_toast(Adw.Toast(title=f"{game.source} is not installed, so {game.title} cannot start",
                                            timeout=5))

    def spawn(self, argv):
        try:
            Gio.Subprocess.new(argv, Gio.SubprocessFlags.NONE)
        except GLib.Error as error:
            self.toasts.add_toast(Adw.Toast(title=error.message))

    def menu(self):
        dialog = Adw.AlertDialog(heading="Mesale Play")
        # Stacked buttons are shown last first: this reads Exit, Refresh, Suspend, Power off, Close
        for response, label in [("cancel", "Close"), ("poweroff", "Power off"), ("suspend", "Suspend"),
                                ("refresh", "Refresh library"), ("exit", "Exit Play")]:
            dialog.add_response(response, label)
        dialog.set_close_response("cancel")
        dialog.set_default_response("exit")   # the top button has the focus
        dialog.set_response_appearance("exit", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self.on_menu)
        dialog.present(self)

    def on_menu(self, _dialog, response):
        if response == "refresh":
            self.reload()
        elif response == "exit":
            self.get_application().quit()
        elif response == "suspend":
            self.spawn(["systemctl", "suspend"])
        elif response == "poweroff":
            self.spawn(["gnome-session-quit", "--power-off"])


def _point():
    gi.require_version("Graphene", "1.0")
    from gi.repository import Graphene
    return Graphene.Point()


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.mesale.Play", flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_activate(self):
        window = self.get_active_window()
        if not window:
            provider = Gtk.CssProvider()
            provider.load_from_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "style.css"))
            Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider,
                                                      Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
            window = Window(self)
            if "--windowed" not in sys.argv:
                window.fullscreen()
        window.present()


if __name__ == "__main__":
    sys.exit(Application().run([a for a in sys.argv if a != "--windowed"]))
