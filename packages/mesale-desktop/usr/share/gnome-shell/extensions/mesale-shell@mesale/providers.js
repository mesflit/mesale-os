// Search results for the command bar.
// A result is {title, subtitle?, kind, icon, run, alt?, fill?}:
//   run   what Enter does        alt   what Ctrl+Enter does (optional)
//   fill  text to put in the entry instead of running (folders while browsing)
//
// Prefixes:  > run a command   ? search the web   : emoji   @ clipboard   / or ~ browse files
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Shell from 'gi://Shell';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as SystemActions from 'resource:///org/gnome/shell/misc/systemActions.js';
import {calculate} from './calculator.js';
import {convert} from './units.js';
import {EMOJI} from './emoji.js';
import * as Clipboard from './clipboard.js';
import * as Files from './files.js';
import * as History from './history.js';

const MAX_RESULTS = 8;
const MAX_WINDOWS = 3;
const MAX_FILES = 4;
const WEB_SEARCH = 'https://duckduckgo.com/?q=';
const FEATURES = '/usr/lib/mesale/features';

const normalize = Files.normalize;
const timers = new Set();
let features = null;

// Helpers

const launchContext = () => global.create_app_launch_context(0, -1);
const openUri = uri => Gio.AppInfo.launch_default_for_uri(uri, launchContext());
const copy = text => St.Clipboard.get_default().set_text(St.ClipboardType.CLIPBOARD, text);
const spawn = argv => GLib.spawn_async(null, argv, null, GLib.SpawnFlags.SEARCH_PATH, null);
const notify = (title, body) => Main.notify?.(title, body);

function inTerminal(command) {
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

function hasSchema(id) {
    return Gio.SettingsSchemaSource.get_default().lookup(id, true) !== null;
}

function fileResult(item) {
    const openFolder = () => openUri((item.folder ? item.file : item.file.get_parent()).get_uri());
    return {
        title: item.name, subtitle: Files.shortPath(item.file.get_parent() ?? item.file),
        kind: item.folder ? 'Folder' : 'File', icon: item.icon,
        run: () => openUri(item.file.get_uri()), alt: openFolder,
    };
}

// Apps

const appResult = app => ({
    title: app.get_name(), kind: 'App', icon: app.get_icon(), id: app.get_id(),
    run: () => {
        History.record(app.get_id());
        app.activate();
    },
    alt: () => {
        History.record(app.get_id());
        app.open_new_window(-1);
    },
});

function* favorites() {
    const system = Shell.AppSystem.get_default();
    const ids = [...global.settings.get_strv('favorite-apps'), ...History.top(MAX_RESULTS)];
    const seen = new Set();
    for (const id of ids) {
        const app = seen.has(id) ? null : system.lookup_app(id);
        seen.add(id);
        if (app)
            yield appResult(app);
    }
}

function* apps(query) {
    const system = Shell.AppSystem.get_default();
    const seen = new Set(), found = [];
    Shell.AppSystem.search(query).forEach((group, rank) => {
        for (const id of group) {
            const app = system.lookup_app(id);
            if (!app || seen.has(id) || !app.get_app_info().should_show())
                continue;
            seen.add(id);
            found.push([rank, History.score(id), app]);
        }
    });
    // Relevance first, then how often the user opens it
    found.sort((a, b) => a[0] - b[0] || b[1] - a[1]);
    for (const [, , app] of found)
        yield appResult(app);
}

function* windows(query) {
    let count = 0;
    for (const window of global.display.list_all_windows()) {
        if (window.skip_taskbar || !window.title || !normalize(window.title).includes(query))
            continue;
        const app = Shell.WindowTracker.get_default().get_window_app(window);
        yield {title: window.title, subtitle: app?.get_name(), kind: 'Window', icon: app?.get_icon() ?? 'window-symbolic',
            run: () => Main.activateWindow(window), alt: () => window.delete(global.get_current_time())};
        if (++count >= MAX_WINDOWS)
            return;
    }
}

// Quick answers

function* calculation(text) {
    const result = calculate(text);
    if (result !== null)
        yield {title: `= ${result}`, kind: 'Copy', icon: 'accessories-calculator-symbolic', run: () => copy(result)};
}

function* conversion(text) {
    const result = convert(text);
    if (result) {
        yield {title: `${result.value} ${result.to}`, subtitle: `${result.from} =`, kind: 'Copy',
            icon: 'accessories-calculator-symbolic', run: () => copy(result.value)};
    }
}

const TIMER = /^(?:timer|zamanlayici|alarm)\s+(\d+(?:[.,]\d+)?)\s*(s|sec|sn|m|min|dk|h|hr|sa)?$/;
const SECONDS = {s: 1, sec: 1, sn: 1, m: 60, min: 60, dk: 60, h: 3600, hr: 3600, sa: 3600};

function* timer(query) {
    const match = TIMER.exec(query);
    if (!match)
        return;
    const unit = match[2] ?? 'm';
    const seconds = Math.round(parseFloat(match[1].replace(',', '.')) * SECONDS[unit]);
    if (seconds < 1 || seconds > 86400)
        return;
    const label = `${match[1]} ${{s: 'sec', sec: 'sec', sn: 'sec', h: 'h', hr: 'h', sa: 'h'}[unit] ?? 'min'}`;
    yield {
        title: `Timer: ${label}`, subtitle: 'A notification when the time is up', kind: 'Timer',
        icon: 'alarm-symbolic',
        run: () => {
            const id = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, seconds, () => {
                timers.delete(id);
                notify('Time is up', `Your ${label} timer finished`);
                global.display.get_sound_player?.().play_from_theme('complete', 'Timer', null);
                return GLib.SOURCE_REMOVE;
            });
            timers.add(id);
            notify('Timer started', label);
        },
    };
}

const URL = /^(https?:\/\/)?([\w-]+\.)+[a-z]{2,}(:\d+)?(\/\S*)?$/i;

// Names that look like addresses but are files
const FILE_TYPES = new Set(['txt', 'md', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'py', 'js', 'ts', 'rs',
    'sh', 'json', 'toml', 'yaml', 'yml', 'xml', 'html', 'css', 'deb', 'iso', 'zip', 'gz', 'xz', 'tar', 'mp3',
    'mp4', 'mkv', 'odt', 'ods', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'conf', 'log', 'nix', 'c', 'h']);

function* address(text) {
    if (!URL.test(text) || /\s/.test(text))
        return;
    const host = text.replace(/^https?:\/\//, '').split(/[/:]/)[0];
    if (!/^https?:\/\//.test(text) && FILE_TYPES.has(host.split('.').pop().toLowerCase()))
        return;
    const uri = /^https?:\/\//.test(text) ? text : `https://${text}`;
    yield {title: text, subtitle: 'Open in the browser', kind: 'Web', icon: 'web-browser-symbolic', run: () => openUri(uri)};
}

// Settings and actions

function* settingsPanels(query) {
    for (const info of Gio.AppInfo.get_all()) {
        if (!/^gnome-.*-panel\.desktop$/.test(info.get_id() ?? ''))
            continue;
        const text = `${info.get_name()} ${info.get_keywords?.().join(' ') ?? ''}`;
        if (normalize(text).includes(query)) {
            yield {title: info.get_name(), kind: 'Setting', icon: info.get_icon(),
                run: () => info.launch([], launchContext())};
        }
    }
}

function toggles() {
    const list = [];
    const shell = new Gio.Settings({schema_id: 'org.mesale.shell'});
    const dark = shell.get_string('theme-mode') === 'dark' ||
        new Gio.Settings({schema_id: 'org.gnome.desktop.interface'}).get_string('color-scheme') === 'prefer-dark';
    list.push([dark ? 'Light style' : 'Dark style', 'dark light style theme mode karanlik aydinlik tema',
        'weather-clear-night-symbolic', () => shell.set_string('theme-mode', dark ? 'light' : 'dark')]);

    const notifications = new Gio.Settings({schema_id: 'org.gnome.desktop.notifications'});
    const quiet = !notifications.get_boolean('show-banners');
    list.push([quiet ? 'Turn off Do Not Disturb' : 'Do Not Disturb', 'do not disturb dnd notifications quiet rahatsiz etme bildirim',
        'notifications-disabled-symbolic', () => notifications.set_boolean('show-banners', quiet)]);

    if (hasSchema('org.gnome.settings-daemon.plugins.color')) {
        const color = new Gio.Settings({schema_id: 'org.gnome.settings-daemon.plugins.color'});
        const on = color.get_boolean('night-light-enabled');
        list.push([on ? 'Turn off Night Light' : 'Night Light', 'night light blue warm gece isigi',
            'night-light-symbolic', () => color.set_boolean('night-light-enabled', !on)]);
    }
    if (GLib.find_program_in_path('nmcli')) {
        list.push(['Wi-Fi on', 'wifi wi-fi wireless on ac kablosuz', 'network-wireless-symbolic', () => spawn(['nmcli', 'radio', 'wifi', 'on'])]);
        list.push(['Wi-Fi off', 'wifi wi-fi wireless off kapat kablosuz', 'network-wireless-offline-symbolic', () => spawn(['nmcli', 'radio', 'wifi', 'off'])]);
    }
    list.push(['Empty Trash', 'empty trash bin cop bosalt', 'user-trash-symbolic', () => spawn(['gio', 'trash', '--empty'])]);
    list.push(['Clear clipboard history', 'clear clipboard history pano temizle', 'edit-clear-all-symbolic', () => Clipboard.clear()]);
    return list;
}

function* systemActions(query) {
    const system = SystemActions.getDefault();
    const actions = [
        ['Lock screen', 'lock screen kilitle', 'system-lock-screen-symbolic', () => system.activateLockScreen()],
        ['Power off', 'power off shut down kapat', 'system-shutdown-symbolic', () => system.activatePowerOff()],
        ['Restart', 'restart reboot yeniden baslat', 'system-reboot-symbolic', () => system.activateRestart()],
        ['Suspend', 'suspend sleep uyku askiya al', 'weather-clear-night-symbolic', () => system.activateSuspend()],
        ['Log out', 'log out sign out oturumu kapat cikis', 'system-log-out-symbolic', () => system.activateLogout()],
        ['Screenshot', 'screenshot ekran goruntusu', 'camera-photo-symbolic', () => Main.screenshotUI.open()],
        ...toggles(),
    ];
    for (const [title, words, icon, run] of actions) {
        if (normalize(`${title} ${words}`).split(/\s+/).some(word => word.startsWith(query)) ||
            normalize(title).includes(query))
            yield {title, kind: 'Action', icon, run};
    }
}

// Mesale features that are not installed yet, from the files mesale-feature reads

function loadFeatures() {
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

function* featureResults(query) {
    if (query.length < 3)
        return;
    if (features === null)
        loadFeatures();
    for (const feature of features) {
        if (feature.group === 'apps' || !normalize(`${feature.name} ${feature.title}`).includes(query) || installed(feature))
            continue;
        yield {title: `Install ${feature.title}`, subtitle: feature.desc, kind: 'Feature', icon: 'software-install-symbolic',
            run: () => install(feature)};
    }
}

// Files

function* files(query) {
    if (query.length < 2)
        return;
    const seen = new Set();
    for (const item of [...Files.recent(query, MAX_FILES), ...Files.search(query, MAX_FILES)]) {
        const uri = item.file.get_uri();
        if (seen.has(uri))
            continue;
        seen.add(uri);
        yield fileResult(item);
        if (seen.size >= MAX_FILES)
            return;
    }
}

function* browse(text) {
    const {folder, items} = Files.browse(text, MAX_RESULTS - 1);
    const base = text.slice(0, text.lastIndexOf('/') + 1);
    if (text.endsWith('/')) {
        yield {title: `Open ${Files.shortPath(folder)}`, kind: 'Folder', icon: 'folder-open',
            run: () => openUri(folder.get_uri())};
    }
    for (const item of items) {
        const result = fileResult(item);
        if (item.folder)
            result.fill = `${base}${item.name}/`;   // Enter goes inside, Ctrl+Enter opens it
        yield result;
    }
}

// Prefix modes

function* command(text) {
    const line = text.trim();
    yield {title: line || 'Type a command', subtitle: 'Run in the terminal', kind: 'Run',
        icon: 'utilities-terminal-symbolic', run: () => line && inTerminal(line)};
}

function* web(text) {
    const words = text.trim();
    yield {title: words ? `Search the web for “${words}”` : 'Type to search the web', kind: 'Web',
        icon: 'web-browser-symbolic', run: () => words && openUri(WEB_SEARCH + encodeURIComponent(words))};
}

function* emoji(query) {
    let count = 0;
    for (const [char, words] of EMOJI) {
        if (query && !words.split(' ').some(word => word.startsWith(query)))
            continue;
        yield {title: `${char}  ${words.split(' ')[0]}`, kind: 'Copy', icon: 'face-smile-symbolic', run: () => copy(char)};
        if (++count >= MAX_RESULTS)
            return;
    }
}

function* clipboard(query) {
    const entries = Clipboard.history();
    if (!entries.length) {
        yield {title: 'Nothing copied yet', subtitle: 'Text you copy appears here until you log out', kind: '',
            icon: 'edit-paste-symbolic', run: () => {}};
        return;
    }
    for (const text of entries) {
        if (query && !normalize(text).includes(query))
            continue;
        const line = text.replace(/\s+/g, ' ').trim();
        yield {title: line.length > 70 ? `${line.slice(0, 70)}…` : line,
            subtitle: text.length > 70 ? `${text.length} characters` : undefined,
            kind: 'Copy', icon: 'edit-paste-symbolic', run: () => copy(text)};
    }
}

function* softwareSearch(text) {
    if (GLib.find_program_in_path('gnome-software')) {
        yield {title: `Search Software for “${text}”`, kind: 'Install', icon: 'software-install-symbolic',
            run: () => spawn(['gnome-software', `--search=${text}`])};
    }
}

// One failing provider must not empty the bar
function* safe(provider, ...args) {
    try {
        yield* provider(...args);
    } catch (e) {
        logError(e, `Mesale command bar: ${provider.name}`);
    }
}

function* allResults(text) {
    const query = normalize(text);
    if (!query) {
        yield* safe(favorites);
        return;
    }
    const rest = text.slice(1);
    switch (text[0]) {
    case '>': yield* safe(command, rest); return;
    case '?': yield* safe(web, rest); return;
    case ':': yield* safe(emoji, normalize(rest.trim())); return;
    case '@': yield* safe(clipboard, normalize(rest.trim())); return;
    case '/': case '~': yield* safe(browse, text); return;
    }
    yield* safe(calculation, text);
    yield* safe(conversion, text);
    yield* safe(timer, query);
    yield* safe(address, text);
    yield* safe(windows, query);
    yield* safe(apps, query);
    yield* safe(systemActions, query);
    yield* safe(settingsPanels, query);
    yield* safe(featureResults, query);
    yield* safe(files, query);
    yield* safe(web, text);
    yield* safe(softwareSearch, text);
}

export function search(text) {
    const results = [];
    for (const result of allResults(text.trimStart())) {
        results.push(result);
        if (results.length >= MAX_RESULTS)
            break;
    }
    return results;
}

export function start() {
    History.load();
    Clipboard.start();
}

// Called when the bar opens: refresh what may have changed
export function prepare(onUpdate) {
    features = null;
    Files.refresh(onUpdate);
}

export function stop() {
    for (const id of timers)
        GLib.source_remove(id);
    timers.clear();
    Clipboard.stop();
    Files.stop();
    features = null;
}
