#!/usr/bin/env python3
"""One-off generator for winter-the-dolphin kiosk assets (under 2 MB each)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "media" / "assets"
PREVIEWS = ROOT / "media" / "previews"

BAND_COLOR = (10, 42, 58)  # #0A2A3A
TICKER_COLOR = (11, 61, 92)  # #0B3D5C


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def save_thumb(src: Path, thumb_name: str, size: tuple[int, int] = (320, 240)) -> None:
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        if im.mode in ("RGBA", "P"):
            bg = Image.new("RGB", im.size, (24, 48, 64))
            if im.mode == "P":
                im = im.convert("RGBA")
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")
        im.thumbnail(size, Image.Resampling.LANCZOS)
        out = PREVIEWS / thumb_name
        im.save(out, "JPEG", quality=82)


def vertical_gradient(size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size)
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        row = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        for x in range(w):
            px[x, y] = row
    return img


def add_soft_divider(panel: Image.Image, x: int, width: int = 24) -> None:
    overlay = Image.new("RGBA", panel.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for i in range(width):
        alpha = int(90 * (1 - i / width))
        draw.line([(x + i, 0), (x + i, panel.height)], fill=(0, 40, 60, alpha))
    panel_rgba = panel.convert("RGBA")
    panel_rgba.alpha_composite(overlay)
    panel.paste(panel_rgba.convert("RGB"))


def make_hero_bg() -> Path:
    img = vertical_gradient((800, 1080), (30, 120, 170), (8, 45, 85))
    draw = ImageDraw.Draw(img)
    for y in range(0, 1080, 48):
        draw.line([(0, y), (800, y + 40)], fill=(80, 160, 200), width=2)
    draw.ellipse((120, 700, 420, 900), fill=(20, 70, 110))
    draw.ellipse((500, 800, 780, 1000), fill=(15, 60, 100))
    out = ASSETS / "bg-hero-pool.jpg"
    img.save(out, "JPEG", quality=88)
    return out


def make_insights_panel() -> Path:
    img = vertical_gradient((1120, 1080), (20, 95, 115), (6, 52, 72))
    add_soft_divider(img, 0)
    out = ASSETS / "bg-insights-panel.jpg"
    img.save(out, "JPEG", quality=88)
    return out


def make_color_png(path: Path, size: tuple[int, int], color: tuple[int, int, int]) -> Path:
    img = Image.new("RGBA", size, color + (255,))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", optimize=True)
    return path


def draw_dolphin_silhouette(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: tuple[int, int, int]) -> None:
    x0, y0, x1, y1 = box
    body = [
        (x0 + 40, y0 + 120),
        (x0 + 200, y0 + 80),
        (x1 - 120, y0 + 90),
        (x1 - 40, y0 + 130),
        (x1 - 20, y0 + 200),
        (x1 - 80, y0 + 240),
        (x0 + 60, y0 + 220),
    ]
    draw.polygon(body, fill=fill)
    draw.polygon(
        [(x0 + 180, y0 + 70), (x0 + 210, y0 + 20), (x0 + 230, y0 + 85)],
        fill=fill,
    )
    draw.polygon(
        [(x1 - 90, y0 + 170), (x1 - 10, y0 + 140), (x1 - 5, y0 + 210), (x1 - 70, y0 + 250)],
        fill=fill,
    )
    draw.ellipse((x0 + 70, y0 + 130, x0 + 86, y0 + 146), fill=(20, 25, 30))


def raster_icon(draw_fn, size: tuple[int, int] = (900, 400)) -> Image.Image:
    base = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(base)
    draw_fn(draw, size)
    return base


def save_icon(filename: str, draw_fn) -> Path:
    img = raster_icon(draw_fn)
    out = ASSETS / filename
    img.save(out, "PNG", optimize=True)
    return out


def icon_hero(draw: ImageDraw.ImageDraw, size: tuple[int, int]) -> None:
    w, h = size
    draw_dolphin_silhouette(draw, (w // 2 - 280, h // 2 - 140, w // 2 + 280, h // 2 + 140), (180, 195, 205))


def icon_diet(draw: ImageDraw.ImageDraw, size: tuple[int, int]) -> None:
    w, h = size
    draw_dolphin_silhouette(draw, (80, h // 2 - 80, 360, h // 2 + 80), (160, 175, 190))
    for fx, fy in [(420, 120), (500, 200), (580, 160), (660, 220)]:
        draw.ellipse((fx, fy, fx + 70, fy + 35), fill=(220, 170, 90))
        draw.polygon([(fx + 35, fy + 35), (fx + 55, fy + 70), (fx + 15, fy + 70)], fill=(220, 170, 90))


def icon_threat(draw: ImageDraw.ImageDraw, size: tuple[int, int]) -> None:
    w, h = size
    draw.rectangle((w // 2 - 200, 60, w // 2 + 200, h - 60), outline=(200, 80, 80), width=8)
    draw.line([(w // 2 - 150, 100), (w // 2 + 120, h - 120)], fill=(220, 60, 60), width=6)


def icon_fact(draw: ImageDraw.ImageDraw, size: tuple[int, int]) -> None:
    w, h = size
    cx = w // 2
    draw.arc((cx - 120, 80, cx + 120, 200), 200, 340, fill=(120, 200, 240), width=12)
    draw.rectangle((cx - 30, 150, cx + 30, 280), fill=(140, 160, 175))
    draw.polygon([(cx - 80, 280), (cx + 80, 280), (cx, 340)], fill=(140, 160, 175))


def icon_help(draw: ImageDraw.ImageDraw, size: tuple[int, int]) -> None:
    w, h = size
    cx, cy = w // 2, h // 2
    draw.ellipse((cx - 100, cy - 100, cx + 100, cy + 100), fill=(90, 170, 120))
    draw.polygon(
        [(cx - 25, cy - 10), (cx - 25, cy + 60), (cx + 55, cy + 60), (cx + 55, cy - 10)],
        fill=(240, 245, 250),
    )
    draw.rectangle((cx - 5, cy - 50, cx + 25, cy + 20), fill=(240, 245, 250))


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    paths.append(make_hero_bg())
    paths.append(make_insights_panel())
    paths.append(make_color_png(ASSETS / "bg-insights-copy-scrim.png", (1040, 280), BAND_COLOR))
    paths.append(make_color_png(ASSETS / "bg-ticker-scrim.png", (1120, 140), TICKER_COLOR))
    paths.append(save_icon("graphic-winter-id.png", icon_hero))
    paths.append(save_icon("graphic-diet-fish.png", icon_diet))
    paths.append(save_icon("graphic-threat-line.png", icon_threat))
    paths.append(save_icon("graphic-fact-tail.png", icon_fact))
    paths.append(save_icon("graphic-help-rescue.png", icon_help))

    preview_map = {
        "bg-hero-pool.jpg": "bg-hero-pool-thumb.jpg",
        "bg-insights-panel.jpg": "bg-insights-panel-thumb.jpg",
        "bg-insights-copy-scrim.png": "bg-insights-copy-scrim-thumb.jpg",
        "bg-ticker-scrim.png": "bg-ticker-scrim-thumb.jpg",
        "graphic-winter-id.png": "graphic-winter-id-thumb.jpg",
        "graphic-diet-fish.png": "graphic-diet-fish-thumb.jpg",
        "graphic-threat-line.png": "graphic-threat-line-thumb.jpg",
        "graphic-fact-tail.png": "graphic-fact-tail-thumb.jpg",
        "graphic-help-rescue.png": "graphic-help-rescue-thumb.jpg",
    }
    for src_name, thumb in preview_map.items():
        save_thumb(ASSETS / src_name, thumb)

    print("Generated assets:")
    for p in paths:
        print(f"  {p.name}: {p.stat().st_size} bytes sha256={sha256_file(p)}")


if __name__ == "__main__":
    main()