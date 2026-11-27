"""Gamepads through libmanette, turned into a few actions:
up down left right, accept, back, sort, filter, menu, previous, next.

libmanette maps every known pad to the standard Linux codes, so an Xbox, PlayStation,
Switch or generic pad all work the same. Without libmanette Play still works with
the keyboard.
"""
import gi
from gi.repository import GLib

try:
    gi.require_version("Manette", "0.2")
    from gi.repository import Manette
except (ValueError, ImportError):
    Manette = None

# Linux input codes (linux/input-event-codes.h). North is the top face button, west the left one.
BUTTONS = {
    304: "accept", 305: "back", 307: "filter", 308: "sort",   # south, east, north, west
    310: "previous", 311: "next", 315: "menu", 316: "menu",    # bumpers, start, guide
    544: "up", 545: "down", 546: "left", 547: "right",         # d-pad as buttons
}
STICK = {0: ("left", "right"), 1: ("up", "down")}              # left stick
HAT = {16: ("left", "right"), 17: ("up", "down")}              # d-pad as a hat
THRESHOLD = 0.6
FIRST_REPEAT_MS, REPEAT_MS = 380, 130


class Gamepads:
    def __init__(self, on_action, accepting):
        """on_action(name) is called for each action while accepting() is true."""
        self.on_action, self.accepting = on_action, accepting
        self.devices, self.held, self.timer = set(), None, 0
        self.listeners = []
        if Manette is None:
            return
        self.monitor = Manette.Monitor.new()
        self.monitor.connect("device-connected", lambda _m, device: self.add(device))
        self.monitor.connect("device-disconnected", lambda _m, device: self.devices.discard(device))
        iterator = self.monitor.iterate()
        while True:
            found, device = iterator.next()
            if not found:
                break
            self.add(device)

    @property
    def connected(self):
        return bool(self.devices)

    def add(self, device):
        self.devices.add(device)
        device.connect("button-press-event", self.on_button)
        device.connect("absolute-axis-event", self.on_axis)
        device.connect("hat-axis-event", self.on_hat)
        for listener in self.listeners:
            listener()

    def emit(self, action):
        # Ignore the pad while a game (or anything else) has the focus
        if self.accepting():
            self.on_action(action)

    def on_button(self, _device, event):
        found, button = event.get_button()
        if found and button in BUTTONS:
            self.emit(BUTTONS[button])

    def on_axis(self, _device, event):
        found, axis, value = event.get_absolute()
        if found and axis in STICK:
            self.direction(axis, STICK[axis], -1 if value < -THRESHOLD else 1 if value > THRESHOLD else 0)

    def on_hat(self, _device, event):
        found, axis, value = event.get_hat()
        if found and axis in HAT:
            self.direction(axis, HAT[axis], -1 if value < 0 else 1 if value > 0 else 0)

    def direction(self, axis, names, sign):
        """Move once, then repeat while the stick or d-pad is held."""
        if sign == 0:
            if self.held and self.held[0] == axis:
                self.stop_repeat()
            return
        action = names[0] if sign < 0 else names[1]
        if self.held == (axis, action):
            return
        self.stop_repeat()
        self.held = (axis, action)
        self.emit(action)
        self.timer = GLib.timeout_add(FIRST_REPEAT_MS, self.repeat_start)

    def repeat_start(self):
        self.timer = GLib.timeout_add(REPEAT_MS, self.repeat)
        return GLib.SOURCE_REMOVE

    def repeat(self):
        if not self.held:
            self.timer = 0
            return GLib.SOURCE_REMOVE
        self.emit(self.held[1])
        return GLib.SOURCE_CONTINUE

    def stop_repeat(self):
        if self.timer:
            GLib.source_remove(self.timer)
        self.timer, self.held = 0, None
