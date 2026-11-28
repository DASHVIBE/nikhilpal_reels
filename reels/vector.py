"""Katha characters in the flat vector look (style A): tall side-profile figures, flat colours, thin ink outline.

Same call as the old characters.char(), plus `face` (+1 looks right, -1 looks left; default from look[0]):
    char(frame, pen, who, X, Y, sc, t, pose, mood, talk, look, walking, sit, face)
who: K Shri Krishna, A Arjun, P devotee (older man), R Raja, C Chatur, G guard.
pose: stand, talk, bless, point, think, wipe, namaste.  mood: smile/neutral, happy, sad, angry, shock, curious.
Drawn fresh every frame (a few dozen flat shapes), so no sprite cache is needed.
"""
import math
from PIL import ImageDraw
from .config import SS, BLINK_OFF
from .util import clamp, blink

INK = (44, 28, 46)
GOLD, GOLD_D = (246, 192, 56), (206, 146, 30)
LOOK = {
    "K": dict(skin=(78, 128, 214), hair=(24, 20, 40), top=None, low=(246, 176, 40), fold=(255, 206, 90), sash=(40, 172, 152), feet=(150, 90, 40)),
    "A": dict(skin=(226, 170, 126), hair=(34, 24, 28), top=(24, 118, 126), low=(246, 228, 190), fold=(255, 242, 214), sash=(246, 192, 56), feet=(120, 74, 40)),
    "P": dict(skin=(184, 128, 88), hair=(40, 30, 32), top=(236, 206, 150), low=(244, 234, 210), fold=(255, 248, 230), sash=(226, 120, 48), feet=(120, 80, 50)),
    "R": dict(skin=(226, 172, 128), hair=(30, 22, 26), top=(98, 40, 140), low=(98, 40, 140), fold=(124, 64, 168), sash=GOLD, feet=(206, 156, 52)),
    "C": dict(skin=(204, 148, 104), hair=(30, 22, 26), top=(52, 140, 96), low=(244, 232, 204), fold=(255, 244, 222), sash=(246, 196, 40), feet=(110, 70, 42)),
    "G": dict(skin=(196, 140, 98), hair=(30, 22, 26), top=(176, 182, 196), low=(36, 56, 108), fold=(48, 70, 128), sash=(200, 50, 50), feet=(78, 54, 36)),
}


def shade(c, f=0.82): return tuple(int(v * f) for v in c[:3])


class Fig:
    """Local units (facing right, y up is negative) -> frame pixels at 2x."""
    def __init__(self, frame, X, Y, sc, f):
        self.d = ImageDraw.Draw(frame, "RGBA"); self.X, self.Y, self.s, self.f = X, Y, sc, f
        self.lw = max(2, int(3.2 * sc * SS))
    def P(self, x, y): return ((self.X + self.f * x * self.s) * SS, (self.Y + y * self.s) * SS)
    def poly(self, pts, fill, ink=True):
        P = [self.P(x, y) for x, y in pts]
        self.d.polygon(P, fill=fill)
        if ink: self.d.line(P + [P[0]], fill=INK, width=self.lw, joint="curve")
    def ell(self, x, y, rx, ry, fill, ink=True):
        cx, cy = self.P(x, y); rx, ry = rx * self.s * SS, ry * self.s * SS
        self.d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=fill, outline=INK if ink else None, width=self.lw if ink else 0)
    def limb(self, pts, w, fill):
        """capsule along pts, outlined"""
        P = [self.P(x, y) for x, y in pts]; W = w * self.s * SS
        self.d.line(P, fill=INK, width=int(W + 2 * self.lw), joint="curve")
        for p in (P[0], P[-1]): self.d.ellipse([p[0] - W / 2 - self.lw, p[1] - W / 2 - self.lw, p[0] + W / 2 + self.lw, p[1] + W / 2 + self.lw], fill=INK)
        self.d.line(P, fill=fill, width=int(W), joint="curve")
        for p in (P[0], P[-1]): self.d.ellipse([p[0] - W / 2, p[1] - W / 2, p[0] + W / 2, p[1] + W / 2], fill=fill)
    def line(self, pts, w, col=INK):
        self.d.line([self.P(x, y) for x, y in pts], fill=col, width=max(1, int(w * self.s * SS)), joint="curve")
    def arc(self, x, y, rx, ry, a0, a1, w, col=INK):
        cx, cy = self.P(x, y); rx, ry = rx * self.s * SS, ry * self.s * SS
        if self.f < 0: a0, a1 = 180 - a1, 180 - a0
        self.d.arc([cx - rx, cy - ry, cx + rx, cy + ry], a0, a1, fill=col, width=max(1, int(w * self.s * SS)))


def vec(a, L):
    """angle in degrees: 0 = straight down, 90 = forward, 180 = straight up"""
    r = math.radians(a); return math.sin(r) * L, math.cos(r) * L


ARM = {   # (upper arm angle, forearm angle) back arm, front arm
    "stand": ((6, 14), (-4, 8)), "talk": ((6, 14), (28, 92)), "bless": ((6, 14), (36, 152)), "point": ((6, 14), (84, 88)),
    "think": ((6, 14), (18, 160)), "wipe": ((6, 14), (26, 172)), "namaste": ((22, 138), (22, 138)),
}


def head(F, who, L, mood, talk, bl, hy):
    """Profile head centred at (0, hy)."""
    skin = L["skin"]
    if who == "K":                                    # long hair falling behind + halo
        F.ell(-6, hy - 6, 92, 92, None, False); F.arc(-6, hy - 6, 92, 92, 0, 360, 5, GOLD)
        F.poly([(-50, hy - 40), (10, hy - 70), (-20, hy + 40), (-56, hy + 120), (-74, hy + 110), (-64, hy + 20)], L["hair"])
    elif who in ("A", "R", "C", "G"):
        F.poly([(-54, hy - 30), (10, hy - 66), (-10, hy + 40), (-44, hy + 60), (-60, hy + 20)], L["hair"])
    elif who == "P":
        F.poly([(-54, hy - 30), (10, hy - 66), (-10, hy + 30), (-40, hy + 52), (-58, hy + 16)], L["hair"])
    pts = [(56 * math.cos(math.radians(a)), -64 * math.sin(math.radians(a)) + hy) for a in range(260, 59, -10)]
    pts += [(x, y + hy) for x, y in [(42, -44), (52, -22), (54, -8), (56, 4), (72, 24), (58, 30), (58, 40), (54, 46),
                                     (56, 52), (46, 64), (22, 70), (-6, 62)]]
    F.poly(pts, skin)
    F.ell(-6, hy + 6, 11, 15, shade(skin, 0.9))       # ear
    if who in ("K", "C", "P", "R"): F.ell(-6, hy + 24, 5, 5, GOLD, False)
    # eye + brow
    ex, ey = 34, hy - 4
    if mood == "happy" and talk < 0.05: F.arc(ex, ey + 2, 9, 8, 200, 340, 3.5)
    elif bl < 0.5: F.line([(ex - 9, ey), (ex + 7, ey)], 3)
    elif mood == "shock":
        F.ell(ex, ey, 10, 12, (255, 255, 255)); F.ell(ex + 3, ey, 3.5, 4.5, INK, False)
    else:
        F.ell(ex, ey, 7, 9, (255, 255, 255), False); F.ell(ex + 3, ey + 1, 5, 7, INK, False); F.ell(ex + 4, ey - 2, 1.8, 1.8, (255, 255, 255), False)
    tilt = {"angry": 7, "sad": -7, "curious": -4, "shock": -2}.get(mood, 0)
    by = ey - 20 - (6 if mood == "shock" else 0)
    F.line([(ex - 12, by - tilt), (ex + 12, by + tilt)], 4.5, L["hair"])
    # mouth
    mx, my = 50, hy + 46
    if talk > 0.06: F.ell(mx, my, 6, 2 + 9 * talk, (110, 30, 40), False)
    elif mood == "shock": F.ell(mx, my, 6, 8, (110, 30, 40), False)
    elif mood == "sad": F.arc(mx - 2, my + 8, 9, 6, 200, 330, 3)
    elif mood == "angry": F.line([(mx - 10, my + 2), (mx + 6, my)], 3)
    else: F.arc(mx - 4, my - 6, 11, 8, 20, 120, 3)
    if who in ("R", "G"):                              # moustache
        F.poly([(60, hy + 34), (40, hy + 36), (26, hy + 46), (44, hy + 42), (58, hy + 42)], L["hair"], False)
    if who == "P":                                     # short dark beard
        F.poly([(-4, hy + 50), (20, hy + 64), (54, hy + 58), (52, hy + 76), (26, hy + 92), (4, hy + 80)], L["hair"])
    # headgear
    if who == "K":
        F.poly([(-46, hy - 42), (40, hy - 54), (34, hy - 92), (14, hy - 76), (0, hy - 108), (-14, hy - 80), (-34, hy - 96)], GOLD)
        F.ell(-2, hy - 62, 7, 7, (220, 40, 60))
        F.line([(-24, hy - 92), (-60, hy - 178)], 4, (60, 120, 60))          # peacock feather
        F.ell(-60, hy - 190, 18, 28, (40, 150, 110)); F.ell(-60, hy - 188, 10, 15, (40, 80, 190), False); F.ell(-60, hy - 186, 5, 7, INK, False)
    elif who == "A":
        F.poly([(-44, hy - 44), (36, hy - 54), (30, hy - 80), (0, hy - 92), (-34, hy - 80)], GOLD)
        F.ell(0, hy - 66, 6, 6, (40, 172, 152))
    elif who == "R":
        F.poly([(-48, hy - 40), (42, hy - 52), (38, hy - 104), (20, hy - 84), (4, hy - 130), (-12, hy - 86), (-36, hy - 110)], GOLD)
        F.ell(2, hy - 68, 9, 9, (220, 40, 60))
    elif who == "C":
        F.poly([(-58, hy - 26), (48, hy - 46), (46, hy - 70), (10, hy - 96), (-40, hy - 84), (-62, hy - 52)], (240, 120, 40))
        for k in range(3): F.line([(-50 + k * 6, hy - 40 - k * 16), (40 - k * 4, hy - 52 - k * 14)], 3, (250, 200, 60))
    elif who == "G":
        F.poly([(-56, hy - 20), (54, hy - 34), (44, hy - 76), (0, hy - 96), (-44, hy - 76)], (150, 156, 170))
        F.line([(0, hy - 96), (6, hy - 120)], 6, (200, 50, 50))
    elif who == "P":
        F.ell(-30, hy - 64, 9, 9, L["hair"])          # shikha knot


def char(frame, pen, who, X, Y, sc, t, pose="stand", mood="smile", talk=0.0, look=(0, 0), walking=False, sit=False, face=None):
    L = LOOK[who]
    f = face if face is not None else (1 if look[0] >= 0 else -1)
    ph = t * 6.5 if walking else 0.0
    bob = -abs(math.sin(ph)) * 8 if walking else 2.5 * math.sin(t * 1.9 + X * 0.01)
    if mood == "sad" and talk < 0.05 and not walking: bob += math.sin(t * 16) * 1.5
    F = Fig(frame, X, Y + bob * sc, sc, f)
    up = 230 if sit else 0                            # sitting: the upper body is lower
    feet = L["feet"]

    # ---------- back items (cape, quiver, spear)
    if who == "R": F.poly([(-30, -640 + up), (-96, -40), (-30, -40)], (60, 24, 96))
    if who == "A":
        F.poly([(-70, -660), (-40, -680), (-20, -440), (-50, -430)], (130, 78, 36))
        for k in range(3): F.poly([(-62 + k * 9, -664 - k * 6), (-50 + k * 9, -700 - k * 6), (-44 + k * 9, -668 - k * 6)], (220, 60, 60), False)

    # ---------- legs + lower garment
    if sit:
        F.poly([(-80, -6), (-74, -160), (40, -176), (120, -120), (150, -40), (140, -6)], L["low"])       # folded legs
        F.poly([(-20, -120), (110, -110), (130, -60), (0, -70)], L["fold"], False)
        F.poly([(96, -36), (150, -40), (154, -10), (96, -6)], L["skin"])                                 # front foot
        F.line([(-74, -150), (40, -166)], 5, L["sash"])
    else:
        sw = 0.42 * math.sin(ph) if walking else 0.0
        hip = -400
        for side, a, col in ((-1, -sw, shade(L["skin"])), (1, sw, L["skin"])):
            fx, fy = vec(math.degrees(a), 380)
            ank = (side * 6 + fx, hip + fy - 14)
            F.limb([(side * 8, hip), ank], 30, col if who != "G" else (shade(L["low"]) if side < 0 else L["low"]))
            F.poly([(ank[0] - 14, -2), (ank[0] + 40, -2), (ank[0] + 36, -18), (ank[0] - 8, -22)], feet if side > 0 else shade(feet))
        if who == "R":
            F.poly([(-50, -430), (46, -430), (70, -30), (-66, -30)], L["low"])
            F.poly([(-66, -46), (70, -46), (70, -30), (-66, -30)], GOLD)
        elif who != "G":
            mid = 30 * math.sin(ph) if walking else 0
            F.poly([(-48, -430), (44, -430), (58 + mid * 0.3, -130), (-54 + mid * 0.3, -130)], L["low"])
            F.poly([(14, -420), (34, -420), (40 + mid * 0.3, -140), (18 + mid * 0.3, -140)], L["fold"], False)
            F.line([(-46, -150), (56, -150)], 5, L["sash"] if who in ("K", "P", "C") else GOLD)
    # ---------- back arm
    ua, fa = ARM.get(pose, ARM["stand"])
    swing = 22 * math.sin(ph) if walking else 0
    sh = (-4, -606 + up)
    def arm(sh, u, v, col, hand_col):
        e = (sh[0] + vec(u, 150)[0], sh[1] + vec(u, 150)[1]); h = (e[0] + vec(v, 140)[0], e[1] + vec(v, 140)[1])
        F.limb([sh, e, h], 30, col); F.ell(h[0], h[1], 16, 16, hand_col)
        return h
    sleeve = L["top"] or L["skin"]
    arm(sh, ua[0] - swing, ua[1] - swing, shade(sleeve), shade(L["skin"]))
    # ---------- torso
    top = L["top"] or L["skin"]
    F.poly([(-40, -634 + up), (30, -640 + up), (48, -560 + up), (42, -410 + up), (-44, -410 + up), (-50, -560 + up)], top)
    if who == "K":
        F.poly([(-36, -630 + up), (-12, -634 + up), (40, -430 + up), (16, -420 + up)], L["sash"])
        F.arc(6, -560 + up, 40, 60, 20, 160, 5, (250, 230, 120))                 # vaijayanti mala
    elif who in ("A", "R", "C", "P"):
        F.poly([(-44, -440 + up), (44, -440 + up), (44, -410 + up), (-44, -410 + up)], L["sash"])
        if who == "A": F.poly([(-20, -630 + up), (36, -628 + up), (44, -520 + up), (-10, -520 + up)], GOLD)
        if who == "R": F.line([(30, -630 + up), (40, -440 + up)], 6, GOLD)
    elif who == "G":
        F.poly([(-44, -470 + up), (44, -470 + up), (44, -410 + up), (-44, -410 + up)], (120, 80, 50))
    F.poly([(-14, -660 + up), (18, -662 + up), (20, -628 + up), (-12, -626 + up)], L["skin"])   # neck
    # ---------- head
    bl = blink(t + BLINK_OFF.get(who, 0))
    head(F, who, L, "neutral" if mood == "smile" else mood, talk, bl, -716 + up)
    # ---------- front arm (on top)
    if pose == "talk": fa = (fa[0], fa[1] + 18 * math.sin(t * 3.3) * min(1, talk * 4))
    h = arm((6, -600 + up), fa[0] + swing, fa[1] + swing, sleeve, L["skin"])
    if who == "G":
        F.line([(h[0], h[1] - 300), (h[0], -10)], 7, (120, 82, 50))
        F.poly([(h[0], h[1] - 350), (h[0] + 12, h[1] - 300), (h[0], h[1] - 286), (h[0] - 12, h[1] - 300)], (215, 222, 232))
    if who == "K" and pose == "bless":
        F.ell(h[0], h[1] - 20, 40, 40, None, False)
    if mood == "sad" and talk < 0.05:                 # a tear
        q = (t % 1.3) / 1.3
        F.ell(36, -716 + up + 8 + q * 50, 4, 6, (130, 195, 255, int(230 * (1 - q))), False)
