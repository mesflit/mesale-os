// Prefix modes: > run a command, ? search the web, : emoji, @ clipboard history.
import GLib from 'gi://GLib';
import * as Clipboard from '../clipboard.js';
import {EMOJI} from '../emoji.js';
import {MAX_RESULTS, copy, inTerminal, normalize, openUri, spawn} from './util.js';

const WEB_SEARCH = 'https://duckduckgo.com/?q=';

export function* command(text) {
    const line = text.trim();
    yield {title: line || 'Type a command', subtitle: 'Run in the terminal', kind: 'Run',
        icon: 'utilities-terminal-symbolic', run: () => line && inTerminal(line)};
}

export function* web(text) {
    const words = text.trim();
    yield {title: words ? `Search the web for “${words}”` : 'Type to search the web', kind: 'Web',
        icon: 'web-browser-symbolic', run: () => words && openUri(WEB_SEARCH + encodeURIComponent(words))};
}

export function* emoji(query) {
    let count = 0;
    for (const [char, words] of EMOJI) {
        if (query && !words.split(' ').some(word => word.startsWith(query)))
            continue;
        yield {title: `${char}  ${words.split(' ')[0]}`, kind: 'Copy', icon: 'face-smile-symbolic', run: () => copy(char)};
        if (++count >= MAX_RESULTS)
            return;
    }
}

export function* clipboard(query) {
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

export function* softwareSearch(text) {
    if (GLib.find_program_in_path('gnome-software')) {
        yield {title: `Search Software for “${text}”`, kind: 'Install', icon: 'software-install-symbolic',
            run: () => spawn(['gnome-software', `--search=${text}`])};
    }
}
