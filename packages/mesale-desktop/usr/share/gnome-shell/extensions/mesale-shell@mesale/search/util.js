// Shared helpers for the search modules.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

export {normalize} from '../parse.js';

export const MAX_RESULTS = 8;

export const launchContext = () => global.create_app_launch_context(0, -1);
export const openUri = uri => Gio.AppInfo.launch_default_for_uri(uri, launchContext());
export const copy = text => St.Clipboard.get_default().set_text(St.ClipboardType.CLIPBOARD, text);
export const spawn = argv => GLib.spawn_async(null, argv, null, GLib.SpawnFlags.SEARCH_PATH, null);
export const notify = (title, body) => Main.notify?.(title, body);

export function inTerminal(command) {
    const hold = `${command}; echo; read -rsn1 -p "Press any key to close"`;
    // Ptyxis opens its own window for a command; --new-window added an empty second one
    for (const [program, ...args] of [['ptyxis', '--'], ['gnome-terminal', '--'], ['kgx', '--']]) {
        if (GLib.find_program_in_path(program)) {
            spawn([program, ...args, 'bash', '-c', hold]);
            return;
        }
    }
    notify('No terminal', 'Install a terminal to run commands');
}

export function hasSchema(id) {
    return Gio.SettingsSchemaSource.get_default().lookup(id, true) !== null;
}
