import {calculate} from './calculator.js';

const REPO = 'mesflit/mesaleos';
const $ = id => document.getElementById(id);

// Command bar demo: the same calculator and feature list the OS uses
const catalog = JSON.parse($('search-data').textContent);
const apps = [['Settings', 'App'], ['Mesale Center', 'App'], ['Terminal', 'App']];

function search(text) {
    const query = text.trim().toLowerCase();
    if (!query)
        return apps;
    const result = calculate(text);
    const found = catalog.filter(([name, about]) => `${name} ${about}`.toLowerCase().includes(query));
    return [...result === null ? [] : [[`= ${result}`, 'Copy']], ...found.map(([name]) => [name, 'Feature'])].slice(0, 3);
}

function showResults() {
    const rows = search($('command').value).map(([title, kind]) => {
        const row = document.createElement('li');
        const label = document.createElement('span');
        const tag = document.createElement('small');
        label.textContent = title;
        tag.textContent = kind;
        row.append(label, tag);
        return row;
    });
    $('results').replaceChildren(...rows);
}

$('command').addEventListener('input', showResults);
for (const button of document.querySelectorAll('.try')) {
    button.addEventListener('click', () => {
        $('command').value = button.textContent;
        showResults();
    });
}
showResults();

// Looks
const hero = document.querySelector('.hero');
const looks = document.querySelectorAll('.look');
for (const look of looks) {
    look.addEventListener('click', () => {
        hero.style.setProperty('--hero', `url("img/${look.dataset.look}.webp")`);
        document.body.toggleAttribute('data-dark', look.dataset.dark === 'true');
        looks.forEach(other => other.setAttribute('aria-pressed', String(other === look)));
        hero.scrollIntoView();
    });
}

// Feature picker
function showCommand() {
    const boxes = [...$('picker').querySelectorAll('input')];
    const add = boxes.filter(b => b.checked && !b.defaultChecked).map(b => b.value);
    const remove = boxes.filter(b => !b.checked && b.defaultChecked).map(b => b.value);
    const parts = [];
    if (add.length)
        parts.push(`mesale-feature add ${add.join(' ')}`);
    if (remove.length)
        parts.push(`mesale-feature remove ${remove.join(' ')}`);
    $('line').textContent = parts.join(' && ') || 'Select features to get the command';
    $('copy').disabled = !parts.length;
}

$('picker').addEventListener('change', showCommand);
$('copy').addEventListener('click', async () => {
    try {
        await navigator.clipboard.writeText($('line').textContent);
        $('copy').textContent = 'Copied';
    } catch {
        getSelection().selectAllChildren($('line'));
        $('copy').textContent = 'Press Ctrl+C';
    }
    setTimeout(() => ($('copy').textContent = 'Copy command'), 1800);
});
showCommand();

// Latest build: real download link and versions
try {
    const reply = await fetch(`https://api.github.com/repos/${REPO}/releases/tags/dev`);
    if (reply.ok) {
        const release = await reply.json();
        const iso = release.assets.find(asset => asset.name.endsWith('.iso'));
        if (iso) {
            $('download').href = iso.browser_download_url;
            const date = new Date(release.published_at).toLocaleDateString('en', {dateStyle: 'medium'});
            $('release').append(` ${(iso.size / 1e9).toFixed(1)} GB, built ${date}.`);
        }
        for (const slot of document.querySelectorAll('[data-version]')) {
            const match = release.body.match(new RegExp(`^${slot.dataset.version} (\\S+)`, 'm'));
            if (match)
                slot.textContent = match[1];
        }
    }
} catch {
    // Offline or rate limited: the releases link still works
}
