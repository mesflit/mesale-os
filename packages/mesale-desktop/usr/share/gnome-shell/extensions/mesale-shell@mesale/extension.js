import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import {CommandBar} from './commandBar.js';
import * as Search from './search/index.js';
import {ThemeManager} from './theme.js';
import * as Workspaces from './workspaces.js';

export default class MesaleShell extends Extension {
    enable() {
        this._skipStartupOverview();
        this._settings = this.getSettings();
        Search.start(this._settings);
        this._commandBar = new CommandBar();
        this._theme = new ThemeManager(this._settings, light => this._commandBar.setLight(light));

        Main.wm.addKeybinding('command-bar', this._settings, Meta.KeyBindingFlags.IGNORE_AUTOREPEAT,
            Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW, () => this._commandBar.toggle());
        Workspaces.enable(this._settings);
    }

    disable() {
        Main.wm.removeKeybinding('command-bar');
        Workspaces.disable();
        Main.layoutManager.disconnectObject(this);
        if (this._overviewTimer)
            GLib.source_remove(this._overviewTimer);
        this._overviewTimer = 0;
        this._theme.destroy();
        this._commandBar.close();
        this._commandBar.destroy();
        Search.stop(this._settings);
        this._theme = this._commandBar = this._settings = null;
    }

    // Land on the desktop, not in the overview. Extensions can load before or after
    // the startup animation, so both cases are handled.
    _skipStartupOverview() {
        if (Main.layoutManager._startingUp) {
            Main.sessionMode.hasOverview = false;
            Main.layoutManager.connectObject('startup-complete', () => {
                Main.sessionMode.hasOverview = true;
                this._hideOverviewSoon();
            }, this);
        } else {
            this._hideOverviewSoon();
        }
    }

    _hideOverviewSoon() {
        this._overviewTimer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 250, () => {
            this._overviewTimer = 0;
            if (Main.overview.visible)
                Main.overview.hide();
            return GLib.SOURCE_REMOVE;
        });
    }
}
