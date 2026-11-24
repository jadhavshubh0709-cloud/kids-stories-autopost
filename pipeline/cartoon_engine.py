"""Cartoon engine (FREE, default): renders an animated 2D story where Veer and Veera really move
(walk, jump, wave, point, bounce, blink) with props, speech bubbles and read-along subtitles. 1080x1920, 30 fps.

render(spec, out_silent_mp4)  ->  spec["scenes"] each have a "dur" (seconds). Scene types: title, story, moral.
Story scene: {"bg": "home|park|night", "text": narration, "chars": [...], "props": [...], "say": [...], "sparkle": bool}
"""
import math, os, random, subprocess
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FONT_DIR = os.path.join(ROOT, "assets", "fonts")
HANDLE = "@kahani.time.kids"
BRAND = "KAHANI TIME"
GROUND = 1330
INK = (52, 36, 60)


def font(size, w="Bold"): return ImageFont.truetype(os.path.join(FONT_DIR, f"Poppins-{w}.ttf"), size)
def ease(t): t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3
def lerp(a, b, t): return a + (b - a) * t


# ---------------------------------------------------------------- backgrounds
def grad(top, bot):
    img = Image.new("RGB", (W, H)); d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H; d.line([(0, y), (W, y)], fill=tuple(int(lerp(top[i], bot[i], t)) for i in range(3)))
    return img


def aa(draw_fn, size, scale=2):
    big = Image.new("RGBA", (size[0] * scale, size[1] * scale), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(big), scale)
    return big.resize(size, Image.LANCZOS)


@lru_cache(None)
def bg_base(kind):
    if kind == "park":
        img = grad((120, 200, 255), (200, 236, 255)).convert("RGBA")
        def f(d, s):
            d.ellipse([820*s, 180*s, 1000*s, 360*s], fill=(255, 214, 70))
            d.ellipse([-300*s, 1000*s, 700*s, 1500*s], fill=(120, 200, 110))
            d.ellipse([400*s, 980*s, 1500*s, 1520*s], fill=(100, 185, 95))
            for x in (150, 900):
                d.rounded_rectangle([(x-22)*s, 900*s, (x+22)*s, 1180*s], 12*s, fill=(140, 95, 60))
                for dx, dy, r in ((0, 840, 120), (-70, 900, 90), (70, 900, 90)):
                    d.ellipse([(x+dx-r)*s, (dy-r)*s, (x+dx+r)*s, (dy+r)*s], fill=(70, 160, 80))
            d.rectangle([0, 1250*s, W*s, H*s], fill=(110, 195, 100))
            for x in range(20, W, 70):
                d.ellipse([x*s, 1300*s, (x+18)*s, 1318*s], fill=(250, 245, 120) if x % 140 else (255, 150, 180))
        img.alpha_composite(aa(f, (W, H)))
    elif kind == "night":
        img = grad((20, 24, 70), (70, 60, 130)).convert("RGBA")
        def f(d, s):
            d.ellipse([780*s, 200*s, 960*s, 380*s], fill=(255, 245, 200))
            d.ellipse([830*s, 180*s, 1000*s, 350*s], fill=(26, 30, 78))
            r = random.Random(4)
            for _ in range(60):
                x, y, k = r.randint(0, W), r.randint(60, 1000), r.choice((3, 4, 6))
                d.ellipse([(x-k)*s, (y-k)*s, (x+k)*s, (y+k)*s], fill=(255, 250, 220))
            d.ellipse([-300*s, 1050*s, 800*s, 1550*s], fill=(40, 70, 70))
            d.ellipse([350*s, 1020*s, 1500*s, 1560*s], fill=(35, 60, 62))
            d.rectangle([0, 1250*s, W*s, H*s], fill=(45, 80, 75))
        img.alpha_composite(aa(f, (W, H)))
    elif kind == "village":
        img = grad((140, 205, 250), (250, 225, 180)).convert("RGBA")
        def f(d, s):
            d.ellipse([90*s, 170*s, 250*s, 330*s], fill=(255, 200, 80))
            d.ellipse([-200*s, 950*s, 1300*s, 1400*s], fill=(150, 190, 100))
            for x0, w, col in ((60, 300, (220, 160, 110)), (700, 320, (230, 175, 120))):
                d.rectangle([x0*s, 880*s, (x0 + w)*s, 1180*s], fill=col)
                d.polygon([((x0 - 40)*s, 890*s), ((x0 + w/2)*s, 700*s), ((x0 + w + 40)*s, 890*s)], fill=(190, 120, 60))
                d.rounded_rectangle([(x0 + w/2 - 45)*s, 1020*s, (x0 + w/2 + 45)*s, 1180*s], 30*s, fill=(120, 80, 50))
            d.rectangle([0, 1250*s, W*s, H*s], fill=(215, 175, 120))
            for x in range(40, W, 160): d.ellipse([x*s, 1290*s, (x + 40)*s, 1305*s], fill=(195, 155, 105))
        img.alpha_composite(aa(f, (W, H)))
    elif kind == "school":
        img = grad((250, 245, 225), (240, 232, 205)).convert("RGBA")
        def f(d, s):
            d.rounded_rectangle([160*s, 300*s, 920*s, 760*s], 20*s, fill=(150, 110, 70))
            d.rounded_rectangle([185*s, 325*s, 895*s, 735*s], 12*s, fill=(45, 95, 70))
            d.arc([260*s, 420*s, 420*s, 560*s], 200, 340, fill=(240, 240, 240), width=6*s)       # chalk doodles, no text
            d.ellipse([600*s, 430*s, 700*s, 530*s], outline=(240, 240, 240), width=6*s)
            d.line([480*s, 600*s, 820*s, 600*s], fill=(240, 240, 240), width=5*s)
            for x in (60, 960): d.ellipse([(x - 40)*s, 820*s, (x + 40)*s, 900*s], fill=(120, 190, 120))
            d.rectangle([0, 1250*s, W*s, H*s], fill=(190, 170, 140))
            d.rounded_rectangle([380*s, 1150*s, 700*s, 1200*s], 14*s, fill=(170, 120, 80))
            d.rectangle([400*s, 1200*s, 425*s, 1290*s], fill=(140, 95, 60)); d.rectangle([655*s, 1200*s, 680*s, 1290*s], fill=(140, 95, 60))
        img.alpha_composite(aa(f, (W, H)))
    elif kind == "jungle":
        img = grad((120, 200, 170), (200, 240, 200)).convert("RGBA")
        def f(d, s):
            r = random.Random(7)
            for _ in range(14):
                x, y, rr = r.randint(-50, W + 50), r.randint(200, 900), r.randint(90, 170)
                d.ellipse([(x - rr)*s, (y - rr)*s, (x + rr)*s, (y + rr)*s], fill=r.choice([(40, 130, 70), (60, 150, 80), (30, 110, 60)]))
            for x in (120, 480, 930):
                d.rounded_rectangle([(x - 28)*s, 700*s, (x + 28)*s, 1260*s], 14*s, fill=(110, 75, 45))
            for x in (300, 700): d.line([x*s, 0, (x + 30)*s, 600*s], fill=(70, 140, 70), width=8*s)
            d.rectangle([0, 1250*s, W*s, H*s], fill=(90, 160, 90))
            for x in range(10, W, 90):
                d.polygon([(x*s, 1260*s), ((x + 20)*s, 1200*s), ((x + 40)*s, 1260*s)], fill=(60, 140, 70))
        img.alpha_composite(aa(f, (W, H)))
    else:  # home
        img = grad((255, 236, 210), (255, 222, 190)).convert("RGBA")
        def f(d, s):
            for x in range(0, W, 120): d.rectangle([x*s, 0, (x+60)*s, 1250*s], fill=(255, 229, 200))
            d.rounded_rectangle([640*s, 330*s, 980*s, 720*s], 20*s, fill=(255, 255, 255))
            d.rounded_rectangle([660*s, 350*s, 960*s, 700*s], 12*s, fill=(150, 210, 255))
            d.rectangle([805*s, 350*s, 815*s, 700*s], fill=(255, 255, 255))
            d.rectangle([660*s, 520*s, 960*s, 530*s], fill=(255, 255, 255))
            d.rounded_rectangle([620*s, 710*s, 1000*s, 740*s], 10*s, fill=(200, 140, 90))
            d.rounded_rectangle([90*s, 380*s, 330*s, 560*s], 12*s, fill=(255, 190, 120))
            d.ellipse([140*s, 420*s, 280*s, 520*s], fill=(255, 120, 120))
            d.rectangle([0, 1250*s, W*s, H*s], fill=(205, 150, 105))
            for x in range(0, W, 180): d.line([x*s, 1250*s, (x-80)*s, H*s], fill=(190, 135, 95), width=4*s)
            d.rounded_rectangle([380*s, 1150*s, 700*s, 1200*s], 14*s, fill=(170, 110, 70))
            d.rectangle([400*s, 1200*s, 425*s, 1290*s], fill=(150, 95, 60))
            d.rectangle([655*s, 1200*s, 680*s, 1290*s], fill=(150, 95, 60))
        img.alpha_composite(aa(f, (W, H)))
    return img


@lru_cache(16)
def photo_bg(path):
    """AI-made 3D background: fill 1080x1920, slight soft focus so the characters stand out (depth of field)."""
    im = Image.open(path).convert("RGB")
    sc = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * sc + 1), int(im.height * sc + 1)), Image.LANCZOS)
    x0 = (im.width - W) // 2; y0 = (im.height - H) // 2
    im = im.crop((x0, y0, x0 + W, y0 + H)).filter(ImageFilter.GaussianBlur(2.2))
    # gentle darkening at the bottom so subtitles and feet read well
    grad_ = Image.linear_gradient("L").resize((W, H)).point(lambda v: int(max(0, v - 150) * 0.5))
    shade = Image.new("RGB", (W, H), (20, 10, 30))
    return Image.composite(shade, im, grad_).convert("RGBA")


def scene_bg(kind, spec):
    p = (spec.get("bg_images") or {}).get(kind)
    if p and os.path.exists(p):
        return photo_bg(p).copy(), True
    return bg_base(kind).copy(), False


@lru_cache(8)
def _shadow(wd):
    sh = Image.new("RGBA", (wd + 60, 90), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([30, 25, wd + 30, 65], fill=(0, 0, 0, 120))
    return sh.filter(ImageFilter.GaussianBlur(10))


def ground_shadow(img, x, lift):
    k = max(0.45, 1 - lift / 260)
    sh = _shadow(int(200 * k))
    img.alpha_composite(sh, (int(x - sh.width / 2), GROUND - 50))


def camera(img, t, dur, push=0.05):
    """Slow movie-style push-in towards the characters."""
    z = 1 + push * ease(t / max(dur, 0.1))
    if z <= 1.001: return img
    w2, h2 = int(W / z), int(H / z)
    cx, cy = W / 2, 1050
    box = (int(cx - w2 / 2), int(min(max(cy - h2 * 0.55, 0), H - h2)), 0, 0)
    box = (box[0], box[1], box[0] + w2, box[1] + h2)
    return img.crop(box).resize((W, H), Image.BICUBIC)


def clouds(img, t, kind):
    if kind != "park": return
    d = ImageDraw.Draw(img)
    for i, (y, sp, sc) in enumerate(((260, 18, 1.0), (470, 12, 0.8), (640, 25, 0.65))):
        x = (i * 420 + t * sp) % (W + 400) - 200
        for dx, dy, r in ((0, 0, 60), (55, -25, 70), (115, 0, 58), (55, 15, 60)):
            r *= sc; d.ellipse([x + dx*sc - r, y + dy*sc - r, x + dx*sc + r, y + dy*sc + r], fill=(255, 255, 255))


# ---------------------------------------------------------------- characters
CAST = {
    # children (no adults are ever drawn)
    "veer":  {"kind": "kid", "name": "Veer", "desc": "6-year-old boy superhero, blue suit, red cape (twin of Veera)",
              "suit": (60, 120, 230), "cape": (230, 60, 60), "mask": True, "hair": "spiky", "trim": (255, 210, 60)},
    "veera": {"kind": "kid", "name": "Veera", "desc": "6-year-old girl superhero, pink suit, yellow cape (twin of Veer)",
              "suit": (235, 90, 160), "cape": (255, 200, 40), "mask": True, "hair": "ponytails", "trim": (120, 220, 255)},
    "aarav": {"kind": "kid", "name": "Aarav", "desc": "curious 7-year-old boy in a green kurta",
              "suit": (70, 170, 100), "cape": None, "mask": False, "hair": "short", "trim": (250, 230, 150)},
    "meera": {"kind": "kid", "name": "Meera", "desc": "cheerful 6-year-old girl in a purple frock, hair in a bun",
              "suit": (150, 100, 220), "cape": None, "mask": False, "hair": "bun", "trim": (255, 180, 200)},
    "anya":  {"kind": "kid", "name": "Anya", "desc": "shy 5-year-old girl in an orange dress with short hair",
              "suit": (250, 140, 60), "cape": None, "mask": False, "hair": "bob", "trim": (255, 240, 120)},
    # animal friends
    "gappu": {"kind": "elephant", "name": "Gappu", "desc": "a playful baby elephant", "fur": (155, 165, 185)},
    "chiku": {"kind": "bunny", "name": "Chiku", "desc": "a quick little white bunny", "fur": (246, 244, 240)},
    "bandu": {"kind": "monkey", "name": "Bandu", "desc": "a cheeky little monkey", "fur": (150, 100, 60)},
    "tara":  {"kind": "bear", "name": "Tara", "desc": "a gentle little honey-brown bear cub", "fur": (190, 130, 70)},
}
KIDS = CAST   # backwards compatible name
SKIN = (205, 150, 110)
CW, CH = 340, 560
MOODS = ("happy", "smile", "sad", "surprised", "cross")
ACTS = ("idle", "bounce", "walk", "jump", "wave", "point", "hero", "droop")


def limb(d, p1, p2, w, col):
    d.line([p1, p2], fill=col, width=int(w))
    for (x, y) in (p1, p2): d.ellipse([x - w/2, y - w/2, x + w/2, y + w/2], fill=col)


def star(d, cx, cy, r, col):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5; rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=col)


def face(d, X, cx, hy, mood, blink, sep=46, size=1.0, mouth_y=72, cheeks=(240, 120, 120)):
    for side in (-1, 1):
        ex, ey = cx + side * sep, hy + 6
        r = 19 * size
        if blink:
            d.line([X(ex - 18*size), X(ey + 4), X(ex + 18*size), X(ey + 4)], fill=INK, width=X(6))
        elif mood == "surprised":
            d.ellipse([X(ex - r - 2), X(ey - r - 3), X(ex + r + 2), X(ey + r + 3)], fill=(255, 255, 255))
            d.ellipse([X(ex - 10*size), X(ey - 10*size), X(ex + 10*size), X(ey + 10*size)], fill=INK)
        else:
            d.ellipse([X(ex - r), X(ey - r), X(ex + r), X(ey + r)], fill=(255, 255, 255))
            d.ellipse([X(ex - 12*size + side * 2), X(ey - 10*size), X(ex + 10*size + side * 2), X(ey + 12*size)], fill=INK)
            d.ellipse([X(ex - 4), X(ey - 7), X(ex + 3), X(ey)], fill=(255, 255, 255))
        if mood == "cross":
            d.line([X(ex - 24 * side), X(ey - 34), X(ex + 18 * side), X(ey - 24)], fill=INK, width=X(8))
        if mood == "sad":
            d.line([X(ex - 20 * side), X(ey - 24), X(ex + 18 * side), X(ey - 34)], fill=INK, width=X(7))
    if cheeks:
        for side in (-1, 1):
            d.ellipse([X(cx + side * (sep + 32) - 18), X(hy + 48), X(cx + side * (sep + 32) + 18), X(hy + 70)], fill=cheeks)
    my = hy + mouth_y
    if mood == "happy":
        d.chord([X(cx - 36), X(my - 26), X(cx + 36), X(my + 26)], 0, 180, fill=(150, 40, 60))
        d.chord([X(cx - 22), X(my + 4), X(cx + 22), X(my + 26)], 200, 340, fill=(255, 130, 140))
    elif mood == "sad":
        d.arc([X(cx - 26), X(my), X(cx + 26), X(my + 32)], 200, 340, fill=INK, width=X(7))
    elif mood == "surprised":
        d.ellipse([X(cx - 15), X(my - 6), X(cx + 15), X(my + 28)], fill=(150, 40, 60))
    elif mood == "cross":
        d.line([X(cx - 22), X(my + 10), X(cx + 22), X(my + 6)], fill=INK, width=X(7))
    else:
        d.arc([X(cx - 28), X(my - 18), X(cx + 28), X(my + 16)], 20, 160, fill=INK, width=X(7))


def _kid(d, X, k, mood, blink, arm_l, arm_r, leg, cape):
    cx = CW / 2; hair = (40, 30, 35)
    if k["cape"]:
        fl = cape * 22
        d.polygon([(X(cx - 62), X(300)), (X(cx + 62), X(300)), (X(cx + 95 + fl), X(470)), (X(cx - 95 + fl * 0.6), X(470))], fill=k["cape"])
    legcol = k["suit"] if k["mask"] else (60, 70, 110)
    for side, ph in ((-1, leg), (1, -leg)):
        hip = (X(cx + side * 30), X(440)); foot = (X(cx + side * 34 + ph * 28), X(530))
        limb(d, hip, foot, X(38), legcol if k["mask"] else SKIN)
        if not k["mask"]:
            d.rounded_rectangle([X(cx + side * 30 - 26), X(430), X(cx + side * 30 + 26), X(480)], X(10), fill=legcol)
        d.ellipse([foot[0] - X(30), foot[1] - X(8), foot[0] + X(30), foot[1] + X(22)], fill=k["cape"] or (120, 80, 60))
    if k["hair"] in ("bun", "bob") and not k["mask"]:   # dress shape
        d.polygon([(X(cx - 60), X(300)), (X(cx + 60), X(300)), (X(cx + 95), X(470)), (X(cx - 95), X(470))], fill=k["suit"])
        d.rounded_rectangle([X(cx - 62), X(290), X(cx + 62), X(370)], X(30), fill=k["suit"])
        d.line([X(cx - 90), X(462), X(cx + 90), X(462)], fill=k["trim"], width=X(10))
    else:
        d.rounded_rectangle([X(cx - 70), X(290), X(cx + 70), X(455)], X(42), fill=k["suit"])
        if k["mask"]:
            d.rectangle([X(cx - 70), X(415), X(cx + 70), X(432)], fill=k["trim"]); star(d, X(cx), X(352), X(30), k["trim"])
        else:
            for yy in (320, 350, 380): d.ellipse([X(cx - 6), X(yy - 6), X(cx + 6), X(yy + 6)], fill=k["trim"])
    for side, ang in ((-1, arm_l), (1, arm_r)):
        sh = (X(cx + side * 66), X(312)); a = math.radians(ang)
        hand = (sh[0] + side * math.sin(a) * X(105), sh[1] + math.cos(a) * X(105))
        limb(d, sh, hand, X(32), k["suit"] if k["mask"] else SKIN)
        if not k["mask"]: limb(d, sh, ((sh[0] * 2 + hand[0]) / 3, (sh[1] * 2 + hand[1]) / 3), X(36), k["suit"])
        d.ellipse([hand[0] - X(22), hand[1] - X(22), hand[0] + X(22), hand[1] + X(22)], fill=SKIN)
    hy = 170; r = 118
    if k["hair"] == "ponytails":
        for side in (-1, 1):
            px = cx + side * 122
            d.ellipse([X(px - 42), X(hy - 20), X(px + 42), X(hy + 95)], fill=hair)
            d.ellipse([X(px - 26), X(hy - 52), X(px + 26), X(hy - 10)], fill=k["cape"])
    if k["hair"] == "bun":
        d.ellipse([X(cx - 48), X(hy - r - 62), X(cx + 48), X(hy - r + 26)], fill=hair)
        d.ellipse([X(cx - 20), X(hy - r - 6), X(cx + 20), X(hy - r + 18)], fill=k["trim"])
    if k["hair"] == "bob":
        d.rounded_rectangle([X(cx - r - 14), X(hy - r), X(cx + r + 14), X(hy + 70)], X(60), fill=hair)
    d.ellipse([X(cx - r), X(hy - r), X(cx + r), X(hy + r)], fill=SKIN)
    d.ellipse([X(cx - r - 14), X(hy - 8), X(cx - r + 18), X(hy + 34)], fill=SKIN)
    d.ellipse([X(cx + r - 18), X(hy - 8), X(cx + r + 14), X(hy + 34)], fill=SKIN)
    if k["hair"] == "spiky":
        d.chord([X(cx - r - 4), X(hy - r - 10), X(cx + r + 4), X(hy + r - 40)], 180, 360, fill=hair)
        for i in range(5):
            x0 = cx - 95 + i * 42
            d.polygon([(X(x0), X(hy - 60)), (X(x0 + 44), X(hy - 60)), (X(x0 + 26), X(hy - 18))], fill=hair)
        d.polygon([(X(cx - 20), X(hy - r - 6)), (X(cx + 10), X(hy - r - 40)), (X(cx + 30), X(hy - r + 2))], fill=hair)
    elif k["hair"] == "short":
        d.chord([X(cx - r - 4), X(hy - r - 8), X(cx + r + 4), X(hy + r - 50)], 180, 360, fill=hair)
        d.pieslice([X(cx - r - 4), X(hy - r - 8), X(cx + 60), X(hy - 10)], 180, 280, fill=hair)
    else:
        d.chord([X(cx - r - 6), X(hy - r - 12), X(cx + r + 6), X(hy + r - 30)], 180, 360, fill=hair)
        d.pieslice([X(cx - r - 6), X(hy - r - 12), X(cx + 30), X(hy + 10)], 180, 270, fill=hair)
    if k["mask"]:
        d.rounded_rectangle([X(cx - 96), X(hy - 16), X(cx + 96), X(hy + 30)], X(22), fill=k["suit"])
    face(d, X, cx, hy, mood, blink)


def _animal(d, X, k, mood, blink, arm_l, arm_r, leg):
    cx = CW / 2; fur = k["fur"]; kind = k["kind"]
    dark = tuple(max(0, c - 40) for c in fur); light = tuple(min(255, c + 45) for c in fur)
    if kind == "monkey":
        d.arc([X(cx + 20), X(330), X(cx + 160), X(480)], 200, 100, fill=dark, width=X(18))
    if kind == "bunny":
        d.ellipse([X(cx + 50), X(400), X(cx + 100), X(450)], fill=(255, 255, 255))
    for side, ph in ((-1, leg), (1, -leg)):
        hip = (X(cx + side * 40), X(450)); foot = (X(cx + side * 44 + ph * 26), X(528))
        limb(d, hip, foot, X(52 if kind in ("elephant", "bear") else 40), fur)
        d.ellipse([foot[0] - X(32), foot[1] - X(8), foot[0] + X(32), foot[1] + X(22)], fill=dark)
    d.ellipse([X(cx - 95), X(300), X(cx + 95), X(490)], fill=fur)
    d.ellipse([X(cx - 55), X(340), X(cx + 55), X(470)], fill=light if kind != "bunny" else (255, 235, 240))
    for side, ang in ((-1, arm_l), (1, arm_r)):
        sh = (X(cx + side * 80), X(345)); a = math.radians(ang)
        hand = (sh[0] + side * math.sin(a) * X(95), sh[1] + math.cos(a) * X(95))
        limb(d, sh, hand, X(36), fur)
        d.ellipse([hand[0] - X(22), hand[1] - X(22), hand[0] + X(22), hand[1] + X(22)], fill=dark if kind != "bunny" else fur)
    hy = 190; r = 110
    if kind == "elephant":
        for side in (-1, 1):
            d.ellipse([X(cx + side * 120 - 80), X(hy - 90), X(cx + side * 120 + 80), X(hy + 90)], fill=fur)
            d.ellipse([X(cx + side * 120 - 52), X(hy - 60), X(cx + side * 120 + 52), X(hy + 62)], fill=(240, 180, 190))
    if kind == "bunny":
        for side in (-1, 1):
            d.ellipse([X(cx + side * 50 - 30), X(hy - 250), X(cx + side * 50 + 30), X(hy - 60)], fill=fur)
            d.ellipse([X(cx + side * 50 - 15), X(hy - 225), X(cx + side * 50 + 15), X(hy - 80)], fill=(255, 190, 200))
    if kind in ("monkey", "bear"):
        for side in (-1, 1):
            d.ellipse([X(cx + side * 100 - 42), X(hy - 110), X(cx + side * 100 + 42), X(hy - 26)], fill=fur)
            d.ellipse([X(cx + side * 100 - 22), X(hy - 90), X(cx + side * 100 + 22), X(hy - 46)], fill=light)
    d.ellipse([X(cx - r), X(hy - r), X(cx + r), X(hy + r)], fill=fur)
    if kind == "monkey":
        d.ellipse([X(cx - 82), X(hy - 50), X(cx + 82), X(hy + 100)], fill=(240, 200, 160))
    if kind == "bear":
        d.ellipse([X(cx - 50), X(hy + 30), X(cx + 50), X(hy + 100)], fill=light)
    face(d, X, cx, hy - 10, mood, blink, sep=40, size=0.9, mouth_y=80, cheeks=(250, 150, 160))
    if kind == "elephant":   # trunk over the mouth, curling up when happy
        up = mood in ("happy", "surprised")
        trunk = tuple(max(0, c - 18) for c in fur)
        pts = [X(cx), X(hy + 30), X(cx + 4), X(hy + 100), X(cx + (46 if up else 12)), X(hy + (112 if up else 165))]
        d.line(pts, fill=dark, width=X(40), joint="curve")
        d.line(pts, fill=trunk, width=X(30), joint="curve")
        for yy in (60, 80): d.arc([X(cx - 12), X(hy + yy - 6), X(cx + 16), X(hy + yy + 6)], 0, 180, fill=dark, width=X(3))
    if kind == "bunny":
        d.polygon([(X(cx - 10), X(hy + 48)), (X(cx + 10), X(hy + 48)), (X(cx), X(hy + 60))], fill=(240, 120, 140))
    if kind == "bear":
        d.ellipse([X(cx - 14), X(hy + 40), X(cx + 14), X(hy + 58)], fill=INK)


def _blur(m, r):
    return np.asarray(Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)),
                      dtype=np.float32) / 255.0


def shade3d(img, strength=1.0, min_px=250):
    """Soft 3D 'clay toy' look. Every flat-coloured part (head, body, arms, ears...) is lit like a rounded object:
    bright towards the top-left, darker towards its bottom-right edge, with a small soft highlight."""
    arr = np.asarray(img, dtype=np.uint8)
    rgb = arr[..., :3].astype(np.float32); a = arr[..., 3].astype(np.float32) / 255.0
    h, w = a.shape
    solid = a > 0.98
    key = (arr[..., 0].astype(np.int32) << 16) | (arr[..., 1].astype(np.int32) << 8) | arr[..., 2].astype(np.int32)
    vals, counts = np.unique(key[solid], return_counts=True)
    factor = np.ones((h, w), np.float32); spec = np.zeros((h, w), np.float32)
    for v, c in zip(vals, counts):
        if c < min_px: continue                                    # eyes, mouths, small details stay crisp
        m = ((key == v) & solid).astype(np.float32)
        ys, xs = np.nonzero(m); size = int(max(10, min(np.ptp(ys), np.ptp(xs)) + 1))
        r = max(3, size // 5); d = max(2, size // 6)
        up_left = np.zeros_like(m); up_left[:h - d, :w - d] = m[d:, d:]           # part moved up-left by d
        lit = _blur(up_left * m, r)                                                # high top-left, low bottom-right
        depth = _blur(m, r)                                                       # 1 inside, ~0.5 at the outline
        f = 0.80 + 0.26 * lit + 0.08 * depth
        factor = np.where(m > 0, f, factor)
        d2 = max(3, size // 3); hl = np.zeros_like(m); hl[:h - d2, :w - d2] = m[d2:, d2:]
        sp = np.clip(_blur(hl * m, r) - 0.82, 0, 1) * 2.2
        spec = np.where(m > 0, sp, spec)
    assigned = (factor != 1).astype(np.float32)
    if assigned.any():   # give anti-aliased edge pixels the shading of the part next to them (no light seams)
        num = np.asarray(Image.fromarray(((factor - 0.5) * assigned * 200).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2)), np.float32)
        den = np.asarray(Image.fromarray((assigned * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2)), np.float32)
        with np.errstate(divide="ignore", invalid="ignore"):
            filled = np.where(den > 8, (num / 200) / np.maximum(den / 255, 1e-3) + 0.5, 1.0)
        factor = np.where(assigned > 0, factor, filled)
    factor = 1 + (factor - 1) * strength
    out = np.clip(rgb * factor[..., None] + 255 * spec[..., None] * 0.35 * strength, 0, 255).astype(np.uint8)
    res = Image.fromarray(np.dstack([out, arr[..., 3]]), "RGBA")
    return res


@lru_cache(6000)
def kid_sprite(who, mood, blink, arm_l, arm_r, leg, cape, flip):
    k = CAST[who]
    def f(d, s):
        X = lambda v: v * s
        if k["kind"] == "kid": _kid(d, X, k, mood, blink, arm_l, arm_r, leg, cape)
        else: _animal(d, X, k, mood, blink, arm_l, arm_r, leg)
    img = shade3d(aa(f, (CW, CH)))
    return img.transpose(Image.FLIP_LEFT_RIGHT) if flip else img


def kid_frame(c, t, dur):
    act = c.get("act", "idle"); who = c["who"]
    ph = t * 2 * math.pi
    seed = (sum(map(ord, who)) % 17) / 6.0
    blink = (t + seed) % 3.1 < 0.12
    x = c.get("x", 540); y_off = 0; leg = 0; arm_l = arm_r = 18; cape = math.sin(ph * 1.2 + seed) * 0.5
    mood = c.get("mood", "smile")
    if act == "idle":
        y_off = -abs(math.sin(ph * 0.9 + seed)) * 8
    elif act == "bounce":
        y_off = -abs(math.sin(ph * 1.6 + seed)) * 40; arm_l = arm_r = 35 + 20 * abs(math.sin(ph * 1.6 + seed))
    elif act == "walk":
        p = ease(t / max(0.1, dur * 0.8)); x = lerp(c.get("from_x", x), c.get("to_x", x), p)
        if p < 1:
            leg = math.sin(ph * 3); y_off = -abs(math.sin(ph * 3)) * 12
            arm_l = 18 + 25 * math.sin(ph * 3); arm_r = 18 - 25 * math.sin(ph * 3); cape = 1
    elif act == "jump":
        y_off = -abs(math.sin(ph * 1.25 + seed)) * 120; arm_l = arm_r = 150; cape = 1; leg = 0.4
    elif act == "wave":
        y_off = -abs(math.sin(ph * 0.9)) * 6; arm_r = 150 + 22 * math.sin(ph * 3)
    elif act == "point":
        arm_r = 95; y_off = -abs(math.sin(ph)) * 6
    elif act == "hero":
        arm_l = arm_r = 40; cape = 1 + 0.3 * math.sin(ph * 2); y_off = -4
    elif act == "droop":
        arm_l = arm_r = 6; y_off = 6
    face_dir = c.get("face") or ("right" if x < 540 else "left")
    q = lambda v, n: round(v / n) * n
    spr = kid_sprite(who, mood, blink, q(arm_l, 6), q(arm_r, 6), round(leg, 1), round(cape, 1), face_dir == "left")
    return spr, x, GROUND + y_off


# ---------------------------------------------------------------- props
PROPS = ("plate", "bird", "ball", "puppy", "kitten", "tree_mango", "mango", "gift", "heart", "flower_pot", "book", "kite")


@lru_cache(64)
def prop_sprite(kind, state=""):
    return shade3d(_prop_sprite(kind, state), 0.8)


def _prop_sprite(kind, state=""):
    if kind == "plate":
        n = {"one": 1, "three": 3, "two": 2, "empty": 0, "": 1}.get(state, 1)
        def f(d, s):
            d.ellipse([10*s, 60*s, 250*s, 120*s], fill=(250, 250, 255)); d.ellipse([40*s, 70*s, 220*s, 110*s], fill=(225, 230, 240))
            if n == 1:
                d.ellipse([90*s, 20*s, 170*s, 100*s], fill=(250, 160, 40)); d.ellipse([105*s, 32*s, 130*s, 52*s], fill=(255, 205, 110))
            for i in range(n if n > 1 else 0):
                cx = 130 + (i - (n - 1) / 2) * 60
                d.pieslice([(cx-30)*s, 45*s, (cx+30)*s, 105*s], 180, 360, fill=(250, 160, 40))
        return aa(f, (260, 130))
    if kind == "bird":
        def f(d, s):
            d.ellipse([20*s, 30*s, 110*s, 100*s], fill=(150, 110, 80)); d.ellipse([75*s, 10*s, 125*s, 60*s], fill=(150, 110, 80))
            d.ellipse([20*s, 50*s, 70*s, 95*s], fill=(120, 85, 60)); d.ellipse([50*s, 55*s, 95*s, 95*s], fill=(235, 220, 200))
            d.polygon([(122*s, 32*s), (145*s, 40*s), (122*s, 46*s)], fill=(250, 170, 40))
            d.ellipse([100*s, 25*s, 112*s, 37*s], fill=INK)
            d.line([60*s, 98*s, 55*s, 120*s], fill=(250, 170, 40), width=4*s); d.line([80*s, 98*s, 85*s, 120*s], fill=(250, 170, 40), width=4*s)
        return aa(f, (150, 125))
    if kind == "ball":
        def f(d, s):
            d.ellipse([5*s, 5*s, 115*s, 115*s], fill=(255, 90, 90)); d.chord([5*s, 5*s, 115*s, 115*s], 200, 340, fill=(255, 230, 80))
            d.chord([5*s, 5*s, 115*s, 115*s], 20, 160, fill=(80, 170, 255))
        return aa(f, (120, 120))
    if kind in ("puppy", "kitten"):
        fur, ear = ((230, 190, 140), (150, 100, 70)) if kind == "puppy" else ((150, 150, 160), (110, 110, 120))
        def f(d, s):
            d.ellipse([20*s, 70*s, 170*s, 160*s], fill=fur)
            for x in (35, 140): d.rounded_rectangle([x*s, 140*s, (x+22)*s, 190*s], 10*s, fill=fur)
            d.ellipse([110*s, 10*s, 210*s, 110*s], fill=fur)
            if kind == "puppy":
                d.ellipse([100*s, 20*s, 135*s, 90*s], fill=ear); d.ellipse([185*s, 20*s, 220*s, 90*s], fill=ear)
            else:
                d.polygon([(115*s, 30*s), (125*s, -5*s), (150*s, 20*s)], fill=fur); d.polygon([(170*s, 20*s), (195*s, -5*s), (205*s, 30*s)], fill=fur)
                for k in (-1, 1): d.line([(160 + k*20)*s, 75*s, (160 + k*60)*s, (70 + k*4)*s], fill=INK, width=2*s)
            d.ellipse([145*s, 45*s, 160*s, 60*s], fill=INK); d.ellipse([175*s, 45*s, 190*s, 60*s], fill=INK)
            d.ellipse([157*s, 70*s, 177*s, 84*s], fill=INK if kind == "puppy" else (240, 130, 150))
            d.line([20*s, 90*s, 0*s, 60*s], fill=fur, width=12*s)
        return aa(f, (225, 195))
    if kind == "tree_mango":
        def f(d, s):
            d.rounded_rectangle([110*s, 260*s, 160*s, 520*s], 14*s, fill=(140, 95, 60))
            d.ellipse([0, 0, 270*s, 320*s], fill=(60, 150, 70))
            for x, y in ((60, 120), (150, 90), (200, 180), (100, 210), (170, 250)):
                d.ellipse([x*s, y*s, (x+34)*s, (y+44)*s], fill=(255, 190, 40))
        return aa(f, (270, 520))
    if kind == "mango":
        def f(d, s):
            d.ellipse([10*s, 20*s, 100*s, 130*s], fill=(255, 190, 40)); d.ellipse([25*s, 35*s, 50*s, 65*s], fill=(255, 225, 120))
            d.ellipse([50*s, 0, 90*s, 25*s], fill=(70, 160, 80))
        return aa(f, (110, 135))
    if kind == "gift":
        def f(d, s):
            d.rounded_rectangle([10*s, 50*s, 170*s, 190*s], 10*s, fill=(150, 110, 255)); d.rectangle([80*s, 50*s, 100*s, 190*s], fill=(255, 220, 80))
            d.ellipse([45*s, 10*s, 90*s, 55*s], outline=(255, 220, 80), width=10*s); d.ellipse([90*s, 10*s, 135*s, 55*s], outline=(255, 220, 80), width=10*s)
        return aa(f, (180, 195))
    if kind == "heart":
        def f(d, s):
            d.ellipse([0, 0, 60*s, 60*s], fill=(255, 80, 120)); d.ellipse([50*s, 0, 110*s, 60*s], fill=(255, 80, 120))
            d.polygon([(4*s, 40*s), (106*s, 40*s), (55*s, 100*s)], fill=(255, 80, 120))
        return aa(f, (110, 105))
    if kind == "flower_pot":
        wilted = state == "wilted"
        def f(d, s):
            d.polygon([(30*s, 150*s), (150*s, 150*s), (130*s, 240*s), (50*s, 240*s)], fill=(200, 100, 60))
            d.line([90*s, 150*s, (60 if wilted else 90)*s, 60*s], fill=(70, 150, 70), width=8*s)
            c = (190, 160, 120) if wilted else (255, 110, 150)
            cx, cy = (60, 70) if wilted else (90, 50)
            for a in range(0, 360, 60):
                d.ellipse([(cx + 28*math.cos(math.radians(a)) - 20)*s, (cy + 28*math.sin(math.radians(a)) - 20)*s,
                           (cx + 28*math.cos(math.radians(a)) + 20)*s, (cy + 28*math.sin(math.radians(a)) + 20)*s], fill=c)
            d.ellipse([(cx-16)*s, (cy-16)*s, (cx+16)*s, (cy+16)*s], fill=(255, 210, 60))
        return aa(f, (180, 245))
    if kind == "book":
        def f(d, s):
            d.polygon([(10*s, 40*s), (100*s, 20*s), (100*s, 120*s), (10*s, 140*s)], fill=(80, 170, 255))
            d.polygon([(100*s, 20*s), (190*s, 40*s), (190*s, 140*s), (100*s, 120*s)], fill=(255, 120, 120))
            d.line([100*s, 20*s, 100*s, 120*s], fill=INK, width=4*s)
        return aa(f, (200, 150))
    if kind == "kite":
        def f(d, s):
            d.polygon([(90*s, 0), (170*s, 90*s), (90*s, 200*s), (10*s, 90*s)], fill=(255, 90, 90))
            d.line([90*s, 0, 90*s, 200*s], fill=(255, 230, 80), width=5*s); d.line([10*s, 90*s, 170*s, 90*s], fill=(255, 230, 80), width=5*s)
            d.line([90*s, 200*s, 60*s, 320*s], fill=INK, width=3*s)
        return aa(f, (180, 325))
    raise ValueError(f"unknown prop: {kind}")


def place_prop(img, p, t):
    spr = prop_sprite(p["kind"], p.get("state", ""))
    x, y = p.get("x", 540), p.get("y", GROUND)
    if "from_x" in p:
        k = ease(t / p.get("move", 1.5)); x = lerp(p["from_x"], x, k); y = lerp(p.get("from_y", y), y, k)
    anim = p.get("anim")
    if anim == "hop": y -= abs(math.sin(t * 5)) * 30
    if anim == "float":
        y -= t * 60; spr = spr.copy(); spr.putalpha(spr.getchannel("A").point(lambda a: int(a * max(0, 1 - t / 3))))
    if anim == "bob": y -= math.sin(t * 3) * 10
    if anim == "sway": x += math.sin(t * 2) * 25; y -= math.sin(t * 3) * 15
    if p.get("flip"): spr = spr.transpose(Image.FLIP_LEFT_RIGHT)
    img.alpha_composite(spr, (int(x - spr.width / 2), int(y - spr.height)))


# ---------------------------------------------------------------- text
def wrap(d, text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        test = (cur + " " + w).strip()
        if d.textlength(test, font=f) <= maxw: cur = test
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines


def narration_box(img, text, t, dur, lead=0.3):
    """Subtitle card; words light up one by one in time with the narrator."""
    d = ImageDraw.Draw(img); f = font(54)
    lines = wrap(d, text, f, 900)
    if len(lines) > 4: f = font(46); lines = wrap(d, text, f, 920)
    lh = int(f.size * 1.32); bh = lh * len(lines) + 70; y0 = 1440
    d.rounded_rectangle([50, y0, W - 50, y0 + bh], 44, fill=(255, 255, 255), outline=(255, 200, 60), width=8)
    words = text.split(); n = len(words)
    speak = max(0.5, dur - lead - 0.6)
    lit = int(n * min(1, max(0, t - lead) / speak)) + 1
    i = 0; y = y0 + 35
    for ln in lines:
        x = (W - d.textlength(ln, font=f)) / 2
        for w in ln.split():
            d.text((x, y), w, font=f, fill=INK if i < lit else (200, 190, 205)); x += d.textlength(w + " ", font=f); i += 1
        y += lh


def bubble(img, text, x, y, t):
    if t < 0.2: return
    d = ImageDraw.Draw(img); f = font(50)
    if d.textlength(text, font=f) > 800: f = font(40)
    tw = d.textlength(text, font=f); bw, bh = tw + 70, f.size + 50
    bx = max(30, min(W - 30 - bw, x - bw / 2)); by = max(240, y - bh)
    d.rounded_rectangle([bx, by, bx + bw, by + bh], 40, fill=(255, 255, 255), outline=INK, width=5)
    d.polygon([(x - 18, by + bh - 3), (x + 18, by + bh - 3), (x, by + bh + 34)], fill=(255, 255, 255))
    d.line([(x - 18, by + bh), (x, by + bh + 34), (x + 18, by + bh)], fill=INK, width=5)
    d.text((bx + 35, by + 22), text, font=f, fill=INK)


def top_pill(img, label):
    d = ImageDraw.Draw(img); f = font(36); tw = d.textlength(label, font=f)
    d.rounded_rectangle([(W - tw) / 2 - 32, 150, (W + tw) / 2 + 32, 222], 36, fill=(255, 200, 40))
    d.text(((W - tw) / 2, 160), label, font=f, fill=INK)


def outlined(d, xy, text, f, fill, stroke=INK, sw=8):
    d.text(xy, text, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke)


def sparkles(img, t, n=14, seed=1):
    d = ImageDraw.Draw(img); r = random.Random(seed)
    for _ in range(n):
        x, y, sp = r.randint(60, W - 60), r.randint(300, 1250), r.uniform(1.5, 3)
        k = (math.sin(t * sp * 3 + x) + 1) / 2 * 16 + 4
        star(d, x, y, k, (255, 230, 90))


# ---------------------------------------------------------------- scenes
def s_title(s, spec, t):
    img, ai = scene_bg(s.get("bg", "park"), spec)
    if not ai: clouds(img, t, s.get("bg", "park"))
    d = ImageDraw.Draw(img)
    k = ease(t / 0.6)
    f1 = font(130); line = BRAND
    outlined(d, ((W - d.textlength(line, font=f1)) / 2, lerp(-150, 300, k)), line, f1, (255, 210, 50), sw=10)
    f2 = font(84); y = 470
    for ln in wrap(d, spec["title"], f2, 960):
        outlined(d, ((W - d.textlength(ln, font=f2)) / 2, y), ln, f2, (255, 255, 255), sw=8); y += 104
    top_pill(img, f"STORY #{spec['story_no']}")
    cast = (spec.get("cast") or ["veer", "veera"])[:2]
    xs = (540,) if len(cast) == 1 else (360, 720)
    for i, (who, x) in enumerate(zip(cast, xs)):
        c = {"who": who, "x": x, "mood": "happy", "act": "wave" if i == 1 else "hero"}
        spr, cx, cy = kid_frame(c, t, s["dur"])
        dy = lerp(500, 0, ease(t / 0.8))
        if dy < 5: ground_shadow(img, cx, GROUND - cy)
        img.alpha_composite(spr, (int(cx - CW / 2), int(cy - CH + dy)))
    sparkles(img, t)
    return img


def s_story(s, spec, t):
    bgk = s.get("bg", "park")
    img, ai = scene_bg(bgk, spec)
    if not ai: clouds(img, t, bgk)
    for p in s.get("props", []):
        if p.get("layer", "back") == "back": place_prop(img, p, t)
    pos = {}
    frames = [(c, *kid_frame(c, t, s["dur"])) for c in s.get("chars", [])]
    for c, spr, x, y in frames: ground_shadow(img, x, GROUND - y)
    for c, spr, x, y in frames:
        pos[c["who"]] = (x, y)
        img.alpha_composite(spr, (int(x - CW / 2), int(y - CH)))
    for p in s.get("props", []):
        if p.get("layer") == "front": place_prop(img, p, t)
    if s.get("sparkle"): sparkles(img, t, seed=len(s["text"]))
    for b in s.get("say", []):
        if b.get("who") in pos:
            x, y = pos[b["who"]]; bubble(img, b["text"], x, y - CH - 10, t - b.get("at", 0.3))
        else:
            bubble(img, b["text"], b.get("x", 540), b.get("y", 700), t - b.get("at", 0.3))
    img = camera(img, t, s["dur"])
    top_pill(img, f"STORY #{spec['story_no']}")
    narration_box(img, s["text"], t, s["dur"], s.get("lead", 0.3))
    return img


def s_moral(s, spec, t):
    img, ai = scene_bg(s.get("bg", "park"), spec)
    if not ai: clouds(img, t, s.get("bg", "park"))
    img.alpha_composite(Image.new("RGBA", (W, H), (40, 20, 70, 150)))
    d = ImageDraw.Draw(img)
    f0 = font(56); lab = "STORY LESSON"
    outlined(d, ((W - d.textlength(lab, font=f0)) / 2, 250), lab, f0, (255, 210, 50), sw=6)
    k = ease(t / 0.5); f1 = font(int(lerp(40, 84, k)))
    y = 360
    for ln in wrap(d, s["text"], f1, 920):
        outlined(d, ((W - d.textlength(ln, font=f1)) / 2, y), ln, f1, (255, 255, 255), sw=7); y += int(f1.size * 1.25)
    cast = (spec.get("cast") or ["veer", "veera"])[:2]
    for who, x in zip(cast, (330, 750) if len(cast) > 1 else (540,)):
        spr, cx, cy = kid_frame({"who": who, "x": x, "mood": "happy", "act": "jump"}, t, s["dur"])
        img.alpha_composite(spr, (int(cx - CW / 2), int(cy - CH - 100)))
    sparkles(img, t, seed=9)
    if s.get("question"):
        f2 = font(46); q = wrap(d, s["question"], f2, 860); bh = len(q) * 62 + 60
        d.rounded_rectangle([70, 1380, W - 70, 1380 + bh], 40, fill=(255, 200, 40))
        yy = 1408
        for ln in q:
            d.text(((W - d.textlength(ln, font=f2)) / 2, yy), ln, font=f2, fill=INK); yy += 62
    f3 = font(40, "Medium"); fl = f"Follow {HANDLE} for daily stories"
    outlined(d, ((W - d.textlength(fl, font=f3)) / 2, 1640), fl, f3, (255, 255, 255), sw=4)
    return img


SCENES = {"title": s_title, "story": s_story, "moral": s_moral}


def render(spec, out):
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                             "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for s in spec["scenes"]:
        fn = SCENES[s["type"]]
        for i in range(int(round(s["dur"] * FPS))):
            proc.stdin.write(fn(s, spec, i / FPS).convert("RGB").tobytes())
    proc.stdin.close()
    if proc.wait() != 0: raise RuntimeError("ffmpeg failed while rendering the cartoon")
    return out


def preview_sheet(spec, path):
    thumbs = [SCENES[s["type"]](s, spec, s["dur"] * 0.85).convert("RGB").resize((270, 480)) for s in spec["scenes"]]
    cols = 5; rows = math.ceil(len(thumbs) / cols)
    sheet = Image.new("RGB", (cols * 280, rows * 490), (30, 30, 30))
    for i, th in enumerate(thumbs): sheet.paste(th, ((i % cols) * 280 + 5, (i // cols) * 490 + 5))
    sheet.save(path, quality=85)
