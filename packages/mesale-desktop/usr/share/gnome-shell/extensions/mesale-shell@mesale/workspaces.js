// Super+1..9 goes to a workspace, Super+Shift+1..9 takes the focused window there.
// Workspaces are made as needed, so a number past the last one means the last,
// empty workspace: GNOME then opens a new empty one after it.
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const COUNT = 9;
const MODES = Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW;

function workspace(number) {
    const manager = global.workspace_manager;
    return manager.get_workspace_by_index(Math.min(number, manager.n_workspaces) - 1);
}

function moveFocused(number) {
    const window = global.display.focus_window;
    if (!window || window.is_always_on_all_workspaces() || window.skip_taskbar)
        return;
    Main.wm.actionMoveWindow(window, workspace(number));
}

const names = () => Array.from({length: COUNT}, (_, i) => [`workspace-${i + 1}`, `move-to-workspace-${i + 1}`, i + 1]);

export function enable(settings) {
    for (const [go, move, number] of names()) {
        Main.wm.addKeybinding(go, settings, Meta.KeyBindingFlags.IGNORE_AUTOREPEAT, MODES,
            () => Main.wm.actionMoveWorkspace(workspace(number)));
        Main.wm.addKeybinding(move, settings, Meta.KeyBindingFlags.IGNORE_AUTOREPEAT, Shell.ActionMode.NORMAL,
            () => moveFocused(number));
    }
}

export function disable() {
    for (const [go, move] of names()) {
        Main.wm.removeKeybinding(go);
        Main.wm.removeKeybinding(move);
    }
}
