// Settings panels, quick toggles and system actions. Actions also match Turkish words.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as SystemActions from 'resource:///org/gnome/shell/misc/systemActions.js';
import * as Clipboard from '../clipboard.js';
import {hasSchema, launchContext, normalize, spawn} from './util.js';

export function* settingsPanels(query) {
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

// [title, words to find it by, icon, run], read fresh so each title shows the current state
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

export function* systemActions(query) {
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
