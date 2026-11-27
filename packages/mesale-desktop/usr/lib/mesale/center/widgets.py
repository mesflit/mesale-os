"""Small building blocks for Mesale Center's settings pages.

Rows that need a settings schema which is not installed (an extension removed, a GNOME
part missing) are simply not shown, so a page never fails as a whole.
"""
from gi.repository import Adw, Gio, Gtk


def settings(schema_id):
    """Gio.Settings for the schema, or None when it is not installed."""
    source = Gio.SettingsSchemaSource.get_default()
    if source is None or source.lookup(schema_id, True) is None:
        return None
    return Gio.Settings.new(schema_id)


def has_key(store, key):
    return store is not None and store.props.settings_schema.has_key(key)


def slider(title, value, low, high, on_change, subtitle=None, step=1):
    scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, low, high, step)
    scale.set_value(value)
    scale.set_size_request(240, -1)
    scale.set_draw_value(True)
    scale.set_value_pos(Gtk.PositionType.LEFT)
    scale.connect("value-changed", lambda s: on_change(int(s.get_value())))
    row = Adw.ActionRow(title=title, subtitle=subtitle)
    row.add_suffix(scale)
    return row


def switch(title, store, key, subtitle=None, invert=False):
    """A switch bound to a boolean key, or None when the key does not exist."""
    if not has_key(store, key):
        return None
    row = Adw.SwitchRow(title=title, subtitle=subtitle)
    flags = Gio.SettingsBindFlags.DEFAULT | (Gio.SettingsBindFlags.INVERT_BOOLEAN if invert else 0)
    store.bind(key, row, "active", flags)
    return row


def choice(title, options, current, on_change, subtitle=None):
    """A drop-down of (value, label) pairs. on_change(value) runs when the user picks one."""
    values = [value for value, _label in options]
    row = Adw.ComboRow(title=title, subtitle=subtitle, model=Gtk.StringList.new([label for _value, label in options]))
    row.set_selected(values.index(current) if current in values else 0)
    row.connect("notify::selected", lambda r, _param: on_change(values[r.get_selected()]))
    return row


def string_choice(title, options, store, key, subtitle=None):
    """A drop-down bound to a string key, or None when the key does not exist."""
    if not has_key(store, key):
        return None
    return choice(title, options, store.get_string(key), lambda value: store.set_string(key, value), subtitle)


def link(title, subtitle, on_activate):
    row = Adw.ActionRow(title=title, subtitle=subtitle, activatable=True)
    row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
    row.connect("activated", lambda _row: on_activate())
    return row


def group(title, rows, description=None):
    """A group of the rows that exist; None when none does."""
    rows = [row for row in rows if row is not None]
    if not rows:
        return None
    box = Adw.PreferencesGroup(title=title, description=description)
    for row in rows:
        box.add(row)
    return box


def spawn(argv):
    try:
        Gio.Subprocess.new(argv, Gio.SubprocessFlags.NONE)
    except Exception as error:
        print(f"Mesale Center: {argv[0]}: {error}")
