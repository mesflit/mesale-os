// Light, dark or automatic theme, and the colors that follow it.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

const PANEL_SCHEMA = 'org.gnome.shell.extensions.dash-to-panel';
const DAY_STARTS = 7;
const DAY_ENDS = 19;
const PANEL_COLORS = {
    light: {background: '#ffffff', border: 'rgba(255,255,255,0.55)'},
    dark: {background: '#0f1730', border: 'rgba(190,210,255,0.16)'},
};

export class ThemeManager {
    constructor(settings, onChange) {
        this._settings = settings;
        this._onChange = onChange;
        this._interface = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
        const schema = Gio.SettingsSchemaSource.get_default().lookup(PANEL_SCHEMA, true);
        this._panel = schema ? new Gio.Settings({settings_schema: schema}) : null;

        this._settings.connectObject('changed::theme-mode', () => this._applyMode(), this);
        this._interface.connectObject('changed::color-scheme', () => this._onSchemeChanged(), this);
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_LOW, 60, () => {
            if (this._settings.get_string('theme-mode') === 'auto')
                this._applyMode();
            return GLib.SOURCE_CONTINUE;
        });
        this._applyMode();
        this._applyColors();
    }

    destroy() {
        GLib.source_remove(this._timer);
        this._settings.disconnectObject(this);
        this._interface.disconnectObject(this);
    }

    _wantedScheme() {
        const mode = this._settings.get_string('theme-mode');
        const hour = GLib.DateTime.new_now_local().get_hour();
        const night = hour < DAY_STARTS || hour >= DAY_ENDS;
        return mode === 'dark' || (mode === 'auto' && night) ? 'prefer-dark' : 'prefer-light';
    }

    _applyMode() {
        const scheme = this._wantedScheme();
        if (this._interface.get_string('color-scheme') !== scheme)
            this._interface.set_string('color-scheme', scheme);
    }

    // GNOME's Dark Style switch and Settings write color-scheme directly. Their choice
    // becomes our mode, so nothing flips it back. They use 'default' for light, which
    // would leave the shell itself dark; changing the mode turns it into 'prefer-light'.
    _onSchemeChanged() {
        const scheme = this._interface.get_string('color-scheme');
        if (scheme !== this._wantedScheme()) {
            const mode = scheme === 'prefer-dark' ? 'dark' : 'light';
            if (this._settings.get_string('theme-mode') !== mode)
                this._settings.set_string('theme-mode', mode);
            this._applyMode();
        }
        this._applyColors();
    }

    _applyColors() {
        const light = this._interface.get_string('color-scheme') !== 'prefer-dark';
        const colors = light ? PANEL_COLORS.light : PANEL_COLORS.dark;
        this._panel?.set_string('trans-bg-color', colors.background);
        this._panel?.set_string('trans-border-custom-color', colors.border);
        this._linkGtkCss(light);
        this._onChange(light);
    }

    // Never touches a gtk.css the user wrote: only replaces our own symlink.
    _linkGtkCss(light) {
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
}
