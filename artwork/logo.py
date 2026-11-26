"""The Mesale mark: two flames that form an M."""

FLAMES = ("M62 196 C50 150 66 96 92 52 C98 92 112 116 128 136 C144 116 158 92 164 52 C190 96 206 150 194 196 "
          "C176 190 166 172 164 144 C156 162 144 176 128 186 C112 176 100 162 92 144 C90 172 80 190 62 196Z")


def mark(size=256, tile=True):
    """SVG of the mark, optionally on its sky tile."""
    ground = '<rect x="8" y="8" width="240" height="240" rx="66" fill="url(#sky)"/>' if tile else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 256 256"><defs>
<linearGradient id="flame" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffc27a"/><stop offset=".55" stop-color="#ff8a3d"/><stop offset="1" stop-color="#e2502a"/></linearGradient>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2f6fc4"/><stop offset="1" stop-color="#9cc8f2"/></linearGradient></defs>
{ground}<path fill="url(#flame)" d="{FLAMES}"/></svg>'''


def wordmark():
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="250" height="64">{mark(64, tile=False)}'
            '<text x="66" y="44" font-family="Inter" font-weight="600" font-size="30" fill="#f2f7ff">Mesale OS</text></svg>')


DOT = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"><circle cx="7" cy="7" r="6" fill="#ff8a3d"/></svg>'


QUADRANTS = " ▘▝▀▖▌▞▛▗▚▐▜▄▙▟█"


def terminal(columns=30, rows=14):
    """The mark in quadrant blocks, coloured top to bottom with fastfetch's $1 $2 $3."""
    import io
    import subprocess

    from PIL import Image

    # The flames span x 54..202 and y 50..198; a cell is two pixels wide and two tall.
    svg = (mark(tile=False).replace('fill="url(#flame)"', 'fill="#000"')
           .replace('viewBox="0 0 256 256"', 'viewBox="54 50 148 148" preserveAspectRatio="none"'))
    png = subprocess.run(["rsvg-convert", "-w", str(columns * 2), "-h", str(rows * 2)],
                         input=svg.encode(), capture_output=True, check=True).stdout
    image = Image.open(io.BytesIO(png)).convert("RGBA")
    lines = []
    for row in range(rows):
        cells = ""
        for column in range(columns):
            bits = sum(1 << i for i, (dx, dy) in enumerate(((0, 0), (1, 0), (0, 1), (1, 1)))
                       if image.getpixel((2 * column + dx, 2 * row + dy))[3] > 110)
            cells += QUADRANTS[bits]
        colour = 1 if row < rows * .4 else 2 if row < rows * .72 else 3
        lines.append(f"${colour}{cells.rstrip()}")
    return "\n".join(lines) + "\n"
