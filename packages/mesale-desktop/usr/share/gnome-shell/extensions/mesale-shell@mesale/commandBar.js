// Command bar (Super+Space): a blurred overlay with an entry and a result list.
import Clutter from 'gi://Clutter';
import GObject from 'gi://GObject';
import Shell from 'gi://Shell';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {search} from './providers.js';

const OFFSET = -84;          // rests just above the bottom bar
const OFFSET_START = -60;
const STYLE = {
    light: 'background-color: rgba(246,249,255,0.94); color: #16243d; border-color: rgba(255,255,255,0.9);',
    dark: 'background-color: rgba(20,29,56,0.93); color: #eef4ff; border-color: rgba(190,210,255,0.16);',
};

export const CommandBar = GObject.registerClass(
class CommandBar extends St.Widget {
    _init() {
        super._init({visible: false, reactive: true, layout_manager: new Clutter.BinLayout()});
        this._results = [];
        this._selected = 0;
        this._buildUi();
        this._connectInput();
        Main.layoutManager.addTopChrome(this);
        this.hide();
    }

    _buildUi() {
        // Dims the screen instead of blurring all of it: the windows stay readable
        // and the card stands out. The card itself is nearly opaque, since a blur
        // effect cannot follow its rounded corners.
        this._backdrop = new St.Widget({style_class: 'mesale-backdrop', x_expand: true, y_expand: true});
        this.add_child(this._backdrop);

        this._box = new St.BoxLayout({
            style_class: 'mesale-command', orientation: Clutter.Orientation.VERTICAL, reactive: true,
            x_align: Clutter.ActorAlign.CENTER, y_align: Clutter.ActorAlign.END, x_expand: true, y_expand: true,
        });
        this._list = new St.BoxLayout({style_class: 'mesale-list', orientation: Clutter.Orientation.VERTICAL});
        this._entry = new St.Entry({
            style_class: 'mesale-entry', hint_text: 'Search, open, calculate\u2026', can_focus: true, x_expand: true,
        });
        this._entry.set_primary_icon(new St.Icon({icon_name: 'system-search-symbolic', icon_size: 18}));
        this._separator = new St.Widget({style_class: 'mesale-separator', x_expand: true});
        this._box.add_child(this._list);
        this._box.add_child(this._separator);
        this._box.add_child(this._entry);
        this.add_child(this._box);
    }

    _connectInput() {
        const text = this._entry.clutter_text;
        text.connect('text-changed', () => this._refresh());
        text.connect('activate', () => this._activate());
        text.connect('key-press-event', (_actor, event) => this._onKey(event));

        const click = new Clutter.ClickGesture();
        click.connect('recognize', () => {
            if (!this._pointerInBox())
                this.close();
        });
        this.add_action(click);
    }

    _pointerInBox() {
        const [x, y] = global.get_pointer();
        const box = this._box.get_transformed_extents();
        return x >= box.get_x() && x <= box.get_x() + box.get_width() &&
            y >= box.get_y() && y <= box.get_y() + box.get_height();
    }

    setLight(light) {
        this._box.style = light ? STYLE.light : STYLE.dark;
    }

    toggle() {
        if (this.visible)
            this.close();
        else
            this._open();
    }

    _open() {
        const monitor = Main.layoutManager.primaryMonitor;
        this.set_position(monitor.x, monitor.y);
        this.set_size(monitor.width, monitor.height);
        this.show();
        this._grab = Main.pushModal(this, {actionMode: Shell.ActionMode.POPUP});
        if (!this._grab) {
            this.close();
            return;
        }
        this._entry.set_text('');
        this._refresh();
        this._entry.grab_key_focus();

        this.opacity = 0;
        this._box.translation_y = OFFSET_START;
        this.ease({opacity: 255, duration: 130, mode: Clutter.AnimationMode.EASE_OUT_QUAD});
        this._box.ease({translation_y: OFFSET, duration: 190, mode: Clutter.AnimationMode.EASE_OUT_CUBIC});
    }

    close() {
        if (this._grab) {
            Main.popModal(this._grab);
            this._grab = null;
        }
        this.hide();
    }

    _onKey(event) {
        switch (event.get_key_symbol()) {
        case Clutter.KEY_Escape:
            this.close();
            return Clutter.EVENT_STOP;
        case Clutter.KEY_Down:
        case Clutter.KEY_Tab:
            this._select(this._selected + 1);
            return Clutter.EVENT_STOP;
        case Clutter.KEY_Up:
        case Clutter.KEY_ISO_Left_Tab:
            this._select(this._selected - 1);
            return Clutter.EVENT_STOP;
        case Clutter.KEY_space:
            if (event.get_state() & Clutter.ModifierType.MOD4_MASK) {
                this.close();
                return Clutter.EVENT_STOP;
            }
        }
        return Clutter.EVENT_PROPAGATE;
    }

    _refresh() {
        this._list.destroy_all_children();
        this._results = search(this._entry.get_text());
        this._results.forEach((result, index) => this._list.add_child(this._createRow(result, index)));
        this._separator.visible = this._results.length > 0;
        this._select(0);
    }

    _createRow(result, index) {
        const icon = new St.Icon({icon_size: 26, y_align: Clutter.ActorAlign.CENTER});
        if (typeof result.icon === 'string')
            icon.icon_name = result.icon;
        else
            icon.gicon = result.icon;

        const content = new St.BoxLayout({x_expand: true, style: 'spacing: 12px;'});
        content.add_child(icon);
        content.add_child(new St.Label({
            text: result.title, style_class: 'mesale-title', x_expand: true, y_align: Clutter.ActorAlign.CENTER,
        }));
        // Apps need no label: their icon says it. Other results name their kind.
        if (result.kind !== 'App')
            content.add_child(new St.Label({text: result.kind, style_class: 'mesale-kind', y_align: Clutter.ActorAlign.CENTER}));
        // Return key hint, shown on the selected row only
        const key = new St.Label({text: '\u21b5', style_class: 'mesale-key', y_align: Clutter.ActorAlign.CENTER, visible: false});
        content.add_child(key);

        const row = new St.Button({style_class: 'mesale-row', x_expand: true, child: content});
        row._key = key;
        row.connect('clicked', () => {
            this._selected = index;
            this._activate();
        });
        // The pointer moves the selection, so only one row is ever highlighted.
        // Motion, not hover: a bar opening under a still pointer keeps the first row.
        row.connect('motion-event', () => {
            if (this._selected !== index)
                this._select(index);
            return Clutter.EVENT_PROPAGATE;
        });
        return row;
    }

    _select(index) {
        const rows = this._list.get_children();
        if (!rows.length)
            return;
        this._selected = (index + rows.length) % rows.length;
        rows.forEach((row, i) => {
            const selected = i === this._selected;
            if (selected)
                row.add_style_class_name('selected');
            else
                row.remove_style_class_name('selected');
            row._key.visible = selected;
        });
    }

    _activate() {
        const result = this._results[this._selected];
        this.close();
        result?.run();
    }
});
