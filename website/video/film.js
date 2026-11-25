// The film is a pure function of time: seek(t) draws the frame at t seconds.
const DURATION = 28;
const $ = id => document.getElementById(id);
const clamp = v => Math.max(0, Math.min(1, v));
const ease = v => 1 - (1 - clamp(v)) ** 3;
const ramp = (t, a, b) => ease((t - a) / (b - a));
// 0 before start, 1 while shown, 0 after end
const shown = (t, start, end, fade = .6) => Math.min(ramp(t, start, start + fade), 1 - ramp(t, end - fade, end));

function place(id, opacity, transform = '') {
    const style = $(id).style;
    style.opacity = opacity;
    style.transform = transform;
    style.visibility = opacity > .001 ? 'visible' : 'hidden';
}

// Sky: [look, time it has fully appeared]. Later skies cover earlier ones.
const SKIES = [['night', 0], ['dawn', 5.2], ['day', 7.4], ['dawn', 22.2], ['mist', 23.1], ['dusk', 24], ['night', 25]];

function sky(t) {
    for (const look of ['night', 'dusk', 'dawn', 'mist', 'day'])
        place(`sky-${look}`, 0);
    SKIES.forEach(([look, at], i) => {
        const alpha = i === 0 ? 1 : ramp(t, at - .8, at);
        if (alpha <= 0)
            return;
        const element = $(`sky-${look}`);
        element.style.zIndex = i;
        place(`sky-${look}`, alpha, `scale(${1.04 + t * .003}) translateX(${Math.sin(t * .15) * 14}px)`);
    });
}

const COMMANDS = [[14.2, '12*4', [['= 48', 'Copy']]], [16.4, 'steam', [['Steam', 'Feature'], ['Search Software', 'Install']]]];

function command(t) {
    place('veil', shown(t, 13.4, 18.4));
    const rise = (1 - ramp(t, 13.6, 14.2)) * 50;
    place('command', shown(t, 13.6, 18.2), `translateY(${rise}px)`);
    const current = COMMANDS.filter(([start]) => t >= start).pop();
    const typed = current ? current[1].slice(0, Math.floor((t - current[0]) * 9)) : '';
    $('entry').textContent = typed + (Math.floor(t * 2.4) % 2 ? '' : '|');
    const rows = current && typed === current[1] ? current[2] : [['Settings', 'App'], ['Mesale Center', 'App']];
    $('rows').innerHTML = rows.map(([title, kind]) => `<li>${title}<small>${kind}</small></li>`).join('');
}

const items = FEATURES.map(name => {
    const item = document.createElement('div');
    item.innerHTML = `<i>✓</i>${name}`;
    $('features').append(item);
    return item;
});

function features(t) {
    place('features', shown(t, 18.2, 21.8));
    items.forEach((item, i) => {
        item.style.transform = `translateY(${(1 - ramp(t, 18.2 + i * .03, 18.9 + i * .03)) * 40}px)`;
        item.classList.toggle('on', i % 3 !== 1 && t > 18.9 + i * .04);
    });
}

const CAPTIONS = [[9.2, 13.2, 'The newest GNOME, drawn in cloud'], [13.8, 18.2, 'Super + Space does the rest'],
    [18.2, 21.8, 'You choose every piece'], [21.9, 25, 'Five skies']];

function caption(t) {
    const current = CAPTIONS.find(([a, b]) => t >= a && t < b);
    $('caption').textContent = current ? current[2] : '';
    $('caption').classList.toggle('light', t > 23.4);
    place('caption', current ? shown(t, current[0], current[1], .5) : 0);
}

function seek(t) {
    sky(t);
    const glow = 1 + Math.sin(t * 5) * .015;
    place('title', shown(t, .5, 4, .9), `scale(${(.92 + ramp(t, .5, 3) * .08) * glow})`);
    place('line1', shown(t, 5.6, 9, .8), `translateY(${(1 - ramp(t, 5.6, 6.8)) * 40}px)`);
    place('desktop', shown(t, 9, 13.4), `perspective(1600px) rotateX(${(1 - ramp(t, 9, 11)) * 22}deg) translateY(${(1 - ramp(t, 9, 10.6)) * 160}px)`);
    place('center-shot', ramp(t, 11.2, 11.8));
    command(t);
    features(t);
    caption(t);
    place('end', ramp(t, 25.2, 26.2), `scale(${.94 + ramp(t, 25.2, 27) * .06})`);
}

// Layers above the sky
for (const [i, id] of ['veil', 'title', 'line1', 'desktop', 'caption', 'command', 'features', 'end'].entries())
    $(id).style.zIndex = 20 + i;
seek(0);
