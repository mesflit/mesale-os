// What the user opens from the command bar, so frequent choices rise to the top.
// Stored as {id: [count, last used in ms]} in ~/.local/share/mesale/command-bar.json.
import GLib from 'gi://GLib';

const FILE = GLib.build_filenamev([GLib.get_user_data_dir(), 'mesale', 'command-bar.json']);
const MAX_ITEMS = 200;
const DAY = 86400000;

let usage = {};

export function load() {
    try {
        const [, bytes] = GLib.file_get_contents(FILE);
        usage = JSON.parse(new TextDecoder().decode(bytes)) ?? {};
    } catch {
        usage = {};
    }
}

function save() {
    try {
        GLib.mkdir_with_parents(GLib.path_get_dirname(FILE), 0o700);
        GLib.file_set_contents(FILE, JSON.stringify(usage));
    } catch (e) {
        logError(e, 'Mesale command bar: could not save history');
    }
}

export function record(id) {
    if (!id)
        return;
    const [count] = usage[id] ?? [0];
    usage[id] = [count + 1, Date.now()];
    const ids = Object.keys(usage);
    if (ids.length > MAX_ITEMS) {
        ids.sort((a, b) => score(a) - score(b));
        for (const old of ids.slice(0, ids.length - MAX_ITEMS))
            delete usage[old];
    }
    save();
}

// Frequent and recent: the count fades by half each week without use.
export function score(id) {
    const entry = usage[id];
    if (!entry)
        return 0;
    return entry[0] * 0.5 ** ((Date.now() - entry[1]) / (7 * DAY));
}

export function top(count) {
    return Object.keys(usage).sort((a, b) => score(b) - score(a)).slice(0, count);
}
