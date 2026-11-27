// Files for the command bar: recently used files, an index of the user's folders built
// in the background (never blocking the shell), and browsing a typed path.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

const ATTRIBUTES = 'standard::name,standard::type,standard::is-hidden,standard::content-type';
const MAX_INDEX = 6000;
const MAX_DEPTH = 4;
const STALE_MS = 2 * 60 * 1000;
const SKIP = new Set(['node_modules', '__pycache__', 'target', 'build', 'dist', 'venv', '.git']);

let index = [];
let indexedAt = 0;
let cancellable = null;

// Lower case without accents, dotless i as i
export const normalize = text => text.toLowerCase().normalize('NFD').replace(/\p{M}/gu, '').replace(/ı/g, 'i');

function entry(file, info) {
    const folder = info.get_file_type() === Gio.FileType.DIRECTORY;
    const type = info.get_content_type();
    return {
        name: info.get_name(), key: normalize(info.get_name()), file, folder,
        icon: folder ? 'folder' : (type ? Gio.content_type_get_icon(type) : 'text-x-generic'),
    };
}

function roots() {
    const home = GLib.get_home_dir();
    const special = [GLib.UserDirectory.DIRECTORY_DESKTOP, GLib.UserDirectory.DIRECTORY_DOCUMENTS,
        GLib.UserDirectory.DIRECTORY_DOWNLOAD, GLib.UserDirectory.DIRECTORY_MUSIC,
        GLib.UserDirectory.DIRECTORY_PICTURES, GLib.UserDirectory.DIRECTORY_VIDEOS]
        .map(d => GLib.get_user_special_dir(d)).filter(p => p && p !== home);
    // [folder, its depth, how deep to go]: the home folder only one level, the user folders deeper
    return [[home, 0, 1], ...special.map(p => [p, 0, MAX_DEPTH])];
}

function list(file, token, done) {
    file.enumerate_children_async(ATTRIBUTES, Gio.FileQueryInfoFlags.NONE, GLib.PRIORITY_LOW, token,
        (_file, result) => {
            let enumerator;
            try {
                enumerator = file.enumerate_children_finish(result);
            } catch {
                done([]);
                return;
            }
            const infos = [];
            const next = () => enumerator.next_files_async(200, GLib.PRIORITY_LOW, token, (_e, res) => {
                let batch = [];
                try {
                    batch = enumerator.next_files_finish(res);
                } catch {}
                if (!batch.length) {
                    enumerator.close_async(GLib.PRIORITY_LOW, null, null);
                    done(infos);
                    return;
                }
                infos.push(...batch);
                next();
            });
            next();
        });
}

// Rebuild the index if it is old. onUpdate runs when the new index is ready.
export function refresh(onUpdate) {
    if (cancellable || Date.now() - indexedAt < STALE_MS)
        return;
    const token = cancellable = new Gio.Cancellable();
    const found = [], seen = new Set();
    const queue = roots().map(([path, depth, limit]) => [Gio.File.new_for_path(path), depth, limit]);
    const step = () => {
        if (token !== cancellable)
            return;   // stopped or replaced
        const item = queue.shift();
        if (!item || found.length >= MAX_INDEX) {
            index = found;
            indexedAt = Date.now();
            cancellable = null;
            onUpdate?.();
            return;
        }
        const [folder, depth, limit] = item;
        const path = folder.get_path();
        if (seen.has(path)) {
            step();
            return;
        }
        seen.add(path);
        list(folder, token, infos => {
            if (token !== cancellable)
                return;
            for (const info of infos) {
                if (info.get_is_hidden() || SKIP.has(info.get_name()))
                    continue;
                const child = folder.get_child(info.get_name());
                const item = entry(child, info);
                found.push(item);
                if (item.folder && depth + 1 < limit)
                    queue.push([child, depth + 1, limit]);
            }
            step();
        });
    };
    step();
}

export function stop() {
    cancellable?.cancel();
    cancellable = null;
    index = [];
    indexedAt = 0;
}

// Best matches first: name starts with the query, then shorter names.
export function search(query, limit) {
    const hits = [];
    for (const item of index) {
        const at = item.key.indexOf(query);
        if (at >= 0)
            hits.push([at === 0 ? 0 : 1, item.name.length, item]);
    }
    hits.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    return hits.slice(0, limit).map(hit => hit[2]);
}

// Recently used files, newest first, from the list GTK apps keep.
export function recent(query, limit) {
    const results = [];
    try {
        const path = GLib.build_filenamev([GLib.get_user_data_dir(), 'recently-used.xbel']);
        const [, bytes] = GLib.file_get_contents(path);
        const text = new TextDecoder().decode(bytes);
        const items = [...text.matchAll(/<bookmark href="([^"]+)"[^>]*modified="([^"]+)"/g)]
            .map(m => [m[1].replace(/&amp;/g, '&'), m[2]])
            .filter(([uri]) => uri.startsWith('file://'))
            .sort((a, b) => b[1].localeCompare(a[1]));
        for (const [uri] of items) {
            const file = Gio.File.new_for_uri(uri);
            const name = file.get_basename();
            if (!normalize(name).includes(query) || !file.query_exists(null))
                continue;
            let type = null;
            try {
                type = file.query_info('standard::content-type', Gio.FileQueryInfoFlags.NONE, null).get_content_type();
            } catch {}
            results.push({name, file, folder: false, icon: type ? Gio.content_type_get_icon(type) : 'text-x-generic'});
            if (results.length >= limit)
                break;
        }
    } catch {}
    return results;
}

// Entries of the folder in a typed path such as "~/Docu" or "/etc/apt/".
export function browse(text, limit) {
    const home = GLib.get_home_dir();
    const path = text.startsWith('~') ? home + text.slice(1) : text;
    const cut = path.lastIndexOf('/');
    const folder = Gio.File.new_for_path(path.slice(0, cut + 1) || '/');
    const part = normalize(path.slice(cut + 1));
    const items = [];
    try {
        const enumerator = folder.enumerate_children(ATTRIBUTES, Gio.FileQueryInfoFlags.NONE, null);
        let info, seen = 0;
        while ((info = enumerator.next_file(null)) && seen++ < 1000) {
            if (info.get_is_hidden() && !part.startsWith('.'))
                continue;
            if (normalize(info.get_name()).startsWith(part))
                items.push(entry(folder.get_child(info.get_name()), info));
        }
        enumerator.close(null);
    } catch {
        return {folder, items: []};
    }
    items.sort((a, b) => Number(b.folder) - Number(a.folder) || a.name.localeCompare(b.name));
    return {folder, items: items.slice(0, limit)};
}

// "~/Documents" instead of "/home/user/Documents"
export function shortPath(file) {
    const path = file.get_path() ?? file.get_uri();
    const home = GLib.get_home_dir();
    return path.startsWith(home) ? `~${path.slice(home.length)}` : path;
}
