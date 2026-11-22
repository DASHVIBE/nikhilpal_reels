"""Text and graphic overlays: captions, title card, end card, hook ribbon, sticker, icon cards, pill, watermark.

Look: dark plum caption boxes with a saffron edge (lower third), a saffron ribbon in the top-left corner,
comic-style Bangers titles, teal tags.
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from .config import W, FONT_CAP, FONT_B, FONT_TITLE, TAGS, CHANNEL_NAME, SAFFRON, PLUM, TEAL, CREAM

CACHE = {}   # fonts + rendered overlays (cleared per reel by render.start())
WHITE = (255, 255, 255)


def fonts():
    if "f_cap" not in CACHE:
        CACHE["f_cap"] = ImageFont.truetype(FONT_CAP, 66)
        CACHE["f_b"] = ImageFont.truetype(FONT_B, 44)
        CACHE["f_tag"] = ImageFont.truetype(FONT_CAP, 38)
        CACHE["f_big"] = ImageFont.truetype(FONT_TITLE, 132)
        CACHE["f_btn"] = ImageFont.truetype(FONT_CAP, 52)
    return CACHE

def parse_tokens(text):
    toks, cur, hl, state = [], "", False, False
    for ch in text:
        if ch == "*": state = not state; continue
        if ch == " ":
            if cur: toks.append((cur, hl)); cur = ""
            continue
        if not cur: hl = state
        cur += ch
    if cur: toks.append((cur, hl))
    return toks

def ctext(d, cx, y, txt, font, fill, stroke=6, sfill=PLUM):
    tw = font.getlength(txt); d.text((cx - tw / 2, y), txt, font=font, fill=fill, stroke_width=stroke, stroke_fill=sfill)

def fit(text, font, maxw):
    size = font.size
    while size > 26 and ImageFont.truetype(font.path, size).getlength(text) > maxw: size -= 4
    return ImageFont.truetype(font.path, size)

def shadowed(img, r=10, off=(0, 10), a=120):
    """Soft drop shadow under everything drawn on img."""
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sh.putalpha(img.getchannel("A").point(lambda v: v * a // 255))
    sh = sh.filter(ImageFilter.GaussianBlur(r))
    out = Image.new("RGBA", img.size, (0, 0, 0, 0)); out.alpha_composite(sh, off); out.alpha_composite(img)
    return out

def make_caption(text, spk, tag=None):
    """Plum box with a saffron left edge; key words in saffron; speaker name on a small tab above the box."""
    f = fonts(); font = f["f_cap"]; sp = font.getlength(" ")
    lines, cur, cw = [], [], 0
    for w, hl in parse_tokens(text):
        ww = font.getlength(w)
        if cur and cw + sp + ww > 860: lines.append(cur); cur, cw = [], 0
        cw = ww if not cur else cw + sp + ww; cur.append((w, hl, ww))
    lines.append(cur)
    lh = int(font.size * 1.12); tab = 62 if spk in TAGS else 0
    bw = max(sum(x[2] for x in ln) + sp * (len(ln) - 1) for ln in lines) + 90
    bh = lh * len(lines) + 44
    img = Image.new("RGBA", (W, tab + bh + 30), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    x0 = (W - bw) / 2; y0 = tab
    d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=26, fill=PLUM + (225,))
    d.rounded_rectangle([x0, y0, x0 + 16, y0 + bh], radius=8, fill=SAFFRON)
    if spk in TAGS:
        name, col = TAGS[spk]; name = tag or name; tf = f["f_tag"]; tw = tf.getlength(name)
        d.rounded_rectangle([x0 + 24, 6, x0 + 24 + tw + 44, tab + 6], radius=14, fill=col)
        d.text((x0 + 46, 6 + (tab - tf.size * 1.3) / 2), name, font=tf, fill=WHITE)
    for li, line in enumerate(lines):
        lw = sum(x[2] for x in line) + sp * (len(line) - 1); x = (W - lw) / 2 + 8; y = y0 + 16 + li * lh
        for w, hl, ww in line:
            d.text((x, y), w, font=font, fill=SAFFRON if hl else WHITE)
            x += ww + sp
    return shadowed(img, 12, (0, 8), 110)

def make_title(label, l1, l2, sub):
    """Comic title: label tab, two big Bangers lines (saffron + white), subtitle on a plum strip."""
    f = fonts(); img = Image.new("RGBA", (W, 520), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    tf = f["f_tag"]; tw = tf.getlength(label)
    d.polygon([(W/2 - tw/2 - 40, 30), (W/2 + tw/2 + 40, 30), (W/2 + tw/2 + 22, 92), (W/2 - tw/2 - 22, 92)], fill=TEAL)
    d.text((W/2 - tw/2, 34), label, font=tf, fill=WHITE)
    ctext(d, W/2, 100, l1.upper(), fit(l1.upper(), f["f_big"], 900), SAFFRON, 9)
    ctext(d, W/2, 240, l2.upper(), fit(l2.upper(), f["f_big"], 900), WHITE, 9)
    sf = fit(sub, f["f_b"], 820); sw = sf.getlength(sub)
    d.rounded_rectangle([W/2 - sw/2 - 34, 400, W/2 + sw/2 + 34, 470], radius=35, fill=PLUM + (230,), outline=SAFFRON, width=4)
    d.text((W/2 - sw/2, 404), sub, font=sf, fill=CREAM)
    return shadowed(img, 14, (0, 10), 140)

def make_end(end_text, end_sub):
    """Cream card with a saffron top band, Bangers headline, teal subscribe button with a bell."""
    f = fonts(); img = Image.new("RGBA", (W, 560), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    x0, x1 = 120, W - 120
    d.rounded_rectangle([x0, 30, x1, 520], radius=40, fill=CREAM + (245,))
    d.rounded_rectangle([x0, 30, x1, 70], radius=20, fill=SAFFRON); d.rectangle([x0, 50, x1, 70], fill=SAFFRON)
    ctext(d, W/2, 90, end_text.upper(), fit(end_text.upper(), f["f_big"], 760), PLUM, 0)
    sf = fit(end_sub, f["f_b"], 740); ctext(d, W/2, 238, end_sub, sf, (90, 60, 80), 0)
    bw, bh, by = 600, 116, 340; bx = (W - bw) / 2
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=58, fill=TEAL)
    bf = f["f_btn"]; label = "SUBSCRIBE KARO"; tw = bf.getlength(label)
    cx = W/2 + 30; d.text((cx - tw/2, by + (bh - bf.size * 1.3) / 2), label, font=bf, fill=WHITE)
    bxl = cx - tw/2 - 62; byl = by + bh/2                      # bell
    d.chord([bxl - 24, byl - 30, bxl + 24, byl + 26], 180, 360, fill=SAFFRON)
    d.rectangle([bxl - 24, byl - 4, bxl + 24, byl + 14], fill=SAFFRON)
    d.rounded_rectangle([bxl - 32, byl + 10, bxl + 32, byl + 20], radius=5, fill=SAFFRON)
    d.ellipse([bxl - 8, byl + 18, bxl + 8, byl + 32], fill=SAFFRON)
    return shadowed(img, 16, (0, 12), 140)

def make_hook(text):
    """Saffron ribbon in the top-left corner for the whole reel; *word* is shown in white."""
    font = fit(text.replace("*", ""), ImageFont.truetype(FONT_CAP, 54), 760)
    toks = parse_tokens(text); sp = font.getlength(" ")
    tw = sum(font.getlength(w) for w, _ in toks) + sp * (len(toks) - 1)
    bw = tw + 110; img = Image.new("RGBA", (W, 150), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.polygon([(0, 30), (bw, 30), (bw - 34, 75), (bw, 120), (0, 120)], fill=SAFFRON)
    d.rectangle([0, 30, 18, 120], fill=PLUM)
    x = 44; y = 75 - font.size * 0.66
    for w, hl in toks:
        d.text((x, y), w, font=font, fill=WHITE if hl else PLUM); x += font.getlength(w) + sp
    return shadowed(img, 8, (0, 6), 110)

def make_watermark():
    font = ImageFont.truetype(FONT_CAP, 30); txt = CHANNEL_NAME; tw = font.getlength(txt)
    img = Image.new("RGBA", (int(tw + 70), 60), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 6, tw + 66, 54], radius=24, fill=PLUM + (150,))
    d.polygon([(18, 30), (28, 18), (38, 30), (28, 42)], fill=SAFFRON)
    d.text((48, 30 - font.size * 0.68), txt, font=font, fill=CREAM + (230,))
    return img

def make_sticker(text):
    """Teal tag tilted the other way, Bangers lettering, a saffron dot like a punched hole."""
    font = fit(text, ImageFont.truetype(FONT_TITLE, 66), 560); tw = font.getlength(text)
    bw, bh = int(tw + 110), int(font.size * 1.45)
    img = Image.new("RGBA", (bw + 30, bh + 30), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle([12, 12, bw + 12, bh + 12], radius=18, fill=TEAL, outline=CREAM, width=5)
    d.ellipse([30, 12 + bh/2 - 11, 52, 12 + bh/2 + 11], fill=SAFFRON)
    d.text((12 + 60 + (bw - 70 - tw) / 2, 12 + (bh - font.size * 1.05) / 2), text, font=font, fill=WHITE)
    return shadowed(img.rotate(5, resample=Image.BICUBIC, expand=True), 8, (0, 8), 120)

def _icon(d, icon, cx, cy, r):
    """Simple bold icons drawn into a 2x-scale card."""
    ink, gold, red, green = (44, 22, 58), (255, 176, 48), (220, 50, 70), (24, 160, 120)
    w = max(4, int(r * 0.14))
    if icon == "gallows":
        d.line([(cx - r*0.6, cy + r), (cx + r*0.2, cy + r)], fill=ink, width=w)
        d.line([(cx - r*0.4, cy + r), (cx - r*0.4, cy - r)], fill=ink, width=w)
        d.line([(cx - r*0.4, cy - r), (cx + r*0.5, cy - r)], fill=ink, width=w)
        d.line([(cx + r*0.4, cy - r), (cx + r*0.4, cy - r*0.35)], fill=ink, width=max(3, w // 2))
        d.ellipse([cx + r*0.22, cy - r*0.4, cx + r*0.58, cy + r*0.05], outline=ink, width=max(3, w // 2))
    elif icon == "sword":
        d.polygon([(cx - r*0.75, cy + r*0.75), (cx + r*0.6, cy - r*0.6), (cx + r*0.85, cy - r*0.85), (cx + r*0.75, cy - r*0.45), (cx - r*0.6, cy + r*0.9)], fill=(200, 208, 220), outline=ink)
        d.line([(cx - r*0.85, cy + r*0.45), (cx - r*0.45, cy + r*0.95)], fill=gold, width=w)
        d.line([(cx - r*0.75, cy + r*0.75), (cx - r*0.95, cy + r*0.95)], fill=(120, 70, 40), width=w)
    elif icon == "question":
        f = ImageFont.truetype(FONT_CAP, int(r * 2.1)); tw = f.getlength("?")
        d.text((cx - tw / 2, cy - r * 1.45), "?", font=f, fill=gold, stroke_width=max(3, w // 2), stroke_fill=ink)
    elif icon == "tick":
        d.line([(cx - r*0.7, cy), (cx - r*0.2, cy + r*0.55), (cx + r*0.75, cy - r*0.6)], fill=green, width=int(w*1.6), joint="curve")
    elif icon == "cross":
        for a, b in (((-0.65, -0.65), (0.65, 0.65)), ((0.65, -0.65), (-0.65, 0.65))):
            d.line([(cx + a[0]*r, cy + a[1]*r), (cx + b[0]*r, cy + b[1]*r)], fill=red, width=int(w*1.6))
    elif icon == "coin":
        for k, (dx, dy) in enumerate(((-0.35, 0.3), (0.3, 0.35), (0, -0.2))):
            x, y = cx + dx*r, cy + dy*r
            d.ellipse([x - r*0.5, y - r*0.5, x + r*0.5, y + r*0.5], fill=gold, outline=(170, 110, 20), width=max(3, w // 2))
            d.ellipse([x - r*0.3, y - r*0.3, x + r*0.3, y + r*0.3], outline=(200, 140, 30), width=max(2, w // 3))
    elif icon == "door":
        d.rectangle([cx - r*0.55, cy - r*0.4, cx + r*0.55, cy + r], fill=(150, 90, 50), outline=ink, width=max(3, w // 2))
        d.pieslice([cx - r*0.55, cy - r*0.95, cx + r*0.55, cy + r*0.15], 180, 360, fill=(150, 90, 50), outline=ink, width=max(3, w // 2))
        d.ellipse([cx + r*0.25, cy + r*0.3, cx + r*0.4, cy + r*0.45], fill=gold)
    elif icon == "lamp":
        d.ellipse([cx - r*0.15, cy - r*0.95, cx + r*0.15, cy - r*0.2], fill=(255, 190, 60))
        d.ellipse([cx - r*0.07, cy - r*0.6, cx + r*0.07, cy - r*0.3], fill=(255, 245, 210))
        d.chord([cx - r*0.8, cy - r*0.5, cx + r*0.8, cy + r*0.7], 0, 180, fill=(190, 100, 50), outline=ink, width=max(3, w // 2))
    elif icon == "crown":
        d.polygon([(cx - r*0.8, cy + r*0.5), (cx - r*0.8, cy - r*0.4), (cx - r*0.4, cy), (cx, cy - r*0.7), (cx + r*0.4, cy), (cx + r*0.8, cy - r*0.4), (cx + r*0.8, cy + r*0.5)], fill=gold, outline=ink)
        d.ellipse([cx - r*0.12, cy + r*0.05, cx + r*0.12, cy + r*0.29], fill=red)
    elif icon == "clock":
        d.ellipse([cx - r*0.8, cy - r*0.8, cx + r*0.8, cy + r*0.8], fill=(255, 250, 235), outline=ink, width=w)
        d.line([(cx, cy), (cx, cy - r*0.55)], fill=ink, width=w); d.line([(cx, cy), (cx + r*0.4, cy + r*0.15)], fill=ink, width=w)

def make_card(icon, label):
    """Round cream medallion with a saffron ring and a plum label ribbon under it."""
    k = 2; cw, ch = 300 * k, 330 * k
    img = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    cx, cy, r = cw / 2, 130 * k, 118 * k
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=CREAM, outline=SAFFRON, width=12 * k)
    _icon(d, icon, cx, cy, 78 * k)
    if label:
        f = fit(label, ImageFont.truetype(FONT_CAP, 40 * k), 250 * k); tw = f.getlength(label)
        d.rounded_rectangle([cx - tw/2 - 24*k, 262*k, cx + tw/2 + 24*k, 318*k], radius=14*k, fill=PLUM)
        d.text((cx - tw / 2, 262*k + (56*k - f.size * 1.3) / 2), label, font=f, fill=WHITE)
    return shadowed(img.resize((cw // k, ch // k), Image.LANCZOS), 8, (0, 8), 120)

def make_pill(text):
    font = ImageFont.truetype(FONT_B, 42); tw = font.getlength(text)
    img = Image.new("RGBA", (int(tw + 90), 90), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 8, tw + 88, 82], radius=37, fill=PLUM + (170,), outline=SAFFRON, width=4)
    d.polygon([(30, 32), (30, 58), (52, 45)], fill=SAFFRON)
    d.text((64, 45 - font.size * 0.7), text, font=font, fill=WHITE)
    return img

def overlay(frame, im, cx, cy, scale, alpha):
    if alpha <= 0.01: return
    if abs(scale - 1) > 0.01:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if alpha < 0.99:
        im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    frame.paste(im, (int(cx - im.width / 2), int(cy - im.height / 2)), im)
