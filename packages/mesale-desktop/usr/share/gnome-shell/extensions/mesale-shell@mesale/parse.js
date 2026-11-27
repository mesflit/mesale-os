// Text parsing for the command bar. No GNOME imports, so tests run it in plain Node.

// Lower case without accents, dotless i as i: "Çöp" and "cop" match
export const normalize = text => text.toLowerCase().normalize('NFD').replace(/\p{M}/gu, '').replace(/ı/g, 'i');

const TIMER = /^(?:timer|zamanlayici|alarm)\s+(\d+(?:[.,]\d+)?)\s*(s|sec|sn|m|min|dk|h|hr|sa)?$/;
const SECONDS = {s: 1, sec: 1, sn: 1, m: 60, min: 60, dk: 60, h: 3600, hr: 3600, sa: 3600};
const UNIT_LABEL = {s: 'sec', sec: 'sec', sn: 'sec', h: 'h', hr: 'h', sa: 'h'};

// "timer 5m", "zamanlayici 10 dk" (normalized) -> {seconds, label}; minutes when no unit
export function parseTimer(query) {
    const match = TIMER.exec(query);
    if (!match)
        return null;
    const unit = match[2] ?? 'm';
    const seconds = Math.round(parseFloat(match[1].replace(',', '.')) * SECONDS[unit]);
    if (seconds < 1 || seconds > 86400)
        return null;
    return {seconds, label: `${match[1]} ${UNIT_LABEL[unit] ?? 'min'}`};
}

const URL = /^(https?:\/\/)?([\w-]+\.)+[a-z]{2,}(:\d+)?(\/\S*)?$/i;
// Names that look like addresses but are files
const FILE_TYPES = new Set(['txt', 'md', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'py', 'js', 'ts', 'rs',
    'sh', 'json', 'toml', 'yaml', 'yml', 'xml', 'html', 'css', 'deb', 'iso', 'zip', 'gz', 'xz', 'tar', 'mp3',
    'mp4', 'mkv', 'odt', 'ods', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'conf', 'log', 'nix', 'c', 'h']);

// "github.com" -> "https://github.com"; null for anything that is not an address
export function parseAddress(text) {
    if (!URL.test(text) || /\s/.test(text))
        return null;
    const scheme = /^https?:\/\//.test(text);
    const host = text.replace(/^https?:\/\//, '').split(/[/:]/)[0];
    if (!scheme && FILE_TYPES.has(host.split('.').pop().toLowerCase()))
        return null;
    return scheme ? text : `https://${text}`;
}
