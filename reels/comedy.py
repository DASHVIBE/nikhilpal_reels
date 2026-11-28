"""Comedy format: Chintu, Mama and Pinki in two looks, drawn fresh every frame (they are only lines and flat shapes).

    style "doodle": grey paper, white big heads, stick bodies, ink lines only (props drawn as ink doodles)
    style "desi":   the same characters with skin, kurtas and a coloured Indian background

Scenes: gali (street), ghar (living room), dukaan (kirana shop). Every shot has two characters facing each other;
the camera cuts to whoever speaks. Mood -> pose: neutral talk, happy laugh, angry point, shock hands up, sad facepalm.
"""
import math, random
import numpy as np
from PIL import Image, ImageDraw
from .config import W, H, SS
from .util import clamp, lerp, ease_out, ease_io, blink

INK = (30, 24, 34)
PAPER = (178, 186, 170)
BGINK = (120, 128, 116)           # doodle backgrounds: soft grey lines so the characters stay in front
FOOT = 1450                       # ground line for the feet
SPOTS = (310, 770)                # x of the left / right character
ORDER = ("T", "M", "Y")           # who stands on the left when two of them share a shot

LOOK = {   # per character: head shape, size, skin, clothes (desi look)
    "T": dict(head="bean", rx=80, ry=104, skin=(232, 178, 130), hair=(34, 28, 36), kurta=(30, 150, 150), trim=(250, 220, 120),
              legs=(246, 240, 226), shoes=(120, 70, 40)),
    "M": dict(head="round", rx=98, ry=90, skin=(204, 144, 100), hair=(70, 66, 70), kurta=(236, 186, 60), trim=(150, 90, 50),
              legs=(246, 240, 226), shoes=(90, 56, 36), vest=(130, 74, 44)),
    "Y": dict(head="oval", rx=84, ry=94, skin=(226, 168, 122), hair=(34, 28, 36), kurta=(232, 90, 140), trim=(255, 214, 90),
              legs=(250, 226, 120), shoes=(200, 60, 80), dupatta=(255, 196, 80)),
}


# ---------------------------------------------------------------- drawing helpers (units = 1080x1920 frame)
class Ink:
    """Drawing in frame units. col = default line colour (the doodle background uses a soft grey ink)."""
    def __init__(self, img, col=INK): self.d = ImageDraw.Draw(img, "RGBA"); self.c = col
    def ell(self, cx, cy, rx, ry, fill=None, w=0, col=None):
        col = col or self.c
        if rx <= 0.3 or ry <= 0.3: return
        self.d.ellipse([(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS], fill=fill,
                       outline=col if w else None, width=int(w * SS) if w else 0)
    def poly(self, pts, fill=None, w=0, col=None):
        P = [(x * SS, y * SS) for x, y in pts]
        if fill: self.d.polygon(P, fill=fill)
        if w: self.line(list(pts) + [pts[0]], w, col)
    def line(self, pts, w, col=None):
        col = col or self.c
        P = [(x * SS, y * SS) for x, y in pts]
        self.d.line(P, fill=col, width=int(w * SS), joint="curve")
        for x, y in (pts[0], pts[-1]): self.ell(x, y, w / 2, w / 2, fill=col)
    def arc(self, cx, cy, rx, ry, a0, a1, w, col=None):
        col = col or self.c
        self.d.arc([(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS], a0, a1, fill=col, width=int(w * SS))
    def chord(self, cx, cy, rx, ry, a0, a1, fill, w=0):
        self.d.chord([(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS], a0, a1, fill=fill,
                     outline=self.c if w else None, width=int(w * SS) if w else 0)
    def rect(self, x0, y0, x1, y1, fill=None, w=0):
        self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill, w)


def bez(p0, p1, p2, n=16):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in [i / n for i in range(n + 1)]]


def limb(a, b, bend):
    """noodle limb from a to b; the middle is pushed sideways by bend"""
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy) or 1
    return bez(a, (mx - dy / L * bend, my + dx / L * bend), b)


def fillc(style, col, paper=(255, 255, 255)):
    return col if style == "desi" else paper


# ---------------------------------------------------------------- face
def face(k, style, who, cx, cy, s, f, mood, talk, bl, look):
    """Head centred at (cx, cy), facing f (+1 right / -1 left)."""
    L = LOOK[who]; rx, ry = L["rx"] * s, L["ry"] * s
    skin = fillc(style, L["skin"])
    if who == "Y":                                     # plaits behind the head
        for side in (-1, 1):
            for j in range(4):
                k.ell(cx + side * (rx + (2 + j * 3) * s), cy + (8 + j * 32) * s, 17 * s, 19 * s, fillc(style, L["hair"]), 5)
    if style == "desi" and mood == "angry": skin = tuple(int(lerp(c, r, 0.35)) for c, r in zip(skin, (230, 60, 50)))
    k.ell(cx, cy, rx, ry, skin, 6)
    if who == "T":                                     # quiff
        if style == "desi":
            k.poly([(cx - rx, cy - 34 * s), (cx - rx * 0.8, cy - ry * 1.02), (cx + 6 * s, cy - ry * 1.32),
                    (cx + rx * 0.9, cy - ry * 0.98), (cx + rx, cy - 30 * s), (cx + 18 * s, cy - ry * 0.74)], L["hair"], 5)
        else:
            k.line(bez((cx - 50 * s, cy - ry * 0.88), (cx + 6 * s, cy - ry * 1.55), (cx + 52 * s, cy - ry * 0.92)), 6)
            k.line(bez((cx - 18 * s, cy - ry * 0.96), (cx + 34 * s, cy - ry * 1.45), (cx + 64 * s, cy - ry * 0.8)), 6)
    elif who == "M":                                   # bald with side tufts and round glasses
        for side in (-1, 1):
            k.ell(cx + side * rx * 0.94, cy - 6 * s, 20 * s, 30 * s, fillc(style, L["hair"], (255, 255, 255)), 5)
        k.arc(cx - 30 * s, cy - ry * 0.62, 26 * s, 10 * s, 200, 340, 4)
    else:                                              # Pinki: centre parting + bindi
        k.chord(cx, cy - 8 * s, rx * 1.02, ry * 0.98, 180, 360, fillc(style, L["hair"]), 5)
        k.line([(cx + f * 6 * s, cy - ry * 0.98), (cx + f * 2 * s, cy - ry * 0.5)], 4, (255, 255, 255) if style == "desi" else INK)
        k.ell(cx + f * 10 * s, cy - 40 * s, 6 * s, 6 * s, (220, 40, 60) if style == "desi" else INK)

    ex, ey = 28 * s, cy - 16 * s
    lx = (look * 9 + f * 4) * s
    for side in (-1, 1):
        x = cx + side * ex + f * 10 * s
        if mood == "happy" and talk < 0.1:              # laughing: ^ ^
            k.arc(x, ey + 6 * s, 18 * s, 16 * s, 200, 340, 7)
        else:
            big = 1.25 if mood == "shock" else 1.0
            k.ell(x, ey, 22 * s * big, 27 * s * big, (255, 255, 255), 5)
            if bl < 0.5:
                k.line([(x - 20 * s, ey), (x + 20 * s, ey)], 6)
            else:
                pr = (6 if mood == "shock" else 9) * s
                k.ell(x + lx, ey + 4 * s, pr, pr * 1.15, INK)
                if mood in ("neutral", "sad") and who == "T":            # Chintu's sly half lids
                    k.chord(x, ey, 22 * s, 27 * s, 180, 360, skin, 5)
                elif mood == "sad":
                    k.chord(x, ey, 22 * s, 27 * s, 200, 340, skin, 0)
        by = ey - 40 * s - (12 * s if mood == "shock" else 0)
        tilt = {"angry": -1, "sad": 1}.get(mood, 0) * side * 10 * s      # angry: inner ends down
        k.line([(x - 18 * s, by + tilt), (x + 18 * s, by - tilt)], 7)
    if who == "M":                                     # glasses over the eyes
        for side in (-1, 1): k.ell(cx + side * ex + f * 10 * s, ey, 34 * s, 32 * s, None, 4)
        k.line([(cx + f * 10 * s - 6 * s, ey), (cx + f * 10 * s + 6 * s, ey)], 4)
    nx = cx + f * 32 * s                                # big round nose
    k.ell(nx, cy + 18 * s, 30 * s, 24 * s, fillc(style, tuple(int(c * 0.92) for c in L["skin"])), 5)
    my = cy + 62 * s; mx = cx + f * 14 * s
    if talk > 0.08 and mood != "happy":
        k.ell(mx, my, 20 * s, (6 + 22 * talk) * s, (120, 30, 40), 5)
    elif mood == "happy":
        k.chord(mx, my - 10 * s, 36 * s, (26 + 12 * talk) * s, 0, 180, (120, 30, 40), 5)
        k.chord(mx, my - 10 * s, 30 * s, 10 * s, 0, 180, (255, 255, 255))
    elif mood == "shock":
        k.ell(mx, my + 4 * s, 16 * s, 20 * s, (120, 30, 40), 5)
    elif mood in ("angry", "sad"):
        k.arc(mx, my + 16 * s, 26 * s, 16 * s, 200, 340, 6)
    else:
        k.line(bez((mx - 24 * s, my - 4 * s), (mx + 2 * s, my + 16 * s), (mx + 28 * s, my - 10 * s)), 6)
    if who == "M":                                     # moustache
        k.line(bez((cx + f * 8 * s - 52 * s, my - 18 * s), (cx + f * 8 * s, my - 40 * s), (cx + f * 8 * s + 52 * s, my - 18 * s)), 14,
               (60, 50, 50) if style == "desi" else INK)
    if who == "Y":
        for side in (-1, 1): k.ell(cx + side * rx * 0.98, cy + 26 * s, 8 * s, 8 * s, (255, 206, 60) if style == "desi" else (255, 255, 255), 3)


# ---------------------------------------------------------------- body + poses
def hands_for(pose, sh, s, f, t, talk):
    """Target points for the back and front hand."""
    x, y = sh
    if pose == "talk":
        g = math.sin(t * 7) * 30 * min(1, talk * 3)
        return (x - f * 70 * s, y + 160 * s), (x + f * 120 * s, y + 40 * s - g * s)
    if pose == "point":
        return (x - f * 60 * s, y + 170 * s), (x + f * 190 * s, y - 10 * s + 6 * math.sin(t * 12) * s)
    if pose == "shock":
        return (x - f * 110 * s, y - 120 * s), (x + f * 110 * s, y - 130 * s)
    if pose == "laugh":
        return (x - f * 40 * s, y + 180 * s), (x + f * 50 * s, y + 175 * s)
    if pose == "facepalm":
        return (x - f * 60 * s, y + 170 * s), (x + f * 40 * s, y - 150 * s)
    if pose == "shrug":
        return (x - f * 130 * s, y + 20 * s), (x + f * 130 * s, y + 20 * s)
    sw = 6 * math.sin(t * 2.4)
    return (x - f * 72 * s, y + 170 * s + sw * s), (x + f * 72 * s, y + 170 * s - sw * s)


def character(k, style, who, X, t, s, f, mood, talk, look, pose, ts):
    L = LOOK[who]
    bounce = 0.0
    if pose == "laugh": bounce = -abs(math.sin(t * 14)) * 14
    elif pose == "shock": bounce = -40 * math.sin(math.pi * clamp(ts / 0.35)) if ts < 0.35 else 0
    elif talk > 0.1: bounce = -talk * 6
    bounce += 3 * math.sin(t * 2.2 + X)
    Y = FOOT + bounce * s
    hip = (X, Y - 250 * s); neck = (X, Y - 480 * s); sh = (X, neck[1] + 50 * s)
    bh, fh = hands_for(pose, sh, s, f, t, talk)
    # legs
    for side in (-1, 1):
        foot = (X + side * 46 * s, FOOT)
        path = limb((X + side * 16 * s, hip[1] - 4 * s), foot, side * 22 * s)
        if style == "desi":
            k.line(path, 28 * s, INK); k.line(path, 17 * s, L["legs"])
            k.ell(foot[0] + f * 14 * s, foot[1] + 2 * s, 32 * s, 14 * s, L["shoes"], 5)
        else:
            k.line(path, 7)
            k.ell(foot[0] + f * 12 * s, foot[1] + 2 * s, 24 * s, 12 * s, (255, 255, 255), 6)
    def arm(h, bend):
        path = limb(sh, h, bend)
        if style == "desi":
            k.line(path, 28 * s, INK); k.line(path, 18 * s, L["kurta"])
            k.ell(h[0], h[1], 18 * s, 18 * s, L["skin"], 5)
        else:
            k.line(path, 7); k.ell(h[0], h[1], 14 * s, 14 * s, INK)
    arm(bh, -f * 26 * s)
    # torso
    if style == "desi":
        top, bot = neck[1] + 20 * s, hip[1] + 50 * s
        k.poly([(X - 62 * s, top), (X + 62 * s, top), (X + 86 * s, bot), (X - 86 * s, bot)], L["kurta"], 6)
        if who == "M":
            k.poly([(X - 62 * s, top), (X - 14 * s, top), (X - 20 * s, bot - 40 * s), (X - 80 * s, bot - 40 * s)], L["vest"], 5)
            k.poly([(X + 14 * s, top), (X + 62 * s, top), (X + 80 * s, bot - 40 * s), (X + 20 * s, bot - 40 * s)], L["vest"], 5)
        if who == "Y":
            k.line(bez((X - 60 * s, top + 10 * s), (X, top + 90 * s), (X + 64 * s, top + 4 * s)), 20 * s, INK)
            k.line(bez((X - 60 * s, top + 10 * s), (X, top + 90 * s), (X + 64 * s, top + 4 * s)), 12 * s, L["dupatta"])
        for j in range(3): k.ell(X + f * 6 * s, top + (34 + 34 * j) * s, 5 * s, 5 * s, L["trim"], 2)
    else:
        k.line([neck, (X, neck[1] + 30 * s)], 7)
        k.ell(X, (neck[1] + 20 * s + hip[1]) / 2 + 4 * s, 34 * s, (hip[1] - neck[1] - 20 * s) / 2 + 4 * s, None, 7)
    head = (X, neck[1] - L["ry"] * s * 0.92)
    if pose == "facepalm":
        face(k, style, who, *head, s, f, "sad", talk, 1.0, look); arm(fh, f * 30 * s)
    else:
        arm(fh, f * 26 * s)
        face(k, style, who, *head, s, f, mood, talk, blink(t + X * 0.01), look)
    # little comic marks
    hx, hy = head; top = hy - L["ry"] * s
    if mood == "angry":
        for j, a in enumerate((-0.5, 0, 0.5)):
            u = (t * 1.6 + j * 0.33) % 1
            k.ell(hx + (a * 90 + 10 * math.sin(t * 5 + j)) * s, top - (20 + 90 * u) * s, (10 + 14 * u) * s, (8 + 10 * u) * s,
                  (255, 255, 255, int(220 * (1 - u))), 3, (INK[0], INK[1], INK[2], int(255 * (1 - u))))
    elif mood == "shock":
        for a in (-40, -15, 15, 40):
            r = math.radians(a - 90); r0, r1 = L["ry"] * s * 1.25, L["ry"] * s * 1.6
            k.line([(hx + math.cos(r) * r0, hy + math.sin(r) * r0), (hx + math.cos(r) * r1, hy + math.sin(r) * r1)], 6)
    elif mood == "sad":
        u = (t % 1.4) / 1.4
        k.ell(hx - f * L["rx"] * s * 0.8, hy - 30 * s + u * 50 * s, 9 * s, 13 * s, (120, 190, 250, int(240 * (1 - u))), 0)
    return head


# ---------------------------------------------------------------- backgrounds (same layout in both looks)
def paper(seed=3):
    rng = np.random.default_rng(seed)
    a = np.empty((H * SS, W * SS, 3), np.float32); a[:] = PAPER
    a += rng.normal(0, 6, (H * SS, W * SS, 1))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def gradient(top, bot, y0, y1, img):
    d = ImageDraw.Draw(img)
    for y in range(int(y0 * SS), int(y1 * SS)):
        u = (y - y0 * SS) / max(1, (y1 - y0) * SS)
        d.line([(0, y), (W * SS, y)], fill=tuple(int(a + (b - a) * u) for a, b in zip(top, bot)))


def bg(scene, style):
    desi = style == "desi"
    img = Image.new("RGB", (W * SS, H * SS), PAPER) if desi else paper()
    k = Ink(img, INK if desi else BGINK); c = lambda col: col if desi else None
    if scene == "gali":
        if desi: gradient((120, 200, 236), (250, 224, 176), 0, 1180, img)
        k.ell(860, 260, 80, 80, c((255, 214, 90)), 0 if desi else 5)
        houses = [(-40, 300, 560, (236, 120, 90)), (240, 280, 650, (110, 180, 160)), (500, 300, 520, (246, 196, 80)), (780, 340, 610, (180, 120, 190))]
        for x, w, h, col in houses:
            y = 1180 - h
            k.rect(x, y, x + w, 1180, c(col) or PAPER, 5)
            k.poly([(x - 10, y), (x + w + 10, y), (x + w - 10, y - 30), (x + 10, y - 30)], c((90, 60, 60)) or PAPER, 5)
            for wy in range(y + 60, 1110, 150):
                for wx in (x + 50, x + w - 110): k.rect(wx, wy, wx + 60, wy + 80, c((60, 50, 80)) or PAPER, 4)
        k.line([(0, 420), (1080, 470)], 3)
        k.rect(0, 1180, W, H, c((206, 186, 160)), 0)
        k.line([(0, 1180), (W, 1180)], 5)
        for i in range(10): k.line([(i * 110 + 20, 1300 + (i % 3) * 110), (i * 110 + 80, 1300 + (i % 3) * 110)], 4, (180, 160, 140) if desi else BGINK)
    elif scene == "ghar":
        if desi: k.rect(0, 0, W, 1180, (246, 214, 170))
        k.rect(0, 1180, W, H, c((178, 120, 86)), 0); k.line([(0, 1180), (W, 1180)], 5)
        k.rect(90, 330, 430, 720, c((150, 210, 236)) or PAPER, 6)                # window
        k.line([(260, 330), (260, 720)], 6); k.line([(90, 525), (430, 525)], 6)
        k.rect(70, 300, 450, 340, c((200, 80, 70)) or PAPER, 5)                 # curtain rod
        k.rect(700, 360, 920, 640, c((40, 40, 50)) or PAPER, 6)                 # TV
        k.rect(760, 640, 860, 700, c((120, 80, 60)) or PAPER, 5)
        k.rect(560, 760, 1080, 1100, c((120, 70, 130)) or PAPER, 6)             # sofa
        k.rect(560, 700, 1080, 790, c((150, 90, 160)) or PAPER, 6)
        k.rect(600, 300, 660, 380, c((255, 255, 255)) or PAPER, 4)              # calendar
        k.line([(610, 320), (650, 320)], 4, (220, 60, 60) if desi else BGINK)
    else:   # dukaan
        if desi: k.rect(0, 0, W, 1180, (250, 236, 200))
        k.rect(0, 1180, W, H, c((190, 170, 140)), 0); k.line([(0, 1180), (W, 1180)], 5)
        k.rect(60, 120, 1020, 250, c((220, 60, 60)) or PAPER, 6)                # signboard
        for y in (420, 620, 820):                                               # shelves with jars
            k.rect(60, y, 1020, y + 22, c((140, 90, 50)) or PAPER, 5)
            for i in range(9):
                x = 100 + i * 105; h = 90 + (i * 37) % 50
                k.rect(x, y - h, x + 70, y, c([(240, 180, 60), (120, 190, 110), (230, 110, 90), (150, 160, 230)][i % 4]) or PAPER, 4)
                k.rect(x + 6, y - h - 14, x + 64, y - h, c((200, 60, 60)) or PAPER, 4)
        k.rect(0, 960, W, 1180, c((160, 104, 60)) or PAPER, 6)                  # counter
    return img


def sign_text(img, scene):
    if scene != "dukaan": return
    from PIL import ImageFont
    from .config import FONT_TITLE
    d = ImageDraw.Draw(img); f = ImageFont.truetype(FONT_TITLE, 90 * SS)
    txt = "CHINTU KIRANA STORE"; tw = d.textlength(txt, font=f)
    d.text(((W * SS - tw) / 2, 140 * SS), txt, font=f, fill=(255, 240, 200), stroke_width=4 * SS, stroke_fill=INK)


BG = {}


def background(scene, style):
    key = (scene, style)
    if key not in BG:
        img = bg(scene, style); sign_text(img, scene); BG[key] = img
    return BG[key]


def animate_bg(k, scene, style, t):
    """small moving things: a crow on the wire, the ceiling fan, a swinging bulb"""
    desi = style == "desi"
    if scene == "gali":
        bob = 4 * math.sin(t * 3)
        k.ell(640, 430 + bob, 28, 18, (40, 40, 50) if desi else (255, 255, 255), 4)
        k.ell(660, 418 + bob, 14, 13, (40, 40, 50) if desi else (255, 255, 255), 4)
        k.poly([(672, 414 + bob), (700, 420 + bob), (672, 426 + bob)], (240, 180, 40) if desi else INK)
    elif scene == "ghar":
        k.line([(540, 0), (540, 120)], 6)
        k.ell(540, 130, 30, 18, (90, 90, 100) if desi else (255, 255, 255), 5)
        for j in range(3):
            a = t * 9 + j * 2 * math.pi / 3
            k.ell(540 + math.cos(a) * 120, 130 + math.sin(a) * 16, 110 * abs(math.cos(a)) + 14, 10, (140, 140, 150) if desi else (255, 255, 255), 4)
    else:
        a = 0.25 * math.sin(t * 1.8); x = 540 + math.sin(a) * 140; y = 260 + math.cos(a) * 140
        k.line([(540, 250), (x, y + 140)], 4)
        k.ell(x, y + 160, 22, 26, (255, 240, 150) if desi else (255, 255, 255), 4)


# ---------------------------------------------------------------- the shot
REACT_POSE = {"neutral": "stand", "happy": "laugh", "angry": "point", "shock": "shock", "sad": "facepalm"}
SPEAK_POSE = {"neutral": "talk", "happy": "laugh", "angry": "point", "shock": "shock", "sad": "facepalm"}


def shot_comedy(t, s, talk_of):
    """talk_of(spk) -> mouth openness now. Returns (image at 2x, camera)."""
    style, scene = s.get("style", "desi"), s["kind"]
    img = background(scene, style).copy(); k = Ink(img)
    animate_bg(Ink(img, INK if style == "desi" else BGINK), scene, style, t)
    cast = s["cast"]; spots = dict(zip(cast, SPOTS if len(cast) == 2 else (540,)))
    speaker = s.get("focus")
    for who in cast:
        X = spots[who]; f = 1 if X < 540 else -1
        if len(cast) == 1: f = 1
        tk = talk_of(who)
        if who == speaker:
            mood = s["mood"]; pose = SPEAK_POSE[mood] if tk > 0.05 or mood != "neutral" else "stand"
        else:
            mood = s.get("react", "neutral"); pose = REACT_POSE[mood]
        if s.get("enter") == who:                    # walks in from the side during the first second
            X += (1 - ease_out(t / 1.0)) * f * -700
        character(k, style, who, X, t, 1.3, f, mood, tk, 0.6 * f, pose, t)
    cam = s.get("cam", "wide"); e = ease_io(t / max(0.1, s["dur"]))
    if cam == "wide" or cam not in spots:
        return img, dict(zoom=lerp(1.0, 1.05, e), cx=540, cy=980)
    return img, dict(zoom=1.42 * lerp(1.0, 1.05, e), cx=spots[cam], cy=880)
