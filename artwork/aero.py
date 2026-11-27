"""Render the Aero look: a bright sky with Mesale's clouds, light rays, glossy green
hills and floating glass bubbles."""
import numpy as np
from PIL import Image

import clouds
from fields import blur, fbm, linear, smoothstep


def rays(scene):
    """Soft beams fanning out from the sun."""
    angle = np.arctan2(scene.v - scene.sun_y, scene.u - scene.sun_x)
    wobble = fbm(np.random.default_rng(scene.look.seed + 2), angle * 3, angle * 0 + 1, 3, 2)
    beams = smoothstep(.55, .9, .5 + .5 * np.sin(angle * 14 + wobble * 6))
    return beams * np.exp(-scene.sun_distance / .9) * .22


def hill(scene, ridge, amplitude, waves, seed):
    """Height of a rolling hill at each column, in picture heights."""
    x = scene.u[0]
    rng = np.random.default_rng(seed)
    height = np.zeros_like(x)
    for _ in range(waves):
        f, phase = rng.uniform(1.4, 3.6), rng.uniform(0, 6.3)
        height += np.sin(x * f + phase) / waves
    return ridge - amplitude * height


def hills(scene, image):
    """Three hills, back to front, lit from the sun with a glossy band along the crest."""
    look, v, k = scene.look, scene.v, scene.k
    pixel = 1 / scene.height
    for i, (ridge, amplitude, dark, light) in enumerate([
            (.68, .05, "#3f9a3a", "#8fd66a"),
            (.78, .07, "#2f8a2c", "#7ccf4f"),
            (.90, .07, "#237a22", "#a6e85a")]):
        top = hill(scene, ridge, amplitude, 3, look.seed * 10 + i)[None, :]
        distance = v - top
        inside = smoothstep(-pixel, pixel, distance)
        shade = np.clip(distance / .25, 0, 1)[..., None]
        color = linear(light) + (linear(dark) - linear(light)) * shade
        slope = np.gradient(top[0])[None, :] * scene.height
        lit = np.clip(.5 - slope * .6, 0, 1)[..., None]            # faces toward the sun are brighter
        color = color * (.8 + .4 * lit)
        gloss = np.exp(-((distance - .012) / .010) ** 2)[..., None] * .55
        color += (1 - color) * gloss
        haze = (.35 - .15 * i) * (1 - shade)                         # far hills fade into the sky
        color = color * (1 - haze) + linear(look.sky[1]) * haze
        image = image + (color - image) * inside[..., None]
        # A thin light line on the crest
        image += (1 - image) * (np.exp(-(distance / (1.2 * pixel * max(k, 1))) ** 2) * .5)[..., None]
    return image


def bubbles(scene, image):
    """Glass bubbles: clear inside, a bright rim, a highlight and a hint of colour."""
    rng = np.random.default_rng(scene.look.seed + 3)
    aspect = scene.width / scene.height
    placed = 0
    while placed < 15:
        r = rng.uniform(.012, .055) * rng.choice([1, 1, 1, 1.7])
        cx, cy = rng.uniform(0, aspect), rng.uniform(.08, .85)
        if np.hypot(cx - scene.sun_x, cy - scene.sun_y) < .35:
            continue   # keep the sun clear
        placed += 1
        x0, x1 = (int(np.clip((cx + s * (r * 1.2)) * scene.height, 0, scene.width)) for s in (-1, 1))
        y0, y1 = (int(np.clip((cy + s * (r * 1.2)) * scene.height, 0, scene.height)) for s in (-1, 1))
        if x0 >= x1 or y0 >= y1:
            continue
        box = np.s_[y0:y1, x0:x1]
        du, dv = scene.u[box] - cx, scene.v[box] - cy
        d = np.sqrt(du * du + dv * dv) / r
        disc = smoothstep(1.0, .97, d)
        rim = np.exp(-((d - .96) / .05) ** 2) * .55 + disc * d ** 6 * .35
        spot = np.exp(-(((du + r * .38) ** 2 + (dv + r * .42) ** 2) / (r * .22) ** 2)) * .85
        tint = np.stack([.35 + .3 * np.cos(np.arctan2(dv, du) + p) for p in (0, 2.1, 4.2)], -1)
        part = image[box]
        part = part * (1 - disc * .06)[..., None] + tint * (disc * d ** 4 * .10)[..., None]
        part += (1 - part) * (rim + spot * disc)[..., None]
        image[box] = part
    return image


def render(look, size):
    scene = clouds.Scene(look, size)
    image = scene.sky()
    image += (1 - image) * rays(scene)[..., None]
    warp_x = fbm(scene.rng, scene.u, scene.v, 6, 7) - .5
    warp_y = fbm(scene.rng, scene.u + 9, scene.v + 4, 6, 7) - .5
    detail = fbm(scene.rng, scene.u + 3, scene.v + 2, 6, 9) - .5
    fine = fbm(np.random.default_rng(look.seed + 1), scene.u + 1, scene.v + 7, 7, 40)
    for depth in (0, .25, .45):   # only the far banks: they rise behind the hills
        color, alpha = scene.layer(depth, warp_x, warp_y, detail, fine)
        image = image * (1 - alpha) + color * alpha
    image += scene.sun_color * scene.glow * .25
    image = hills(scene, image)
    image = bubbles(scene, np.clip(image, 0, 1))
    image = np.clip(image, 0, 1) ** (1 / 2.2)
    grain = scene.rng.normal(0, .004, (scene.height, scene.width, 1)).astype(np.float32)
    pixels = (np.clip(image + grain, 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(pixels)
