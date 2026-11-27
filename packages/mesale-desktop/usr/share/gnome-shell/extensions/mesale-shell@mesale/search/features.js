// Mesale features that are not installed yet, from the files mesale-feature reads.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {normalize, notify} from './util.js';

const FEATURES = '/usr/lib/mesale/features';
let features = null;

function load() {
    features = [];
    try {
        const folder = Gio.File.new_for_path(FEATURES);
        const enumerator = folder.enumerate_children('standard::name', Gio.FileQueryInfoFlags.NONE, null);
        let info;
        while ((info = enumerator.next_file(null))) {
            const name = info.get_name();
            const [, bytes] = GLib.file_get_contents(`${FEATURES}/${name}`);
            const text = new TextDecoder().decode(bytes);
            const value = key => (new RegExp(`^${key}="?([^"\\n]*)`, 'm').exec(text) ?? [])[1] ?? '';
            features.push({name, title: value('NAME') || name, desc: value('DESC'), group: value('GROUP'),
                pkgs: value('PKGS').split(/\s+/).filter(Boolean), flatpaks: value('FLATPAKS').split(/\s+/).filter(Boolean),
                bin: value('BIN')});
        }
        enumerator.close(null);
    } catch {}
}

function installed(feature) {
    if (feature.bin)
        return GLib.find_program_in_path(feature.bin) !== null;
    const dpkg = p => [`${p}.list`, `${p}:amd64.list`].some(f => GLib.file_test(`/var/lib/dpkg/info/${f}`, GLib.FileTest.EXISTS));
    const flatpak = p => GLib.file_test(`/var/lib/flatpak/app/${p}`, GLib.FileTest.EXISTS);
    return feature.pkgs.every(dpkg) && feature.flatpaks.every(flatpak);
}

function install(feature) {
    try {
        const process = Gio.Subprocess.new(['pkexec', '/usr/bin/mesale-feature', 'add', feature.name],
            Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_SILENCE);
        notify(feature.title, 'Installing…');
        process.wait_check_async(null, (_process, result) => {
            let done = false;
            try {
                done = process.wait_check_finish(result);
            } catch {}
            notify(feature.title, done ? 'Installed' : 'Could not install. Mesale Center shows the details.');
        });
    } catch (e) {
        logError(e, 'Mesale command bar: could not start mesale-feature');
    }
}

export function* featureResults(query) {
    if (query.length < 3)
        return;
    if (features === null)
        load();
    for (const feature of features) {
        if (feature.group === 'apps' || !normalize(`${feature.name} ${feature.title}`).includes(query) || installed(feature))
            continue;
        yield {title: `Install ${feature.title}`, subtitle: feature.desc, kind: 'Feature', icon: 'software-install-symbolic',
            run: () => install(feature)};
    }
}

// Read again on the next search: something may have been installed meanwhile
export function forgetFeatures() {
    features = null;
}
