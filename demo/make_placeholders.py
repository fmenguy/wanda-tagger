"""Draws the placeholder images of the demo and writes their sample data.

    python demo/make_placeholders.py

Every scene is drawn with plain shapes, so the demo ships no real artwork.
"""
import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).parent
W, H = 640, 896


def font(size):
    for name in ("arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def gradient(top, bottom):
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        k = y / (H - 1)
        d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * k) for a, b in zip(top, bottom)))
    return img


def mountains(d, base, color, peaks, seed):
    rnd = random.Random(seed)
    pts = [(0, H)]
    for i in range(peaks + 1):
        x = i * W / peaks
        pts.append((x, base - rnd.randint(60, 260) * (i % 2 == 1)))
    pts.append((W, H))
    d.polygon(pts, fill=color)


def stars(d, n, seed, max_y=H):
    rnd = random.Random(seed)
    for _ in range(n):
        x, y, r = rnd.randint(0, W), rnd.randint(0, max_y), rnd.choice([1, 1, 2])
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 240))


def person(d, cx, top, scale, color):
    head = 70 * scale
    d.ellipse([cx - head, top, cx + head, top + 2 * head], fill=color)
    d.rounded_rectangle([cx - 150 * scale, top + 2.2 * head, cx + 150 * scale, H + 40],
                        radius=int(120 * scale), fill=color)


def scene_sunset_mountains(img, d):
    d.ellipse([W / 2 - 90, 330, W / 2 + 90, 510], fill=(255, 214, 120))
    mountains(d, 640, (92, 54, 98), 4, 1)
    mountains(d, 760, (54, 34, 70), 6, 2)


def scene_portrait(img, d):
    d.ellipse([120, 140, 520, 540], fill=(255, 255, 255, 40), outline=(255, 210, 230), width=4)
    person(d, W / 2, 230, 1.15, (40, 30, 60))


def scene_city_night(img, d):
    stars(d, 60, 3, 380)
    rnd = random.Random(4)
    x = 0
    while x < W:
        w, h = rnd.randint(60, 120), rnd.randint(260, 620)
        d.rectangle([x, H - h, x + w, H], fill=(24, 22, 44))
        for wy in range(H - h + 20, H - 20, 34):
            for wx in range(x + 12, x + w - 16, 24):
                if rnd.random() < 0.45:
                    d.rectangle([wx, wy, wx + 10, wy + 16], fill=rnd.choice([(255, 80, 200), (80, 220, 255), (255, 220, 120)]))
        x += w + rnd.randint(4, 14)


def scene_sea(img, d):
    d.ellipse([W / 2 - 110, 300, W / 2 + 110, 520], fill=(255, 190, 110))
    d.rectangle([0, 470, W, H], fill=(30, 80, 130))
    for i, y in enumerate(range(490, H, 28)):
        amp = 6 + i
        d.line([(x, y + amp * math.sin(x / 40 + i)) for x in range(0, W + 10, 10)], fill=(120, 190, 230), width=3)
    d.polygon([(0, 800), (W, 760), (W, H), (0, H)], fill=(230, 200, 150))


def scene_space(img, d):
    stars(d, 220, 5)
    d.ellipse([140, 260, 500, 620], fill=(230, 120, 70))
    d.ellipse([170, 330, 470, 380], fill=(250, 160, 100))
    d.ellipse([60, 400, 580, 480], outline=(250, 220, 180), width=6)


def scene_forest(img, d):
    rnd = random.Random(6)
    for row, (shade, base) in enumerate([((40, 90, 60), 620), ((24, 66, 44), 760), ((12, 40, 28), H + 40)]):
        for _ in range(9):
            cx, h = rnd.randint(-40, W + 40), rnd.randint(260, 420)
            d.polygon([(cx, base - h), (cx - 70, base), (cx + 70, base)], fill=shade)


def scene_cat(img, d):
    c = (30, 26, 36)
    d.ellipse([170, 470, 470, 860], fill=c)
    d.ellipse([210, 280, 430, 500], fill=c)
    d.polygon([(220, 330), (240, 220), (300, 290)], fill=c)
    d.polygon([(420, 330), (400, 220), (340, 290)], fill=c)
    for ex in (275, 365):
        d.ellipse([ex - 18, 370, ex + 18, 400], fill=(250, 220, 90))
    d.arc([380, 600, 600, 860], 180, 330, fill=c, width=26)


def scene_robot(img, d):
    m = (170, 180, 200)
    d.rounded_rectangle([210, 200, 430, 380], radius=30, fill=m)
    d.ellipse([255, 260, 300, 305], fill=(80, 240, 255))
    d.ellipse([340, 260, 385, 305], fill=(80, 240, 255))
    d.line([(320, 200), (320, 140)], fill=m, width=8)
    d.ellipse([306, 120, 334, 148], fill=(255, 90, 90))
    d.rounded_rectangle([170, 410, 470, 760], radius=40, fill=m)
    d.rectangle([250, 480, 390, 560], fill=(60, 70, 90))


def scene_abstract(img, d):
    rnd = random.Random(9)
    for _ in range(14):
        r = rnd.randint(40, 200)
        x, y = rnd.randint(0, W), rnd.randint(0, H)
        col = rnd.choice([(255, 107, 0), (6, 182, 212), (139, 92, 246), (76, 175, 80), (255, 220, 80)])
        d.ellipse([x - r, y - r, x + r, y + r], outline=col, width=rnd.randint(4, 18))


def scene_rain(img, d):
    scene_city_night(img, d)
    rnd = random.Random(10)
    for _ in range(260):
        x, y = rnd.randint(0, W), rnd.randint(0, H)
        d.line([(x, y), (x - 6, y + 26)], fill=(170, 190, 230), width=1)


def scene_winter(img, d):
    mountains(d, 620, (220, 230, 245), 4, 11)
    mountains(d, 780, (170, 190, 215), 6, 12)
    rnd = random.Random(13)
    for _ in range(160):
        x, y, r = rnd.randint(0, W), rnd.randint(0, H), rnd.randint(2, 5)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255))


def scene_closeup(img, d):
    person(d, W / 2, 120, 2.2, (60, 40, 40))


SCENES = [
    # file, top color, bottom color, drawer, tags already saved, tags "suggested by AI"
    ("01-sunset.jpg", (250, 140, 90), (120, 60, 140), scene_sunset_mountains, ["landscape", "mountain", "sunset", "nature", "realistic"], None),
    ("02-portrait.jpg", (250, 180, 200), (130, 90, 170), scene_portrait, ["portrait", "woman", "studio", "Aurora"], None),
    ("03-city.jpg", (20, 20, 60), (70, 30, 90), scene_city_night, ["city", "night", "neon", "urban", "scifi"], None),
    ("04-sea.jpg", (255, 170, 120), (90, 120, 190), scene_sea, ["sea", "beach", "sunset", "landscape"], None),
    ("05-space.jpg", (8, 8, 30), (30, 20, 70), scene_space, None, ["space", "planet", "scifi", "3D"]),
    ("06-forest.jpg", (170, 210, 180), (60, 120, 90), scene_forest, None, ["forest", "nature", "landscape", "outdoor"]),
    ("07-cat.jpg", (250, 200, 120), (240, 140, 90), scene_cat, None, ["animal", "cat", "minimalist", "portrait"]),
    ("08-robot.jpg", (40, 60, 90), (20, 30, 50), scene_robot, None, ["robot", "scifi", "3D", "full-body"]),
    ("09-abstract.jpg", (30, 30, 40), (10, 10, 20), scene_abstract, None, ["abstract", "colorful", "minimalist"]),
    ("10-rain.jpg", (40, 40, 70), (60, 60, 90), scene_rain, None, ["city", "rain", "night", "urban", "neon"]),
    ("11-winter.jpg", (150, 180, 220), (230, 240, 250), scene_winter, None, ["winter", "mountain", "landscape", "nature"]),
    ("12-closeup.jpg", (200, 160, 120), (110, 70, 60), scene_closeup, None, ["portrait", "close-up", "man", "Aurora"]),
]


def label(img, n):
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle([W / 2 - 150, 40, W / 2 + 150, 120], radius=18, fill=(0, 0, 0, 120))
    d.text((W / 2, 80), f"PLACEHOLDER {n:02d}", font=font(30), fill=(255, 255, 255, 230), anchor="mm")
    d.text((W - 20, H - 20), "wanda-tagger demo", font=font(18), fill=(255, 255, 255, 170), anchor="rs")


def main():
    out = HERE / "images"
    out.mkdir(exist_ok=True)
    metadata, suggestions = {}, {}
    for n, (name, top, bottom, draw, saved, suggested) in enumerate(SCENES, 1):
        img = gradient(top, bottom)
        draw(img, ImageDraw.Draw(img, "RGBA"))
        img = img.filter(ImageFilter.SMOOTH)
        label(img, n)
        img.save(out / name, quality=82, optimize=True)
        key = f"images/{name}"
        suggestions[key] = saved or suggested
        if saved:
            metadata[key] = {"tags": saved}

    (HERE / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    (HERE / "suggestions.json").write_text(json.dumps(suggestions, indent=2) + "\n", encoding="utf-8")
    print(f"{len(SCENES)} placeholders written to {out}")


if __name__ == "__main__":
    main()
