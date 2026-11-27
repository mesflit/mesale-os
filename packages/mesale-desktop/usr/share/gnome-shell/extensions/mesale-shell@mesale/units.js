// Unit conversion for the command bar: "10 km to mi", "100 f in c", "2 GiB MB".
const DIMENSIONS = {
    length: {mm: .001, cm: .01, dm: .1, m: 1, km: 1000, in: .0254, inch: .0254, inches: .0254, ft: .3048,
        foot: .3048, feet: .3048, yd: .9144, yard: .9144, yards: .9144, mi: 1609.344, mile: 1609.344,
        miles: 1609.344, nmi: 1852},
    mass: {mg: 1e-6, g: .001, kg: 1, t: 1000, ton: 1000, tonne: 1000, oz: .028349523125, lb: .45359237,
        lbs: .45359237, st: 6.35029318},
    volume: {ml: .001, cl: .01, dl: .1, l: 1, gal: 3.785411784, qt: .946352946, pt: .473176473,
        cup: .2365882365, cups: .2365882365, floz: .0295735295625, tbsp: .01478676478125, tsp: .00492892159375},
    data: {B: 1, kB: 1e3, KB: 1e3, MB: 1e6, GB: 1e9, TB: 1e12, KiB: 1024, MiB: 1024 ** 2, GiB: 1024 ** 3,
        TiB: 1024 ** 4, bit: .125, bits: .125, kbit: 125, Mbit: 125e3, Gbit: 125e6},
    time: {ms: .001, s: 1, sec: 1, min: 60, h: 3600, hr: 3600, hour: 3600, hours: 3600, d: 86400, day: 86400,
        days: 86400, week: 604800, weeks: 604800, wk: 604800, year: 31557600, years: 31557600, yr: 31557600},
    speed: {'m/s': 1, 'km/h': 1 / 3.6, kmh: 1 / 3.6, kph: 1 / 3.6, mph: .44704, kn: 1852 / 3600, knot: 1852 / 3600,
        knots: 1852 / 3600},
    area: {mm2: 1e-6, cm2: 1e-4, m2: 1, km2: 1e6, ha: 1e4, acre: 4046.8564224, acres: 4046.8564224,
        ft2: .09290304, in2: .00064516, mi2: 2589988.110336},
};
const TEMPERATURE = {
    c: [v => v, v => v], f: [v => (v - 32) * 5 / 9, v => v * 9 / 5 + 32], k: [v => v - 273.15, v => v + 273.15],
};

const UNIT = '[a-zA-Z°][a-zA-Z°/²0-9]*';
const PATTERN = new RegExp(`^(-?\\d+(?:[.,]\\d+)?)\\s*(${UNIT})\\s+(?:to\\s+|in\\s+|=\\s*|->\\s*)?(${UNIT})$`);

// Exact match first, so MB and Mbit or B and b stay apart; then case-insensitive.
function find(unit) {
    unit = unit.replace('²', '2');
    for (const [dimension, units] of Object.entries(DIMENSIONS)) {
        if (unit in units)
            return [dimension, units[unit], unit];
    }
    const lower = unit.toLowerCase();
    for (const [dimension, units] of Object.entries(DIMENSIONS)) {
        const key = Object.keys(units).find(u => u.toLowerCase() === lower);
        if (key)
            return [dimension, units[key], key];
    }
    const temperature = lower.replace(/^°/, '');
    if (temperature in TEMPERATURE)
        return ['temperature', TEMPERATURE[temperature], temperature.toUpperCase()];
    return null;
}

const format = value => String(+value.toPrecision(10));

// Returns {value, from, to} or null.
export function convert(text) {
    const match = PATTERN.exec(text.trim());
    if (!match)
        return null;
    const amount = parseFloat(match[1].replace(',', '.'));
    const from = find(match[2]), to = find(match[3]);
    if (!from || !to || from[0] !== to[0])
        return null;
    const value = from[0] === 'temperature' ? to[1][1](from[1][0](amount)) : amount * from[1] / to[1];
    const label = u => (from[0] === 'temperature' && u !== 'K' ? `°${u}` : u);
    return {value: format(value), from: `${format(amount)} ${label(from[2])}`, to: label(to[2])};
}
