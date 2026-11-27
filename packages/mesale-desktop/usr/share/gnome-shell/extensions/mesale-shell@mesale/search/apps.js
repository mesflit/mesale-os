// Apps and open windows. Apps the user opens often rank higher (../history.js).
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as History from '../history.js';
import {MAX_RESULTS, normalize} from './util.js';

const MAX_WINDOWS = 3;

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

// Empty entry: pinned apps, then the most used ones
export function* favorites() {
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

export function* apps(query) {
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

export function* windows(query) {
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
