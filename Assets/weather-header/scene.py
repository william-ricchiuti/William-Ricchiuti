"""A New Orleans street painted pixel by pixel at 256x96, in the style of a
1990s VGA adventure game. Every color is snapped to the VGA DAC's 6-bit levels.

Conditions are produced the way those games did it: one drawing, different
palettes (day / overcast / night) plus weather layers (clouds, rain, fog, stars,
sun, a moon in its real phase). Output: an animated GIF at an exact 3x scale.
"""
import math, random, pathlib


def _flat(im):
    """Pixel list; works on old and new Pillow."""
    return im.get_flattened_data() if hasattr(im, "get_flattened_data") else list(im.getdata())
from PIL import Image, ImageDraw, ImageFont

W, H, SCALE, FRAMES, FRAME_MS = 256, 96, 3, 150, 90
BAR, GROUND = 12, 79
HERE = pathlib.Path(__file__).parent
FONT = str(HERE / "fonts" / "PixelifySans-Regular.ttf")
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def vga(h):
    """#rrggbb -> nearest color the VGA DAC can show (6 bits per channel)."""
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    q = lambda v: (v >> 2) << 2 | (v >> 6)
    return (q(r), q(g), q(b))


def mix(a, b, t):
    pa, pb = (int(a[i:i + 2], 16) for i in (1, 3, 5)), (int(b[i:i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(pa, pb))


def gray(h, t):
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    l = round(r * .3 + g * .59 + b * .11)
    return mix(h, f"#{l:02x}{l:02x}{l:02x}", t)


# ---------------------------------------------------------------- palettes
NIGHT = dict(
    s0="#10142c", s1="#181c3c", s2="#22244c", s3="#30305c", s4="#423c68", s5="#584870", s6="#705478",
    cloud="#2c2c4c", cloud2="#383858",
    far="#1c1e34", far2="#262842", farS="#16182a", winA="#d8a850", winB="#806438",
    domeW="#383c58", domeR="#565c7c", domeH="#7880a0", rib="#262a40",
    led0="#f8d070", led1="#d8a040", led2="#8c6830",
    cat="#c8bca0", catL="#e0d4b4", catS="#8c8270", catD="#4c463c", door="#f0c058", catRoof="#28283c",
    lav="#5c5088", lavT="#a8a0cc", mint="#3c6c60", mintT="#a0ccb8", cor="#8c544c", corT="#cca090",
    win="#f0c868", winD="#2c2c3c", doorD="#241c24",
    brick="#7c4434", brick2="#5c3028", corn="#a88468", shut="#2c4c38", iron="#101014", fern="#2c5c2c", fern2="#447c38",
    oak="#18241c", oak2="#24382a", oak3="#30483a", moss="#56664c", bark="#2c241c",
    post="#141418", glass="#fce098", glow0="#6c5434", glow1="#8c6c3c",
    walk="#4a4a58", walkH="#5c5c6c", curb="#24242c", st0="#16161e", st1="#1e1e28", rail="#4c4c5c",
    refl0="#5c4a30", refl1="#7c6440",
    carG="#3e5a2c", carG2="#2c4220", carR="#22341a", cream="#b8ac7c", carW="#e8d08c", red="#8c2c24", head="#fce098",
    tire="#0c0c0c", rain="#6c7ca4", rainH="#a4b4d4", splash="#8898bc",
    moon="#f0ecd0", moonD="#2c2c48", star0="#f4f0d8", star1="#9c9cbc", star2="#4c4c74",
    sun="#fcf4c8", sunH="#f8e8a0", fog="#5c5474", fog2="#7c7090",
)
DAY = dict(NIGHT,
    s0="#2c5ca8", s1="#3868b4", s2="#4878c0", s3="#5c8cc8", s4="#74a0d0", s5="#90b4d8", s6="#b0c8dc",
    cloud="#c4d0e0", cloud2="#e8ecf4",
    far="#64708a", far2="#8894ac", farS="#525c74", winA="#a8b8cc", winB="#8c9cb4",
    domeW="#8890a4", domeR="#aab2c4", domeH="#d0d8e4", rib="#727a8e",
    led0="#9ca4b4", led1="#9ca4b4", led2="#9ca4b4",
    cat="#e4dcc8", catL="#f4ecdc", catS="#a89c84", catD="#5c5444", door="#6c4428", catRoof="#5c5c6c",
    lav="#9484c4", lavT="#ece4f8", mint="#68ac94", mintT="#e0f4ec", cor="#c87c68", corT="#f8dccc",
    win="#56789c", winD="#3c4c5c", doorD="#4c3c34",
    brick="#a85c44", brick2="#84443c", corn="#d4b494", shut="#3c6c48", iron="#24242c", fern="#3c7c34", fern2="#5c9c44",
    oak="#284628", oak2="#386034", oak3="#507c40", moss="#8c9c7c", bark="#4c3c2c",
    post="#24242c", glass="#a4b4c4",
    walk="#8c8c94", walkH="#a4a4ac", curb="#5c5c64", st0="#4c4c54", st1="#585860", rail="#8c8c9c",
    refl0="#6c747c", refl1="#848c94",
    carG="#4c7c38", carG2="#3c6428", carR="#2c4c24", cream="#e4d8a4", carW="#a4bccc", red="#a83c2c", head="#e8e8d8",
    rain="#8c98ac", rainH="#c4ccd8", splash="#a4acbc",
)
# overcast day: same drawing, desaturated, gray sky
OVERCAST = {k: gray(v, .45) for k, v in DAY.items()}
OVERCAST.update(s0="#545c6c", s1="#5c6474", s2="#646c7c", s3="#6c7484", s4="#788090", s5="#848c98", s6="#9098a0",
                cloud="#4c5464", cloud2="#a4acb4", fog="#a8acb0", fog2="#c4c8c8",
                barBg="#b0b0b0")
HOT = dict(DAY, s4="#88aed0", s5="#b4c4c8", s6="#dcd4b0")      # washed-out, hazy horizon

UI = dict(barBg="#b0b0b0", barTx="#000000", rule="#000000",
          boxBg="#d4d4cc", boxHi="#f4f4ec", boxSh="#7c7c74", boxEdge="#202020")


class Canvas:
    def __init__(s, pal, w=W, h=H):
        s.pal, s.w, s.h = {k: vga(v) for k, v in {**pal, **UI}.items()}, w, h
        s.im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); s.px = s.im.load()

    def p(s, x, y, c):
        if 0 <= x < s.w and 0 <= y < s.h: s.px[x, y] = (*s.pal[c], 255)
    def rect(s, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1): s.p(x, y, c)
    def dither(s, x0, y0, x1, y1, c1, c2, t):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1): s.p(x, y, c2 if BAYER[y % 4][x % 4] < t * 16 else c1)
    def hline(s, x0, x1, y, c):
        for x in range(x0, x1 + 1): s.p(x, y, c)
    def vline(s, x, y0, y1, c):
        for y in range(y0, y1 + 1): s.p(x, y, c)
    def line(s, x0, y0, x1, y1, c):
        dx, dy = abs(x1 - x0), -abs(y1 - y0); sx = 1 if x0 < x1 else -1; sy = 1 if y0 < y1 else -1; e = dx + dy
        while True:
            s.p(x0, y0, c)
            if x0 == x1 and y0 == y1: break
            e2 = 2 * e
            if e2 >= dy: e += dy; x0 += sx
            if e2 <= dx: e += dx; y0 += sy
    def tri(s, ax, base_y, apex_x, apex_y, bx, c):
        for y in range(apex_y, base_y + 1):
            f = (y - apex_y) / max(1, base_y - apex_y)
            s.hline(round(apex_x - (apex_x - ax) * f), round(apex_x + (bx - apex_x) * f), y, c)
    def disc(s, cx, cy, r, c, mask=None):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + r * 0.6 and (mask is None or mask(x, y)): s.p(x, y, c)


# ---------------------------------------------------------------- layers
CLOUDS = {
    "clear_day": [(212, 30, 16, 3), (60, 44, 14, 2)],
    "clear_night": [],
    "partly": [(150, 22, 22, 4), (232, 34, 18, 3), (70, 46, 18, 3), (196, 46, 14, 2)],
    "cloudy": [(40, 20, 40, 7), (120, 16, 44, 6), (200, 22, 40, 7), (250, 14, 24, 5), (90, 32, 32, 5), (160, 34, 30, 5), (230, 40, 26, 4), (20, 40, 22, 4)],
    "rain": [(40, 20, 34, 6), (120, 16, 40, 5), (200, 22, 36, 6), (250, 14, 22, 4), (80, 30, 26, 4)],
}
MOON_XY, SUN_XY = (170, 24), (168, 26)
BOX_RECT = (6, 14, 126, 37)      # narrator box area: keep stars and sun out of it
REFLECT_X = [44, 50, 66, 72, 88, 94, 108, 119, 132, 145, 213, 228, 243]


def sky(c, kind):
    ramp = ["s0", "s1", "s2", "s3", "s4", "s5", "s6"]
    top, bot = BAR, GROUND - 1
    for y in range(top, bot + 1):
        f = ((y - top) / (bot - top)) ** 1.35 * (len(ramp) - 1)
        i = min(int(f), len(ramp) - 2)
        c.dither(0, y, W - 1, y, ramp[i], ramp[i + 1], f - i)


def clouds(c, key, density=22):
    for cx, cy, rx, ry in CLOUDS.get(key, []):
        for y in range(cy - ry, cy + ry + 1):
            for x in range(cx - rx, cx + rx + 1):
                d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                if d <= 1:
                    t = 1 - d; b = BAYER[y % 4][x % 4]
                    if b < t * density: c.p(x, y, "cloud2" if (t > .6 and b < 6) else "cloud")


def moon(c, phase):
    """Real lunar phase. phase: 0 new .. .5 full .. 1 new. Lit side per northern hemisphere."""
    cx, cy = MOON_XY; r = 5; th = 2 * math.pi * phase
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            u, v = (x - cx) / (r + .5), (y - cy) / (r + .5)
            if u * u + v * v > 1: continue
            edge = math.cos(th) * math.sqrt(max(0, 1 - v * v))
            lit = (u > edge) if phase < .5 else (u < -edge)
            c.p(x, y, "moon" if lit else "moonD")


def sun(c):
    cx, cy = SUN_XY
    for y in range(cy - 10, cy + 11):
        for x in range(cx - 10, cx + 11):
            d = math.hypot(x - cx, y - cy)
            if d <= 4.6: c.p(x, y, "sun")
            elif d < 10 and BAYER[y % 4][x % 4] < (10 - d) * 1.4: c.p(x, y, "sunH")


def stars(seed=5, n=34):
    random.seed(seed); out = []
    while len(out) < n:
        x, y = random.randint(0, W - 1), random.randint(BAR + 1, 50)
        bx0, by0, bx1, by1 = BOX_RECT
        if bx0 - 2 <= x <= bx1 + 2 and by0 - 2 <= y <= by1 + 2: continue
        if math.hypot(x - MOON_XY[0], y - MOON_XY[1]) < 9: continue
        if 113 <= x <= 151 and y >= 20: continue           # cathedral spires
        out.append((x, y, random.randint(0, 5)))
    return out


def buildings(c, night):
    rnd = random.Random(3)
    # far CBD skyline
    for x, w, top in [(184, 9, 38), (194, 7, 46), (202, 11, 30), (214, 8, 42), (223, 12, 34), (236, 9, 26), (246, 10, 40)]:
        c.rect(x, top, x + w - 1, GROUND - 1, "far"); c.vline(x, top, GROUND - 1, "far2"); c.vline(x + w - 1, top, GROUND - 1, "farS"); c.hline(x, x + w - 1, top, "far2")
        for wy in range(top + 3, GROUND - 4, 3):
            for wx in range(x + 2, x + w - 1, 2):
                r = rnd.random()
                if r < (.22 if night else .30): c.p(wx, wy, "winA")
                elif r < .40: c.p(wx, wy, "winB")
    # Superdome
    cx, base = 178, GROUND - 1
    for y in range(68, base + 1):
        hw = 21 + (y - 68) * 2 // 10
        c.hline(cx - hw, cx + hw, y, "domeW")
        for x in range(cx - hw + 1, cx + hw, 3): c.p(x, y, "rib")
    for y in range(60, 68):
        k = (68 - y) / 8.0; hw = round(21 * math.sqrt(max(0, 1 - k * k)))
        c.hline(cx - hw, cx + hw, y, "domeR")
    c.hline(cx - 14, cx + 14, 62, "domeH"); c.hline(cx - 18, cx + 18, 64, "domeH")
    for x in range(cx - 21, cx + 22): c.p(x, 67, ["led0", "led1", "led2"][x % 3])
    # St. Louis Cathedral
    L, R = 114, 150
    c.rect(118, 52, 146, 60, "catRoof"); c.rect(L, 60, R, GROUND - 1, "cat")
    if night:
        c.dither(L, 72, R, 73, "cat", "catL", .5); c.rect(L, 74, R, GROUND - 1, "catL")
    else:
        c.rect(L, 61, L + 3, GROUND - 1, "catL")                          # sunlit left edge
    c.hline(L - 1, R + 1, 60, "catS"); c.hline(L - 1, R + 1, 61, "catD"); c.hline(L, R, 69, "catS")
    c.vline(R, 62, GROUND - 1, "catS")
    c.rect(128, 40, 136, 59, "cat"); c.vline(136, 40, 59, "catS"); c.hline(127, 137, 40, "catS")
    c.tri(128, 39, 132, 27, 136, "catS"); c.vline(132, 27, 39, "catL")
    c.vline(132, 21, 26, "catD"); c.hline(131, 133, 23, "catD")
    for (x, y) in [(131, 43), (132, 43), (133, 43), (130, 44), (134, 44), (130, 45), (134, 45), (130, 46), (134, 46), (131, 47), (132, 47), (133, 47)]: c.p(x, y, "catS")
    c.rect(131, 44, 133, 46, "catL"); c.p(132, 44, "catD"); c.p(132, 45, "catD"); c.p(133, 45, "catD")
    c.rect(131, 51, 133, 56, "catD"); c.p(132, 50, "catD")
    for x0 in (115, 142):
        c.rect(x0, 49, x0 + 7, 59, "cat"); c.vline(x0 + 7, 49, 59, "catS"); c.hline(x0 - 1, x0 + 8, 49, "catS")
        c.tri(x0, 48, x0 + 3, 38, x0 + 7, "catS"); c.vline(x0 + 3, 39, 48, "catL")
        c.rect(x0 + 2, 52, x0 + 4, 57, "catD"); c.p(x0 + 3, 51, "catD")
    for x0, top in [(118, 72), (130, 70), (143, 72)]:
        w = 5 if x0 == 130 else 4
        c.rect(x0, top + 1, x0 + w - 1, GROUND - 1, "door"); c.hline(x0 + 1, x0 + w - 2, top, "door")
    for x0 in (120, 132, 145): c.rect(x0, 63, x0 + 1, 66, "door" if night else "catD")
    # gas lamp
    lx = 108
    if night:
        for y in range(52, 70):
            for x in range(lx - 8, lx + 9):
                d = math.hypot(x - lx, (y - 61) * 1.2)
                if d < 8 and BAYER[y % 4][x % 4] < (8 - d) * 1.6: c.p(x, y, "glow0" if d > 4 else "glow1")
    c.vline(lx, 64, GROUND - 1, "post"); c.hline(lx - 1, lx + 1, GROUND - 1, "post"); c.hline(lx - 1, lx + 1, 64, "post")
    c.rect(lx - 2, 58, lx + 2, 63, "post"); c.hline(lx - 3, lx + 3, 57, "post"); c.hline(lx - 1, lx + 1, 56, "post")
    c.rect(lx - 1, 59, lx + 1, 62, "glass")
    # shotgun houses
    for x0, body, trim in [(39, "lav", "lavT"), (61, "mint", "mintT"), (83, "cor", "corT")]:
        x1 = x0 + 20; mid = x0 + 10
        c.rect(x0, 64, x1, GROUND - 1, body); c.tri(x0, 63, mid, 55, x1, body)
        c.line(x0 - 1, 64, mid, 54, trim); c.line(mid, 54, x1 + 1, 64, trim)
        c.p(mid, 59, trim); c.hline(x0, x1, 64, trim)
        for x in range(x0 + 1, x1, 2): c.p(x, 65, trim)
        c.vline(x0 + 1, 65, GROUND - 1, trim); c.vline(x1 - 1, 65, GROUND - 1, trim)
        c.rect(x0 + 4, 69, x0 + 7, GROUND - 1, "doorD"); c.rect(x0 + 5, 70, x0 + 6, 72, "win")
        c.vline(x0 + 11, 67, 74, trim); c.vline(x0 + 17, 67, 74, trim)
        c.rect(x0 + 12, 68, x0 + 16, 73, "win")
        if not night: c.p(x0 + 13, 69, trim); c.p(x0 + 14, 69, trim)          # glint on glass
        c.hline(x0, x1, GROUND - 1, "doorD")
    # live oak with Spanish moss
    for a, b in [((14, GROUND - 1), (15, 62)), ((15, GROUND - 1), (16, 62)), ((16, GROUND - 1), (17, 63)), ((16, 64), (30, 55)), ((15, 66), (4, 59))]:
        c.line(*a, *b, "bark")
    blobs = [(6, 54, 11), (19, 47, 12), (31, 51, 10), (-2, 59, 8), (25, 58, 8), (12, 57, 9)]
    for bx, by, r in blobs: c.disc(bx, by, r, "oak")
    for bx, by, r in blobs:
        c.disc(bx - 2, by - 3, r - 4, "oak2", mask=lambda x, y: BAYER[y % 4][x % 4] < 9)
        c.disc(bx - 3, by - 4, max(1, r - 7), "oak3", mask=lambda x, y: BAYER[y % 4][x % 4] < 7)
    rm = random.Random(7)
    for mx in [1, 4, 8, 11, 19, 23, 27, 30, 34, 36]:
        top_y = 61 + rm.randint(-2, 2); ln = rm.randint(5, 10)
        for k in range(ln):
            if k % 3 != 2: c.p(mx + (1 if k > ln // 2 else 0), top_y + k, "moss")
    # Creole townhouse
    x0, x1 = 206, 252
    c.rect(x0, 54, x1, GROUND - 1, "brick")
    for y in range(56, GROUND, 3):
        for x in range(x0 + (y // 3) % 2 * 2, x1, 4): c.p(x, y, "brick2")
    c.rect(x0 - 2, 52, x1 + 2, 53, "corn"); c.hline(x0 - 2, x1 + 2, 54, "brick2")
    for dx in (211, 226, 241):
        c.vline(dx - 1, 56, 63, "shut"); c.vline(dx + 6, 56, 63, "shut")
        c.rect(dx, 56, dx + 5, 63, "win"); c.vline(dx + 2, 56, 63, "brick2")
        c.vline(dx - 1, 69, GROUND - 1, "shut"); c.vline(dx + 6, 69, GROUND - 1, "shut")
        c.rect(dx, 69, dx + 5, GROUND - 1, "winD" if dx == 226 else "win")
    c.hline(x0 - 2, x1 + 2, 63, "iron")
    for x in range(x0 - 2, x1 + 3, 2): c.vline(x, 64, 65, "iron")
    c.hline(x0 - 3, x1 + 3, 66, "iron"); c.hline(x0 - 3, x1 + 3, 67, "brick2")
    for px_ in (x0 - 1, 229, x1 + 1): c.vline(px_, 68, GROUND - 1, "iron")
    for fx in (215, 245):
        c.rect(fx - 1, 68, fx + 1, 69, "fern"); c.p(fx, 70, "fern"); c.p(fx - 1, 68, "fern2"); c.p(fx + 1, 69, "fern2")
    # street
    c.rect(0, GROUND, W - 1, GROUND + 1, "walk"); c.hline(0, W - 1, GROUND, "walkH")
    c.hline(0, W - 1, GROUND + 2, "curb")
    c.dither(0, GROUND + 3, W - 1, H - 1, "st0", "st1", .35)
    c.hline(0, W - 1, 89, "rail"); c.hline(0, W - 1, 92, "rail")


def fog_layer(pal):
    """Two dithered fog banks hugging the street; drawn over the buildings."""
    f = Canvas(pal)
    for y in range(52, GROUND + 6):
        dens = max(0.0, 1 - abs(y - 70) / 16) * .38
        for x in range(W):
            if BAYER[y % 4][x % 4] < dens * 16: f.p(x, y, "fog2" if y > 64 and BAYER[y % 4][x % 4] < 4 else "fog")
    return f.im


def streetcar(pal):
    s = Canvas(pal, 40, 26); oy = 7
    s.line(10, oy, 3, 0, "tire")
    s.rect(8, oy, 31, oy + 1, "carR"); s.rect(2, oy + 2, 37, oy + 2, "carR")
    s.rect(0, oy + 3, 39, oy + 13, "carG2"); s.rect(1, oy + 3, 38, oy + 12, "carG")
    for (x, y) in [(0, oy + 3), (39, oy + 3), (0, oy + 13), (39, oy + 13)]: s.px[x, y] = (0, 0, 0, 0)
    for i in range(9):
        wx = 3 + i * 4
        s.rect(wx, oy + 5, wx + 2, oy + 7, "carW"); s.p(wx + 1, oy + 4, "carW")
    s.hline(1, 38, oy + 8, "cream"); s.rect(0, oy + 12, 39, oy + 13, "red")
    s.p(39, oy + 10, "head")
    s.hline(3, 12, oy + 14, "tire"); s.hline(27, 36, oy + 14, "tire")
    for x in (5, 10, 29, 34): s.p(x, oy + 15, "tire")
    return s.im



# Hand-drawn 5x7 digits (the font's 5 reads as an S and its 7 as a 1 at this size).
DIGITS = {
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": ["..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."],
    "°": [".#.", "#.#", ".#."],
}
GLYPH_TOP = 4          # where the font's cap height starts when drawn at y=0 (size 11)


_GLYPHS = {}
SPACE_W, GAP = 3, 1


def glyph(ch, size=11):
    """Bitmap for one character: the font rendered with no smoothing, trimmed to its
    exact ink width (digits use the hand-drawn set). Returns (width, [(x, y), ...])."""
    if ch in _GLYPHS: return _GLYPHS[ch]
    if ch in DIGITS:
        rows = DIGITS[ch]
        g = (len(rows[0]), [(x, GLYPH_TOP + y) for y, r in enumerate(rows) for x, c in enumerate(r) if c == "#"])
    elif ch == " ":
        g = (SPACE_W, [])
    else:
        im = Image.new("1", (24, 20), 0); d = ImageDraw.Draw(im); d.fontmode = "1"
        d.text((4, 0), ch, font=ImageFont.truetype(FONT, size), fill=1)
        bb = im.getbbox()
        if not bb: g = (SPACE_W, [])
        else:
            x0, x1 = bb[0], bb[2]
            g = (x1 - x0, [(x - x0, y) for y in range(20) for x in range(x0, x1) if im.getpixel((x, y))])
    _GLYPHS[ch] = g
    return g


def text_width(s, size=11):
    return sum(glyph(ch)[0] for ch in s) + GAP * max(0, len(s) - 1)


def draw_text(img, x, y, s, fill, size=11):
    """True bitmap text: whole-pixel glyph widths and an even 1 px gap between letters."""
    px = img.load(); x = round(x)
    for ch in s:
        w, pts = glyph(ch)
        for gx, gy in pts:
            X, Y = x + gx, y + gy
            if 0 <= X < img.width and 0 <= Y < img.height: px[X, Y] = fill
        x += w + GAP


def ui_layer(pal, status, message):
    c = Canvas(pal)
    c.rect(0, 0, W - 1, BAR - 2, "barBg"); c.hline(0, W - 1, BAR - 1, "rule")
    f = ImageFont.truetype(FONT, 11)
    w = max(int(text_width(l)) for l in message) + 10; h = 9 * len(message) + 6
    x0, y0 = BOX_RECT[0], BOX_RECT[1]; x1, y1 = x0 + w, y0 + h
    c.rect(x0, y0, x1, y1, "boxBg")
    for a in [(x0, x1, y0), (x0, x1, y1)]: c.hline(*a, "boxEdge")
    c.vline(x0, y0, y1, "boxEdge"); c.vline(x1, y0, y1, "boxEdge")
    c.hline(x0 + 1, x1 - 1, y0 + 1, "boxHi"); c.vline(x0 + 1, y0 + 1, y1 - 1, "boxHi")
    c.hline(x0 + 1, x1 - 1, y1 - 1, "boxSh"); c.vline(x1 - 1, y0 + 1, y1 - 1, "boxSh")
    ink = (*vga(UI["barTx"]), 255)
    draw_text(c.im, 3, -1, status[0], ink)
    draw_text(c.im, W - 3 - text_width(status[1]), -1, status[1], ink)
    for i, l in enumerate(message): draw_text(c.im, x0 + 5, y0 + 1 + 9 * i, l, ink)
    return c.im


# ---------------------------------------------------------------- scenes
def palette_for(cond):
    if cond["tod"] == "night": return NIGHT
    if cond["sky"] in ("rain", "cloudy", "fog"): return OVERCAST
    return HOT if cond.get("hot") else DAY


def render(cond, status, message):
    """cond: tod 'day'|'night', sky 'clear'|'partly'|'cloudy'|'rain'|'fog', moon 0..1, hot bool."""
    night, kind = cond["tod"] == "night", cond["sky"]
    pal = palette_for(cond)
    base = Canvas(pal)
    sky(base, kind)
    if night and kind in ("clear", "partly"): moon(base, cond.get("moon", .3))
    if not night and kind in ("clear", "partly"): sun(base)
    ckey = {"clear": "clear_night" if night else "clear_day", "partly": "partly", "cloudy": "cloudy",
            "rain": "rain", "fog": "cloudy"}[kind]
    clouds(base, ckey, density=26 if kind in ("cloudy", "fog") else 22)
    buildings(base, night)
    fog = fog_layer(pal) if kind == "fog" else None
    ui = ui_layer(pal, status, message)
    car = streetcar(pal)
    star_list = stars() if night and kind in ("clear", "partly") else []
    rnd = random.Random(11)
    drops = [(rnd.randint(0, W + 30), rnd.randint(BAR, BAR + 5), rnd.randint(0, 14)) for _ in range(70)] if kind == "rain" else []
    wet = kind in ("rain", "fog") or night

    frames = []
    for t in range(FRAMES):
        c = Canvas(pal); c.im = base.im.copy(); c.px = c.im.load()
        for i, (x, y, ph) in enumerate(star_list):            # palette-cycled twinkle
            c.p(x, y, ["star0", "star0", "star1", "star2", "star1", "star0"][(t // 5 + ph) % 6])
        if night:                                                # Superdome lights + lamp flicker
            for x in range(157, 200): c.p(x, 67, ["led0", "led1", "led2"][(x + t) % 3])
            c.rect(107, 59, 109, 62, "glass" if t % 6 else "win")
        if wet:                                                  # reflections on the wet street
            for i, rx in enumerate(REFLECT_X if night else REFLECT_X[::2]):
                ln = 7 + (i % 3) * 2
                for k, y in enumerate(range(GROUND + 4, GROUND + 4 + ln)):
                    if (k + t // 2 + i) % 2 == 0 and y not in (89, 92):
                        c.p(rx + ((k // 2 + t // 3 + i) % 3 == 0), y, "refl1" if k < ln // 2 else "refl0")
        cx = -40 + (t * 2) % (W + 40)                            # streetcar sprite, 2 px per frame
        c.im.alpha_composite(car, (max(cx, 0), 66), (max(0, -cx), 0))
        if fog is not None:                                      # fog bank breathes: shifts 2 px every 25 frames
            c.im.alpha_composite(fog.transform(fog.size, Image.AFFINE, (1, 0, -((t // 25) % 2) * 2, 0, 1, 0)))
        for x0, y0, ph in drops:
            s = (t + ph) % 15; x, y = x0 - s * 2, y0 + s * 6
            if y >= GROUND + 3: c.p(x, GROUND + 3 + (x % 5), "splash"); continue
            c.p(x, y, "rainH"); c.p(x, y + 1, "rain"); c.p(x - 1, y + 2, "rain")
        c.im.alpha_composite(ui)
        frames.append(c.im.convert("RGB"))
    return frames


def save_gif(frames, out):
    big = [f.resize((W * SCALE, H * SCALE), Image.NEAREST) for f in frames]
    colors = sorted({col for f in frames for _, col in f.getcolors(1 << 16)})
    assert len(colors) <= 255, f"{len(colors)} colors - over the GIF/VGA limit"
    flat = [v for col in colors for v in col] + [0, 0, 0] * (256 - len(colors))
    lut = {col: i for i, col in enumerate(colors)}; TR = 255

    def to_p(im):
        p = Image.new("P", im.size); p.putpalette(flat); p.putdata([lut[c] for c in _flat(im)]); return p
    out_frames, prev = [], None
    for im in big:
        p = to_p(im)
        if prev is None:
            out_frames.append(p)
        else:   # unchanged pixels become transparent, so each frame stores only what moved
            a, b = _flat(prev), _flat(p)
            q = Image.new("P", im.size); q.putpalette(flat); q.putdata([TR if x == y else y for x, y in zip(a, b)])
            q.info["transparency"] = TR; out_frames.append(q)
        prev = p
    out_frames[0].save(out, save_all=True, append_images=out_frames[1:], duration=FRAME_MS, loop=0,
                       disposal=1, optimize=False, transparency=TR)
    return len(colors)
