"""Render a look: a sky with five layers of cumulus, painted back to front."""
import numpy as np
from PIL import Image

from fields import blur, fbm, linear, smoothstep

WIDTH, HEIGHT = 1920, 1080   # soft content, upscaled for the final size
LAYERS = 5


class Scene:
    def __init__(self, look):
        self.look = look
        self.rng = np.random.default_rng(look.seed)
        yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH].astype(np.float32)
        self.u, self.v = xx / HEIGHT, yy / HEIGHT
        self.sun_x, self.sun_y = look.sun[0] * WIDTH / HEIGHT, look.sun[1]
        self.sun_distance = np.hypot(self.u - self.sun_x, self.v - self.sun_y)
        self.glow = (.30 * np.exp(-(self.sun_distance / .16) ** 2)
                     + .30 * np.exp(-(self.sun_distance / .5) ** 2))[..., None]
        self.horizon = linear(look.sky[1])
        self.sun_color = linear(look.sun_color)
        self.shadow, self.middle, self.light = (linear(c) for c in look.cloud)

    def sky(self):
        top = linear(self.look.sky[0])
        image = top + (self.horizon - top) * np.clip(self.v / .85, 0, 1)[..., None] ** 1.1
        image += self.sun_color * self.glow * (.6 if self.look.dark else .7)
        if self.look.stars:
            points = (self.rng.random(self.u.shape) > .9996) * self.rng.random(self.u.shape) ** 2
            points = points * np.clip(1 - self.v * 1.4, 0, 1)
            image += blur(points.astype(np.float32), 1)[..., None] * 5
        cirrus = fbm(self.rng, self.u * .6 + self.v * .5 + 5, self.v * 4.2 - self.u * .5 + 9, 6, 1.6)
        amount = smoothstep(.52, .80, cirrus) * np.clip(1 - self.v * 1.3, 0, 1) * .30
        return image + (self.light - image) * amount[..., None]

    def spheres(self, warped_u, warped_v, base, height, depth):
        """Height field of overlapping balls grouped into heaps. Below zero is empty."""
        rng, field = self.rng, np.full_like(self.u, -1)
        heap_x = rng.uniform(-.2, .5)
        while heap_x < 2.0:
            width, tall = rng.uniform(.16, .42) * (.6 + .9 * depth), rng.uniform(.7, 2.3) * height
            for _ in range(int(16 + 22 * depth)):
                offset = rng.normal(0, .42)
                cx = heap_x + offset * width
                cy = base - tall * np.exp(-(offset / .55) ** 2) * rng.uniform(.1, 1.0) + height * .3
                radius = height * rng.uniform(.30, .85) * (.55 + .6 * np.exp(-offset * offset * 3))
                x0, x1 = (int(np.clip((cx + s * (radius + .12)) * HEIGHT, 0, WIDTH)) for s in (-1, 1))
                y0, y1 = (int(np.clip((cy + s * (radius + .12)) * HEIGHT, 0, HEIGHT)) for s in (-1, 1))
                if x0 >= x1 or y0 >= y1:
                    continue
                box = np.s_[y0:y1, x0:x1]
                d2 = radius ** 2 - (warped_u[box] - cx) ** 2 - (warped_v[box] - cy) ** 2
                field[box] = np.maximum(field[box], np.where(d2 > 0, np.sqrt(np.maximum(d2, 0)), -1))
            heap_x += width * rng.uniform(.8, 1.9)
        return field

    def layer(self, depth, warp_x, warp_y, detail):
        """One cloud layer. depth 0 is the farthest, 1 the nearest. Returns colour and alpha."""
        base, height = .56 + .40 * depth, .055 + .115 * depth
        haze = .62 * (1 - depth) ** 1.3
        strength = .05 + .07 * depth
        balls = self.spheres(self.u + warp_x * strength, self.v + warp_y * strength, base, height, depth)
        body = smoothstep(base - .01, base + .10, self.v + warp_y * .10 + warp_x * .05)
        relief = np.maximum(balls, 0) + body * height * .55
        alpha = np.clip(np.maximum(blur((balls > 0).astype(np.float32), 2 + 4 * depth), body), 0, 1)

        surface = (blur(relief, 5 + 11 * depth) + .6 * blur(relief, 18 + 34 * depth)
                   + detail * .003 * (.5 + depth))
        slope_x, slope_y = (np.gradient(surface, axis=a) * HEIGHT for a in (1, 0))
        normal_z = 1 / np.sqrt(1 + slope_x ** 2 + slope_y ** 2)
        to_sun_x, to_sun_y = self.sun_x - self.u, self.sun_y - self.v
        length = np.sqrt(to_sun_x ** 2 + to_sun_y ** 2 + .06)
        lambert = ((-slope_x * to_sun_x / length - slope_y * (to_sun_y / length * .7 - .45)) * normal_z * .62
                   + normal_z * .30)
        depth_shade = np.clip((self.v - (base - height * 1.8)) / (height * 4.0), 0, 1)
        light = np.clip(.40 + lambert * .62 - depth_shade * .26 + .22 * np.exp(-(self.sun_distance / .55) ** 2), 0, 1)
        light = blur(light, 3 + 4 * depth)[..., None]
        color = np.where(light < .5,
                         self.shadow + (self.middle - self.shadow) * light * 2,
                         self.middle + (self.light - self.middle) * (light * 2 - 1))
        color = color * (1 - haze) + (self.horizon + self.sun_color * self.glow * .5) * haze
        return color, alpha[..., None]


def render(look, size):
    scene = Scene(look)
    image = scene.sky()
    warp_x = fbm(scene.rng, scene.u, scene.v, 6, 7) - .5
    warp_y = fbm(scene.rng, scene.u + 9, scene.v + 4, 6, 7) - .5
    detail = fbm(scene.rng, scene.u + 3, scene.v + 2, 6, 9) - .5
    for i in range(LAYERS):
        color, alpha = scene.layer(i / (LAYERS - 1), warp_x, warp_y, detail)
        image = image * (1 - alpha) + color * alpha
    image += scene.sun_color * scene.glow * .18
    image = np.clip(image, 0, 1) ** (1 / 2.2)
    grain = scene.rng.normal(0, .004, (HEIGHT, WIDTH, 1))   # hides banding
    pixels = (np.clip(image + grain, 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(pixels).resize(size, Image.LANCZOS)
