"""Render a glass look: soft peaks of frosted glass over a pastel sky, back to front."""
import numpy as np
from PIL import Image

from fields import blur, fbm, linear, smoothstep

BASE = 1080   # pixel sizes below are given for this height and scaled to the real one


class Scene:
    def __init__(self, look, size):
        self.look = look
        self.width, self.height = size
        self.k = self.height / BASE
        self.rng = np.random.default_rng(look.seed)
        yy, xx = np.mgrid[0:self.height, 0:self.width].astype(np.float32)
        self.u, self.v = xx / self.height, yy / self.height
        self.aspect = self.width / self.height

    def sky(self):
        """Diagonal gradient with large soft patches of the look's colours."""
        look, u, v = self.look, self.u, self.v
        top, bottom = linear(look.sky[0]), linear(look.sky[1])
        t = np.clip(v * .75 + (u / self.aspect) * .25, 0, 1)[..., None]
        image = top + (bottom - top) * t
        for i, color in enumerate(look.glass):
            cx, cy = self.rng.uniform(0, self.aspect), self.rng.uniform(.1, .9)
            spread = self.rng.uniform(.35, .6)
            weight = np.exp(-((u - cx) ** 2 + (v - cy) ** 2) / spread ** 2)[..., None]
            image += (linear(color) - image) * weight * .35
        if look.stars:
            grid = (BASE, round(BASE * self.aspect))
            points = (self.rng.random(grid) > .9995) * self.rng.random(grid) ** 2
            rows = np.arange(self.height) * BASE // self.height
            cols = np.arange(self.width) * grid[1] // self.width
            points = points[rows][:, cols] * np.clip(1 - v * 1.2, 0, 1)
            image += blur(points.astype(np.float32), self.k)[..., None] * 4
        return image

    def peak(self, image, x, top, slope, round_, tint, depth):
        """One pane of glass shaped like a peak with a rounded tip."""
        u, v, k = self.u, self.v, self.k
        d = u - x
        # Hyperbola: straight flanks, rounded apex. The flanks bow slightly.
        edge = top + slope * (np.sqrt(d * d + round_ * round_) - round_) * (1 + .18 * np.abs(d))
        slope_at = slope * d / np.sqrt(d * d + round_ * round_)
        distance = (v - edge) / np.sqrt(1 + slope_at ** 2)   # > 0 inside, in picture heights
        pixel = 1 / self.height
        inside = smoothstep(-pixel, pixel, distance)

        # Frosted: what is behind is blurred, then tinted, lighter near the tip
        frosted = np.stack([blur(image[..., c], (10 + 18 * depth) * k) for c in range(3)], -1)
        glass = linear(tint)
        fade = np.clip((v - top) / .9, 0, 1)[..., None]
        fill = frosted * (.50 - .2 * fade) + glass * (.50 + .2 * fade)
        fill += (1 - fill) * (.22 * np.exp(-distance / .05))[..., None]   # inner glow along the rim
        out = image + (fill - image) * (inside * (.58 + .14 * depth))[..., None]

        # A thin bright rim, stronger on the side facing the light (upper left)
        facing = np.clip(.55 - .45 * np.sign(d) * np.minimum(np.abs(d) / .05, 1), .12, 1)
        rim = np.exp(-(distance / (1.4 * pixel * max(k, 1))) ** 2) * facing
        out += (1 - out) * (rim * .75)[..., None]
        # Soft shadow cast just outside, below the pane
        shadow = np.exp(-(np.maximum(-distance, 0) / .02)) * (distance < 0) * .06
        return out * (1 - shadow)[..., None]


def render(look, size):
    scene = Scene(look, size)
    image = scene.sky()
    rng = scene.rng
    count = 6
    # Panes in a shuffled order across the width; the tallest stand near the middle
    slots = rng.permutation(count)
    for i in range(count):
        depth = i / (count - 1)
        x = (slots[i] + rng.uniform(.2, .8)) / count * scene.aspect * 1.1 - scene.aspect * .05
        middle = abs(x / scene.aspect - .5) * 2
        top = .10 + .26 * middle + rng.uniform(0, .12) + .14 * depth
        slope = rng.uniform(1.3, 2.5)
        tint = look.glass[rng.integers(len(look.glass))]
        image = scene.peak(image, x, top, slope, rng.uniform(.05, .11), tint, depth)
    # Light falling from the upper left
    glow = np.exp(-((scene.u - scene.aspect * .2) ** 2 + (scene.v + .1) ** 2) / .6)[..., None]
    image += (1 - image) * glow * (.02 if look.dark else .18)
    # A faint marbling so large areas are not flat
    marble = fbm(rng, scene.u * .8, scene.v * .8, 5, 3) - .5
    image *= (1 + marble * .04)[..., None]
    image = np.clip(image, 0, 1) ** (1 / 2.2)
    grain = rng.normal(0, .004, (scene.height, scene.width, 1)).astype(np.float32)
    pixels = (np.clip(image + grain, 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(pixels)
