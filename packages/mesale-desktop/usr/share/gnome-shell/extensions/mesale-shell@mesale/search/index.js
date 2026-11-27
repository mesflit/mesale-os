// Search results for the command bar, gathered from the modules in this folder.
// A result is {title, subtitle?, kind, icon, run, alt?, fill?}:
//   run   what Enter does        alt   what Ctrl+Enter does (optional)
//   fill  text to put in the entry instead of running (folders while browsing)
//
// Prefixes:  > run a command   ? search the web   : emoji   @ clipboard   / or ~ browse files
import * as Clipboard from '../clipboard.js';
import * as FileIndex from '../fileIndex.js';
import * as History from '../history.js';
import {systemActions, settingsPanels} from './actions.js';
import {address, calculation, conversion, stopTimers, timer} from './answers.js';
import {apps, favorites, windows} from './apps.js';
import {featureResults, forgetFeatures} from './features.js';
import {browse, files} from './files.js';
import {clipboard, command, emoji, softwareSearch, web} from './prefixes.js';
import {MAX_RESULTS, normalize, setting, useSettings} from './util.js';

// One failing provider must not empty the bar
function* safe(provider, ...args) {
    try {
        yield* provider(...args);
    } catch (e) {
        logError(e, `Mesale command bar: ${provider.name}`);
    }
}

// The order here is the order of the results
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
    if (setting('search-files', true))
        yield* safe(files, query);
    if (setting('search-web', true))
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

let settingsHandler = 0;

export function start(settings) {
    useSettings(settings);
    History.load();
    // Clipboard history only runs while it is wanted; turning it off forgets what it kept
    const follow = () => (settings.get_boolean('clipboard-history') ? Clipboard.start() : Clipboard.stop());
    settingsHandler = settings.connect('changed::clipboard-history', follow);
    follow();
}

// Called when the bar opens: refresh what may have changed
export function prepare(onUpdate) {
    forgetFeatures();
    FileIndex.refresh(onUpdate);
}

export function stop(settings) {
    if (settingsHandler)
        settings.disconnect(settingsHandler);
    settingsHandler = 0;
    useSettings(null);
    stopTimers();
    Clipboard.stop();
    FileIndex.stop();
    forgetFeatures();
}
