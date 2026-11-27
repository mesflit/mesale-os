// Prefix modes: > run a command, ? search the web, : emoji, @ clipboard history.
import GLib from 'gi://GLib';
import * as Clipboard from '../clipboard.js';
import {EMOJI} from '../emoji.js';
import {MAX_RESULTS, copy, inTerminal, normalize, openUri, setting, spawn} from './util.js';

const ENGINES = {
    duckduckgo: ['DuckDuckGo', 'https://duckduckgo.com/?q='],
    google: ['Google', 'https://www.google.com/search?q='],
    startpage: ['Startpage', 'https://www.startpage.com/do/search?q='],
    brave: ['Brave Search', 'https://search.brave.com/search?q='],
    ecosia: ['Ecosia', 'https://www.ecosia.org/search?q='],
};

export function* command(text) {
    const line = text.trim();
    yield {title: line || 'Type a command', subtitle: 'Run in the terminal', kind: 'Run',
        icon: 'utilities-terminal-symbolic', run: () => line && inTerminal(line)};
}

export function* web(text) {
    const words = text.trim();
    const [name, url] = ENGINES[setting('search-engine', 'duckduckgo')] ?? ENGINES.duckduckgo;
    yield {title: words ? `Search ${name} for “${words}”` : `Type to search ${name}`, kind: 'Web',
        icon: 'web-browser-symbolic', run: () => words && openUri(url + encodeURIComponent(words))};
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
    if (!setting('clipboard-history', true)) {
        yield {title: 'Clipboard history is off', subtitle: 'Turn it on in Mesale Center, Desktop', kind: '',
            icon: 'edit-paste-symbolic', run: () => {}};
        return;
    }
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
