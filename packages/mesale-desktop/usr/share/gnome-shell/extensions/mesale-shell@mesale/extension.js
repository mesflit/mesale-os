import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import {KomutCubugu} from './command.js';

const CUBUK = 'org.gnome.shell.extensions.dash-to-panel';

export default class MesaleShell extends Extension {
    enable() {
        // Land on the desktop, not in the overview
        if (Main.layoutManager._startingUp) {
            Main.sessionMode.hasOverview = false;
            Main.layoutManager.connectObject('startup-complete', () => {
                Main.sessionMode.hasOverview = true;
                Main.overview.hide();
            }, this);
        }
        this._ayar = this.getSettings();
        this._arayuz = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
        const sema = Gio.SettingsSchemaSource.get_default().lookup(CUBUK, true);
        this._cubukAyar = sema ? new Gio.Settings({settings_schema: sema}) : null;

        this._komut = new KomutCubugu();
        Main.wm.addKeybinding('command-bar', this._ayar, Meta.KeyBindingFlags.IGNORE_AUTOREPEAT,
            Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW, () => this._komut.acKapat());

        this._ayar.connectObject('changed::theme-mode', () => this._temaUygula(), this);
        this._arayuz.connectObject('changed::color-scheme', () => this._renkUygula(), this);
        // Auto theme: check the clock once a minute (light 07-19)
        this._zaman = GLib.timeout_add_seconds(GLib.PRIORITY_LOW, 60, () => {
            this._temaUygula();
            return GLib.SOURCE_CONTINUE;
        });
        this._temaUygula();
        this._renkUygula();
    }

    disable() {
        GLib.source_remove(this._zaman);
        Main.wm.removeKeybinding('command-bar');
        Main.layoutManager.disconnectObject(this);
        this._ayar.disconnectObject(this);
        this._arayuz.disconnectObject(this);
        this._komut.kapat();
        this._komut.destroy();
        this._komut = this._ayar = this._arayuz = this._cubukAyar = null;
    }

    _renkUygula() {
        const acik = this._arayuz.get_string('color-scheme') === 'prefer-light';
        this._komut.renkAyarla(acik);
        this._gtkApply(acik);
        this._cubukAyar?.set_string('trans-bg-color', acik ? '#ffffff' : '#0f1730');
        this._cubukAyar?.set_string('trans-border-custom-color', acik ? 'rgba(255,255,255,0.55)' : 'rgba(190,210,255,0.16)');
    }

    // GTK tint: link our css, never touch a file the user made
    _gtkApply(light) {
        const dir = GLib.build_filenamev([GLib.get_user_config_dir(), 'gtk-4.0']);
        const link = Gio.File.new_for_path(`${dir}/gtk.css`);
        try {
            GLib.mkdir_with_parents(dir, 0o755);
            const type = link.query_file_type(Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, null);
            if (type === Gio.FileType.SYMBOLIC_LINK)
                link.delete(null);
            else if (type !== Gio.FileType.UNKNOWN)
                return;
            link.make_symbolic_link(`/usr/share/mesale/gtk-${light ? 'light' : 'dark'}.css`, null);
        } catch (e) {
            console.warn(`mesale-shell: ${e.message}`);
        }
    }

    _temaUygula() {
        const mod = this._ayar.get_string('theme-mode');
        const saat = GLib.DateTime.new_now_local().get_hour();
        const koyu = mod === 'dark' || (mod === 'auto' && (saat < 7 || saat >= 19));
        const istenen = koyu ? 'prefer-dark' : 'prefer-light';
        if (this._arayuz.get_string('color-scheme') !== istenen)
            this._arayuz.set_string('color-scheme', istenen);
    }
}
