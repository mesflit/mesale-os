// Clipboard history for the command bar ("@" prefix). Kept in memory only and cleared
// when the extension stops, so nothing copied ever reaches the disk. Copies a password
// manager marks as secret are skipped.
import Meta from 'gi://Meta';
import St from 'gi://St';

const MAX_ENTRIES = 30;
const MAX_LENGTH = 4000;
const TEXT = ['text/plain;charset=utf-8', 'text/plain', 'UTF8_STRING', 'STRING', 'TEXT'];
const SECRET = ['x-kde-passwordManagerHint'];

let entries = [];
let selection = null;
let handler = 0;

function add(text) {
    if (!text || !text.trim() || text.length > MAX_LENGTH)
        return;
    entries = [text, ...entries.filter(entry => entry !== text)].slice(0, MAX_ENTRIES);
}

export function start() {
    if (handler)
        return;   // already watching
    selection = global.display.get_selection();
    handler = selection.connect('owner-changed', (_selection, type, source) => {
        if (type !== Meta.SelectionType.SELECTION_CLIPBOARD || !source)
            return;
        const mimes = source.get_mimetypes();
        if (mimes.some(m => SECRET.includes(m)) || !mimes.some(m => TEXT.includes(m)))
            return;
        St.Clipboard.get_default().get_text(St.ClipboardType.CLIPBOARD, (_clipboard, text) => add(text));
    });
}

export function stop() {
    if (selection && handler)
        selection.disconnect(handler);
    selection = null;
    handler = 0;
    entries = [];
}

export const history = () => entries;

export function clear() {
    entries = [];
}
