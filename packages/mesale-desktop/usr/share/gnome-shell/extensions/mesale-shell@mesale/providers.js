// Search results for the command bar. A result is {title, kind, icon, run}.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Shell from 'gi://Shell';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as SystemActions from 'resource:///org/gnome/shell/misc/systemActions.js';
import {calculate} from './calculator.js';

const MAX_RESULTS = 7;
const MAX_WINDOWS = 3;

// Lower case without accents
const normalize = text => text.toLowerCase().normalize('NFD').replace(/\p{M}/gu, '').replace(/\u0131/g, 'i');

const appResult = app => ({title: app.get_name(), kind: 'App', icon: app.get_icon(), run: () => app.activate()});

function* calculation(text) {
    const result = calculate(text);
    if (result !== null) {
        yield {title: `= ${result}`, kind: 'Copy', icon: 'accessories-calculator-symbolic',
            run: () => St.Clipboard.get_default().set_text(St.ClipboardType.CLIPBOARD, result)};
    }
}

function* favorites() {
    for (const id of global.settings.get_strv('favorite-apps')) {
        const app = Shell.AppSystem.get_default().lookup_app(id);
        if (app)
            yield appResult(app);
    }
}

function* windows(query) {
    let count = 0;
    for (const window of global.display.list_all_windows()) {
        if (window.skip_taskbar || !window.title || !normalize(window.title).includes(query))
            continue;
        const app = Shell.WindowTracker.get_default().get_window_app(window);
        yield {title: window.title, kind: 'Window', icon: app?.get_icon() ?? 'window-symbolic',
            run: () => Main.activateWindow(window)};
        if (++count >= MAX_WINDOWS)
            return;
    }
}

function* apps(query) {
    const seen = new Set();
    for (const id of Shell.AppSystem.search(query).flat()) {
        const app = Shell.AppSystem.get_default().lookup_app(id);
        if (!app || seen.has(id) || !app.get_app_info().should_show())
            continue;
        seen.add(id);
        yield appResult(app);
    }
}

function* settingsPanels(query) {
    for (const info of Gio.AppInfo.get_all()) {
        if (!/^gnome-.*-panel\.desktop$/.test(info.get_id() ?? ''))
            continue;
        const text = `${info.get_name()} ${info.get_keywords?.().join(' ') ?? ''}`;
        if (normalize(text).includes(query)) {
            yield {title: info.get_name(), kind: 'Setting', icon: info.get_icon(),
                run: () => info.launch([], global.create_app_launch_context(0, -1))};
        }
    }
}

function* systemActions(query) {
    const system = SystemActions.getDefault();
    const actions = [
        ['Lock screen', 'system-lock-screen-symbolic', () => system.activateLockScreen()],
        ['Power off', 'system-shutdown-symbolic', () => system.activatePowerOff()],
        ['Restart', 'system-reboot-symbolic', () => system.activateRestart()],
        ['Suspend', 'weather-clear-night-symbolic', () => system.activateSuspend()],
        ['Log out', 'system-log-out-symbolic', () => system.activateLogout()],
        ['Screenshot', 'camera-photo-symbolic', () => Main.screenshotUI.open()],
    ];
    for (const [title, icon, run] of actions) {
        if (normalize(title).includes(query))
            yield {title, kind: 'Action', icon, run};
    }
}

function* softwareSearch(text) {
    if (GLib.find_program_in_path('gnome-software')) {
        yield {title: `Search Software for \u201c${text}\u201d`, kind: 'Install', icon: 'software-install-symbolic',
            run: () => GLib.spawn_async(null, ['gnome-software', `--search=${text}`], null, GLib.SpawnFlags.SEARCH_PATH, null)};
    }
}

function* allResults(text) {
    const query = normalize(text);
    if (!query) {
        yield* favorites();
        return;
    }
    yield* calculation(text);
    yield* windows(query);
    yield* apps(query);
    yield* settingsPanels(query);
    yield* systemActions(query);
    yield* softwareSearch(text);
}

export function search(text) {
    const results = [];
    for (const result of allResults(text.trim())) {
        results.push(result);
        if (results.length >= MAX_RESULTS)
            break;
    }
    return results;
}
