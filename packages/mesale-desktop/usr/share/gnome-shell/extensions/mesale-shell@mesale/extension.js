import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import {CommandBar} from './commandBar.js';
import {ThemeManager} from './theme.js';

export default class MesaleShell extends Extension {
    enable() {
        this._skipStartupOverview();
        this._settings = this.getSettings();
        this._commandBar = new CommandBar();
        this._theme = new ThemeManager(this._settings, light => this._commandBar.setLight(light));

        Main.wm.addKeybinding('command-bar', this._settings, Meta.KeyBindingFlags.IGNORE_AUTOREPEAT,
            Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW, () => this._commandBar.toggle());
    }

    disable() {
        Main.wm.removeKeybinding('command-bar');
        Main.layoutManager.disconnectObject(this);
        this._theme.destroy();
        this._commandBar.close();
        this._commandBar.destroy();
        this._theme = this._commandBar = this._settings = null;
    }

    // Land on the desktop, not in the overview
    _skipStartupOverview() {
        if (!Main.layoutManager._startingUp)
            return;
        Main.sessionMode.hasOverview = false;
        Main.layoutManager.connectObject('startup-complete', () => {
            Main.sessionMode.hasOverview = true;
            Main.overview.hide();
        }, this);
    }
}
