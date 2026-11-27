// Sunrise and sunset without asking for the location: the time zone's own place
// (from the system's zone1970.tab) is close enough to switch the theme. No GNOME
// imports, so tests run it in plain Node.

const RAD = Math.PI / 180;

// "+4101+02858" or "+404251-0740023" (ISO 6709) -> [latitude, longitude] in degrees
export function parseCoordinates(text) {
    const match = /^([+-])(\d{2})(\d{2})(\d{2})?([+-])(\d{3})(\d{2})(\d{2})?$/.exec(text);
    if (!match)
        return null;
    const part = (sign, d, m, s) => (sign === '-' ? -1 : 1) * (+d + +m / 60 + +(s ?? 0) / 3600);
    return [part(match[1], match[2], match[3], match[4]), part(match[5], match[6], match[7], match[8])];
}

// The coordinates of a zone such as "Europe/Istanbul" in the text of zone1970.tab
export function zoneCoordinates(table, zone) {
    for (const line of table.split('\n')) {
        if (line.startsWith('#'))
            continue;
        const [, coordinates, name] = line.split('\t');
        if (name === zone)
            return parseCoordinates(coordinates);
    }
    return null;
}

// Sunrise and sunset in UTC hours for a day, from NOAA's simplified equations.
// null when the sun does not rise or does not set (polar day or night).
export function sunTimesUtc(date, latitude, longitude) {
    const start = Date.UTC(date.getUTCFullYear(), 0, 1);
    const day = Math.floor((Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()) - start) / 86400000);
    const angle = 2 * Math.PI / 365 * day;
    const equation = 229.18 * (0.000075 + 0.001868 * Math.cos(angle) - 0.032077 * Math.sin(angle) -
        0.014615 * Math.cos(2 * angle) - 0.040849 * Math.sin(2 * angle));
    const declination = 0.006918 - 0.399912 * Math.cos(angle) + 0.070257 * Math.sin(angle) -
        0.006758 * Math.cos(2 * angle) + 0.000907 * Math.sin(2 * angle) -
        0.002697 * Math.cos(3 * angle) + 0.00148 * Math.sin(3 * angle);
    const cosHour = Math.cos(90.833 * RAD) / (Math.cos(latitude * RAD) * Math.cos(declination)) -
        Math.tan(latitude * RAD) * Math.tan(declination);
    if (cosHour < -1 || cosHour > 1)
        return null;
    const hourAngle = Math.acos(cosHour) / RAD;
    const noon = 720 - 4 * longitude - equation;   // minutes after UTC midnight
    return {sunrise: (noon - 4 * hourAngle) / 60, sunset: (noon + 4 * hourAngle) / 60};
}

// Is it between sunrise and sunset at this moment? Polar day counts as day.
export function isDaytime(now, latitude, longitude) {
    const times = sunTimesUtc(now, latitude, longitude);
    if (!times) {
        // Sun above the horizon all day in local summer
        const summer = (now.getUTCMonth() >= 3 && now.getUTCMonth() <= 8) === latitude > 0;
        return summer;
    }
    const hour = now.getUTCHours() + now.getUTCMinutes() / 60;
    const inRange = (h, a, b) => (a <= b ? h >= a && h < b : h >= a || h < b);
    const wrap = h => ((h % 24) + 24) % 24;
    return inRange(hour, wrap(times.sunrise), wrap(times.sunset));
}
