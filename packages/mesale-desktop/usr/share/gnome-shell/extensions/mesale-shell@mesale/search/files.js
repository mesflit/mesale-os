// File results: recent files and the folder index (../fileIndex.js), and browsing a typed path.
import * as FileIndex from '../fileIndex.js';
import {MAX_RESULTS, openUri} from './util.js';

const MAX_FILES = 4;

function fileResult(item) {
    const openFolder = () => openUri((item.folder ? item.file : item.file.get_parent()).get_uri());
    return {
        title: item.name, subtitle: FileIndex.shortPath(item.file.get_parent() ?? item.file),
        kind: item.folder ? 'Folder' : 'File', icon: item.icon,
        run: () => openUri(item.file.get_uri()), alt: openFolder,
    };
}

export function* files(query) {
    if (query.length < 2)
        return;
    const seen = new Set();
    for (const item of [...FileIndex.recent(query, MAX_FILES), ...FileIndex.search(query, MAX_FILES)]) {
        const uri = item.file.get_uri();
        if (seen.has(uri))
            continue;
        seen.add(uri);
        yield fileResult(item);
        if (seen.size >= MAX_FILES)
            return;
    }
}

export function* browse(text) {
    const {folder, items} = FileIndex.browse(text, MAX_RESULTS - 1);
    const base = text.slice(0, text.lastIndexOf('/') + 1);
    if (text.endsWith('/')) {
        yield {title: `Open ${FileIndex.shortPath(folder)}`, kind: 'Folder', icon: 'folder-open',
            run: () => openUri(folder.get_uri())};
    }
    for (const item of items) {
        const result = fileResult(item);
        if (item.folder)
            result.fill = `${base}${item.name}/`;   // Enter goes inside, Ctrl+Enter opens it
        yield result;
    }
}
