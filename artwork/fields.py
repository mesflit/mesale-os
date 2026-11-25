"""Numeric helpers: colour conversion, noise and blur."""
import numpy as np


def linear(hex_color):
    """sRGB hex to linear light."""
    rgb = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
    return (np.array(rgb, np.float32) / 255) ** 2.2


def smoothstep(a, b, v):
    t = np.clip((v - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def fbm(rng, x, y, octaves, frequency):
    """Fractal value noise in 0..1."""
    size, total, weight, weights = 64, np.zeros_like(x), 1.0, 0.0
    for octave in range(octaves):
        table = rng.random((size, size), dtype=np.float32)
        px = x * frequency * 2 ** octave + 13.7 * octave
        py = y * frequency * 2 ** octave + 7.1 * octave
        ix, iy = np.floor(px).astype(np.int32), np.floor(py).astype(np.int32)
        fx, fy = px - ix, py - iy
        fx = fx ** 3 * (fx * (fx * 6 - 15) + 10)
        fy = fy ** 3 * (fy * (fy * 6 - 15) + 10)
        a, b = table[iy % size, ix % size], table[iy % size, (ix + 1) % size]
        c, d = table[(iy + 1) % size, ix % size], table[(iy + 1) % size, (ix + 1) % size]
        total += weight * ((a + (b - a) * fx) * (1 - fy) + (c + (d - c) * fx) * fy)
        weights += weight
        weight *= .5
    return total / weights


def blur(field, radius):
    """Three box passes, close to a Gaussian."""
    r = max(1, int(radius))
    for _ in range(3):
        for axis in (0, 1):
            pad = [(r + 1, r) if a == axis else (0, 0) for a in (0, 1)]
            cum = np.cumsum(np.pad(field, pad, mode="edge"), axis=axis, dtype=np.float64)
            if axis == 0:
                field = cum[2 * r + 1:] - cum[:-2 * r - 1]
            else:
                field = cum[:, 2 * r + 1:] - cum[:, :-2 * r - 1]
            field = field.astype(np.float32) / (2 * r + 1)
    return field
