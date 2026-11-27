// Quick answers: arithmetic, unit conversion, timers, web addresses.
import GLib from 'gi://GLib';
import {calculate} from '../calculator.js';
import {parseAddress, parseTimer} from '../parse.js';
import {convert} from '../units.js';
import {copy, notify, openUri} from './util.js';

const timers = new Set();

export function* calculation(text) {
    const result = calculate(text);
    if (result !== null)
        yield {title: `= ${result}`, kind: 'Copy', icon: 'accessories-calculator-symbolic', run: () => copy(result)};
}

export function* conversion(text) {
    const result = convert(text);
    if (result) {
        yield {title: `${result.value} ${result.to}`, subtitle: `${result.from} =`, kind: 'Copy',
            icon: 'accessories-calculator-symbolic', run: () => copy(result.value)};
    }
}

export function* timer(query) {
    const parsed = parseTimer(query);
    if (!parsed)
        return;
    const {seconds, label} = parsed;
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

export function stopTimers() {
    for (const id of timers)
        GLib.source_remove(id);
    timers.clear();
}

export function* address(text) {
    const uri = parseAddress(text);
    if (uri)
        yield {title: text, subtitle: 'Open in the browser', kind: 'Web', icon: 'web-browser-symbolic', run: () => openUri(uri)};
}
