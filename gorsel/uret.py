#!/usr/bin/env python3
"""Mesale OS görselleri — özgün, tamamı koddan: ipeksi ışık duvar kâğıtları, logo, plymouth, grub.
Kullanım: uret.py <çıktı> [genişlik]     (numpy, pillow, rsvg-convert)"""
import json, pathlib, subprocess, sys
import numpy as np
from PIL import Image

OUT = pathlib.Path(sys.argv[1]); HERE = pathlib.Path(__file__).parent
W = int(sys.argv[2]) if len(sys.argv) > 2 else 3840
H = W * 9 // 16

# ad: (görünen ad, koyu mu, tohum, gök[üst, alt], bulut[gölge, orta, ışık], güneş(x, y), güneş rengi)
TEMA = {
    "day": ("Day", 0, 4, ["#3f86d8", "#bfe0fa"], ["#9db9dc", "#e6f0fb", "#ffffff"], (.74, .10), "#fff3d6"),
    "dawn": ("Dawn", 0, 9, ["#8ea6e6", "#ffd8c6"], ["#b9a3cf", "#f9cfcb", "#fff6ec"], (.22, .62), "#ffe0b0"),
    "mist": ("Mist", 0, 41, ["#b4c2d0", "#eef2f6"], ["#b9c5d1", "#e4eaf0", "#ffffff"], (.5, .10), "#ffffff"),
    "dusk": ("Dusk", 1, 17, ["#262a5e", "#e88a78"], ["#473a70", "#a2678f", "#ffc09a"], (.70, .66), "#ffb883"),
    "night": ("Night", 1, 23, ["#060a1a", "#1f3059"], ["#17234a", "#2a3f70", "#7f95c8"], (.78, .14), "#b9cbff"),
}

hx = lambda h: np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255
lin = lambda h: hx(h) ** 2.2

def gurultu(r, x, y, oktav, dalga):
    """Değer gürültüsü (fBm): yumuşak, döşemesiz."""
    top, g, gt = np.zeros_like(x), 1.0, 0.0
    for o in range(oktav):
        n = 64
        t = r.random((n, n), dtype=np.float32)
        X, Y = x * dalga * 2 ** o + 13.7 * o, y * dalga * 2 ** o + 7.1 * o
        xi, yi = np.floor(X).astype(np.int32), np.floor(Y).astype(np.int32)
        fx, fy = X - xi, Y - yi
        fx = fx ** 3 * (fx * (fx * 6 - 15) + 10); fy = fy ** 3 * (fy * (fy * 6 - 15) + 10)
        a, b = t[yi % n, xi % n], t[yi % n, (xi + 1) % n]
        c, d = t[(yi + 1) % n, xi % n], t[(yi + 1) % n, (xi + 1) % n]
        top += g * ((a + (b - a) * fx) * (1 - fy) + (c + (d - c) * fx) * fy)
        gt += g; g *= .5
    return top / gt

def yumusa(a, b, v):
    t = np.clip((v - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)

def bulanik(a, r):
    """Üç kutu süzgeci ≈ Gauss."""
    r = max(1, int(r))
    for _ in range(3):
        for ek in (0, 1):
            p = np.pad(a, [(r + 1, r) if e == ek else (0, 0) for e in (0, 1)], mode="edge")
            c = np.cumsum(p, axis=ek, dtype=np.float64)
            a = ((c[2 * r + 1:] - c[:-2 * r - 1]) if ek == 0 else (c[:, 2 * r + 1:] - c[:, :-2 * r - 1])).astype(np.float32) / (2 * r + 1)
    return a

def duvar(v, w, h):
    ad, koyu, tohum, gok, bulut, gunes, gr = v
    cikis, w, h = (w, h), 1920, 1080
    r = np.random.default_rng(tohum)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, t = xx / h, yy / h
    g0, g1 = lin(gok[0]), lin(gok[1])
    im = g0 + (g1 - g0) * np.clip(t / .85, 0, 1)[..., None] ** 1.1
    gx, gy = gunes[0] * w / h, gunes[1]
    uz = np.sqrt((u - gx) ** 2 + (t - gy) ** 2)
    isin = (.30 * np.exp(-(uz / .16) ** 2) + .30 * np.exp(-(uz / .5) ** 2))[..., None]
    im += lin(gr) * isin * (.6 if koyu else .7)
    if ad == "Night":
        yl = (r.random((h, w)) > .9996) * r.random((h, w)) ** 2 * np.clip(1 - t * 1.4, 0, 1)
        im += bulanik(yl.astype(np.float32), 1)[..., None] * 5
    c0, c1, c2 = (lin(c) for c in bulut)
    # ince yüksek sirrus
    ci = gurultu(r, u * .6 + t * .5 + 5, t * 4.2 - u * .5 + 9, 6, 1.6)
    im += (c2 - im) * (yumusa(.52, .80, ci) * np.clip(1 - t * 1.3, 0, 1) * .30)[..., None]

    bw = gurultu(r, u, t, 6, 7) - .5                         # kenarları karnabahar gibi büken alanlar
    bh = gurultu(r, u + 9, t + 4, 6, 7) - .5
    ince = gurultu(r, u + 3, t + 2, 6, 9) - .5
    for k in range(5):
        q = k / 4
        taban = .56 + .40 * q; buy = .055 + .115 * q; hava = .62 * (1 - q) ** 1.3
        U, V = u + bw * (.05 + .07 * q), t + bh * (.05 + .07 * q)
        z = np.zeros_like(u) - 1
        # kümeler: her biri üstü kubbe, altı dolu top yığını
        m = r.uniform(-.2, .5)
        while m < 2.0:
            en, boy = r.uniform(.16, .42) * (.6 + .9 * q), r.uniform(.7, 2.3) * buy
            for _ in range(int(16 + 22 * q)):
                e = r.normal(0, .42)
                cx = m + e * en
                kub = boy * np.exp(-(e / .55) ** 2)
                cy = taban - kub * r.uniform(.1, 1.0) + buy * .3
                rr = buy * r.uniform(.30, .85) * (.55 + .6 * np.exp(-e * e * 3))
                x0, x1 = int((cx - rr - .12) * h), int((cx + rr + .12) * h)
                y0, y1 = int((cy - rr - .12) * h), int((cy + rr + .12) * h)
                x0, x1, y0, y1 = max(x0, 0), min(x1, w), max(y0, 0), min(y1, h)
                if x0 >= x1 or y0 >= y1: continue
                sl = np.s_[y0:y1, x0:x1]
                d2 = rr * rr - (U[sl] - cx) ** 2 - (V[sl] - cy) ** 2
                z[sl] = np.maximum(z[sl], np.where(d2 > 0, np.sqrt(np.maximum(d2, 0)), -1))
            m += en * r.uniform(.8, 1.9)
        dolgu = yumusa(taban - .01, taban + .10, t + bh * .10 + bw * .05)   # bulut denizinin gövdesi
        maske = np.maximum((z > 0).astype(np.float32), 0)
        y_ = np.maximum(z, 0) + dolgu * buy * .55
        al = np.clip(np.maximum(bulanik(maske, 2 + 4 * q), dolgu), 0, 1)
        Z = bulanik(y_, 5 + 11 * q) + .6 * bulanik(y_, 18 + 34 * q) + ince * .003 * (.5 + q)
        dzx, dzy = np.gradient(Z, axis=1) * h, np.gradient(Z, axis=0) * h
        nz = 1 / np.sqrt(1 + dzx ** 2 + dzy ** 2)
        lx, ly = gx - u, gy - t
        lm = np.sqrt(lx * lx + ly * ly + .06)
        lam = (-dzx * lx / lm - dzy * (ly / lm * .7 - .45)) * nz * .62 + nz * .30
        der = np.clip((t - (taban - buy * 1.8)) / (buy * 4.0), 0, 1)
        isik = np.clip(.40 + lam * .62 - der * .26 + .22 * np.exp(-(uz / .55) ** 2), 0, 1)
        isik = bulanik(isik, 3 + 4 * q)[..., None]
        renk = np.where(isik < .5, c0 + (c1 - c0) * isik * 2, c1 + (c2 - c1) * (isik * 2 - 1))
        renk = renk * (1 - hava) + (g1 + lin(gr) * isin * .5) * hava
        im = im * (1 - al[..., None]) + renk * al[..., None]
    im += lin(gr) * isin * .18                               # ışık pusu
    im = np.clip(im, 0, 1) ** (1 / 2.2)
    im = Image.fromarray((np.clip(im + r.normal(0, .004, (h, w, 1)), 0, 1) * 255).astype(np.uint8))
    return im.resize(cikis, Image.LANCZOS)

# Logo: iki alev dili → M
def logo(boy=256, zemin=True):
    z = '<rect x="8" y="8" width="240" height="240" rx="66" fill="url(#z)"/>' if zemin else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{boy}" height="{boy}" viewBox="0 0 256 256"><defs>
<linearGradient id="a" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffc27a"/><stop offset=".55" stop-color="#ff8a3d"/><stop offset="1" stop-color="#e2502a"/></linearGradient><linearGradient id="z" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2f6fc4"/><stop offset="1" stop-color="#9cc8f2"/></linearGradient></defs>{z}
<path fill="url(#a)" d="M62 196 C50 150 66 96 92 52 C98 92 112 116 128 136 C144 116 158 92 164 52 C190 96 206 150 194 196 C176 190 166 172 164 144 C156 162 144 176 128 186 C112 176 100 162 92 144 C90 172 80 190 62 196Z"/></svg>'''

def svg2png(svg, yol, w=None):
    yol.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["rsvg-convert", "-o", str(yol)] + (["-w", str(w)] if w else []), input=svg.encode(), check=True)

def yaz(yol, s):
    yol.parent.mkdir(parents=True, exist_ok=True); yol.write_text(s)

bg = OUT / "usr/share/backgrounds/mesale"; bg.mkdir(parents=True, exist_ok=True)
on = OUT / "usr/share/mesale/previews"; on.mkdir(parents=True, exist_ok=True)
xml = ['<?xml version="1.0"?><!DOCTYPE wallpapers SYSTEM "gnome-wp-list.dtd"><wallpapers>']
for ad, v in TEMA.items():
    im = duvar(v, W, H)
    im.save(bg / f"{ad}.jpg", quality=93, subsampling=0)
    im.resize((640, 360), Image.LANCZOS).save(on / f"{ad}.png")
    if ad == "night":
        im.resize((1920, 1080), Image.LANCZOS).point(lambda p: int(p * .55)).save(OUT / "usr/share/mesale/grub.png")
    xml.append(f'<wallpaper deleted="false"><name>{v[0]}</name><filename>/usr/share/backgrounds/mesale/{ad}.jpg</filename>'
               f'<options>zoom</options><pcolor>{v[3][0]}</pcolor><scolor>{v[3][1]}</scolor></wallpaper>')
yaz(OUT / "usr/share/gnome-background-properties/mesale.xml", "".join(xml) + "</wallpapers>")
yaz(OUT / "usr/share/mesale/looks.json", json.dumps({k: {"name": v[0], "dark": bool(v[1])} for k, v in TEMA.items()}, ensure_ascii=False))
L, A = logo(), logo(zemin=False)
yaz(OUT / "usr/share/icons/hicolor/scalable/apps/mesale-logo.svg", L)
yaz(OUT / "usr/share/icons/hicolor/scalable/apps/mesale-flame.svg", A)
svg2png(L, OUT / "usr/share/pixmaps/mesale-logo.png", 256)
P = OUT / "usr/share/plymouth/themes/mesale"
svg2png(A, P / "logo.png", 200)
svg2png('<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"><circle cx="7" cy="7" r="6" fill="#ff8a3d"/></svg>', P / "nokta.png")
svg2png(f'<svg xmlns="http://www.w3.org/2000/svg" width="250" height="64">{logo(64, False)}'
        '<text x="66" y="44" font-family="Inter" font-weight="600" font-size="30" fill="#f6efe6">Mesale OS</text></svg>',
        OUT / "usr/share/mesale/gdm-logo.png")
