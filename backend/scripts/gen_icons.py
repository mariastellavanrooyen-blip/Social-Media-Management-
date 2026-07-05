"""Regenerate the Marisol CRM homescreen icons: a signature flower motif above
an "MV" monogram, on a soft cream badge with a thin terracotta ring.

Requires Pillow (`pip install Pillow` — not a runtime dependency of the app itself,
so it's not in requirements.txt):

    python scripts/gen_icons.py
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CREAM = (242, 236, 225, 255)
INK = (34, 29, 24, 255)
TERRACOTTA = (184, 92, 56, 255)
TERRACOTTA_SOFT = (196, 116, 84, 255)

# A serif system font stands in for Playfair Display here — good enough at icon size.
# Adjust this path if it doesn't exist on your machine (e.g. macOS: "/Library/Fonts/Georgia.ttf").
FONT_PATH = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"

OUT_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "icons"


def draw_flower(draw, cx, cy, petal_radius, orbit_radius, petal_color, center_color, petals=6):
    for i in range(petals):
        angle = (2 * math.pi / petals) * i
        px = cx + orbit_radius * math.cos(angle)
        py = cy + orbit_radius * math.sin(angle)
        draw.ellipse(
            [px - petal_radius, py - petal_radius, px + petal_radius, py + petal_radius],
            fill=petal_color,
        )
    center_r = petal_radius * 0.55
    draw.ellipse([cx - center_r, cy - center_r, cx + center_r, cy + center_r], fill=center_color)


def make_icon(size: int, path: Path) -> None:
    img = Image.new("RGBA", (size, size), CREAM)
    draw = ImageDraw.Draw(img)

    margin = size * 0.09
    ring_width = max(2, int(size * 0.02))
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        outline=TERRACOTTA_SOFT,
        width=ring_width,
    )

    draw_flower(
        draw,
        cx=size / 2,
        cy=size * 0.36,
        petal_radius=size * 0.052,
        orbit_radius=size * 0.085,
        petal_color=TERRACOTTA,
        center_color=INK,
    )

    text = "MV"
    font = ImageFont.truetype(FONT_PATH, int(size * 0.24))
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (size - text_w) / 2 - bbox[0]
    ty = size * 0.62 - bbox[1]
    draw.text((tx, ty), text, font=font, fill=INK)

    img.save(path)
    print(f"wrote {path} ({size}x{size})")


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    make_icon(512, OUT_DIR / "icon-512.png")
    make_icon(192, OUT_DIR / "icon-192.png")
    make_icon(180, OUT_DIR / "apple-touch-icon.png")
