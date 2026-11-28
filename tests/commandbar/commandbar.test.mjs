// Command bar tests. Run: node --test tests/commandbar/*.test.mjs
import assert from 'node:assert/strict';
import {register} from 'node:module';
import {test} from 'node:test';

register('./stubs.mjs', import.meta.url);
globalThis.global = new Proxy({}, {get: () => () => null});
globalThis.logError = () => {};

const EXTENSION = '../../packages/mesale-desktop/usr/share/gnome-shell/extensions/mesale-shell@mesale';
const load = name => import(`${EXTENSION}/${name}`);

test('every module loads and finds what it imports', async () => {
    for (const name of ['extension.js', 'commandBar.js', 'search/index.js', 'theme.js'])
        await load(name);
});

test('arithmetic', async () => {
    const {calculate} = await load('calculator.js');
    assert.equal(calculate('2+2*3'), '8');
    assert.equal(calculate('(1+2)^2'), '9');
    assert.equal(calculate('10 / 4'), '2.5');
    assert.equal(calculate('1,5*2'), '3');
    assert.equal(calculate('42'), null);         // a number alone is not a sum
    assert.equal(calculate('10 km'), null);
    assert.equal(calculate('1/0'), null);
});

test('unit conversion', async () => {
    const {convert} = await load('units.js');
    assert.deepEqual(convert('10 km to mi'), {value: '6.213711922', from: '10 km', to: 'mi'});
    assert.equal(convert('100 f to c').value, '37.77777778');
    assert.equal(convert('0 c k').to, 'K');
    assert.equal(convert('2 GiB to MB').value, '2147.483648');
    assert.equal(convert('1 MB to Mbit').value, '8');
    assert.equal(convert('3,5 l to cup').from, '3.5 l');
    assert.equal(convert('10 m² to ft2').value, '107.6391042');
    assert.equal(convert('10 km to kg'), null);   // different dimensions
    assert.equal(convert('5 apples to mi'), null);
});

test('timers', async () => {
    const {parseTimer, normalize} = await load('parse.js');
    assert.deepEqual(parseTimer('timer 5m'), {seconds: 300, label: '5 min'});
    assert.deepEqual(parseTimer('timer 90'), {seconds: 5400, label: '90 min'});
    assert.deepEqual(parseTimer('timer 1,5 h'), {seconds: 5400, label: '1,5 h'});
    assert.deepEqual(parseTimer(normalize('Zamanlayıcı 10 dk')), {seconds: 600, label: '10 min'});
    assert.equal(parseTimer('timer'), null);
    assert.equal(parseTimer('timer 0'), null);
    assert.equal(parseTimer('timer 30 h'), null);  // more than a day
});

test('addresses', async () => {
    const {parseAddress} = await load('parse.js');
    assert.equal(parseAddress('github.com'), 'https://github.com');
    assert.equal(parseAddress('mesflit.github.io/mesaleos'), 'https://mesflit.github.io/mesaleos');
    assert.equal(parseAddress('http://localhost.test:8080/x'), 'http://localhost.test:8080/x');
    assert.equal(parseAddress('notes.txt'), null);   // a file, not a site
    assert.equal(parseAddress('report.pdf'), null);
    assert.equal(parseAddress('10.5'), null);
    assert.equal(parseAddress('hello world.com'), null);
});

test('Turkish text matches without accents', async () => {
    const {normalize} = await load('parse.js');
    assert.equal(normalize('Çöp Kutusu'), 'cop kutusu');
    assert.equal(normalize('KARANLIK'), 'karanlik');
    assert.equal(normalize('Işık'), 'isik');
});

test('emoji list', async () => {
    const {EMOJI} = await load('emoji.js');
    assert.equal(new Set(EMOJI.map(([char]) => char)).size, EMOJI.length, 'no emoji twice');
    for (const [char, words] of EMOJI)
        assert.match(words, /^[a-z0-9 -]+$/, `${char}: words must be plain lower case to match normalized queries`);
});

test('sunrise and sunset from the time zone', async () => {
    const {isDaytime, parseCoordinates, sunTimesUtc, zoneCoordinates} = await load('sun.js');
    const close = (actual, expected, label) =>
        assert.ok(Math.abs(actual - expected) < 0.1, `${label}: ${actual.toFixed(2)} not near ${expected}`);

    const [lat, lon] = zoneCoordinates('#comment\nTR\t+4101+02858\tEurope/Istanbul\n', 'Europe/Istanbul');
    close(lat, 41.0167, 'latitude');
    close(lon, 28.9667, 'longitude');
    assert.deepEqual(parseCoordinates('+404251-0740023').map(v => +v.toFixed(3)), [40.714, -74.006]);
    assert.equal(parseCoordinates('nonsense'), null);

    // Istanbul, UTC+3 all year: 05:32-20:39 in June, 08:26-17:39 in December
    const june = sunTimesUtc(new Date(Date.UTC(2026, 5, 21)), lat, lon);
    close(june.sunrise, 2.53, 'June sunrise');
    close(june.sunset, 17.65, 'June sunset');
    const december = sunTimesUtc(new Date(Date.UTC(2026, 11, 21)), lat, lon);
    close(december.sunrise, 5.43, 'December sunrise');
    close(december.sunset, 14.65, 'December sunset');

    assert.equal(isDaytime(new Date(Date.UTC(2026, 11, 21, 12)), lat, lon), true);    // 15:00 local
    assert.equal(isDaytime(new Date(Date.UTC(2026, 11, 21, 15)), lat, lon), false);   // 18:00 local
    // Midnight sun in Tromsø in June, polar night in December
    assert.equal(isDaytime(new Date(Date.UTC(2026, 5, 21, 23)), 69.65, 18.96), true);
    assert.equal(isDaytime(new Date(Date.UTC(2026, 11, 21, 11)), 69.65, 18.96), false);
});

test('one-time settings steps run once', async () => {
    const {run} = await load('migrate.js');
    const store = {steps: 0, writes: 0};
    const settings = {
        get_int: () => store.steps,
        set_int: (_key, value) => {
            store.steps = value;
            store.writes++;
        },
    };
    run(settings);
    assert.ok(store.steps >= 1, 'steps recorded');
    const after = store.writes;
    run(settings);
    assert.equal(store.writes, after, 'nothing runs or is written the second time');
});
