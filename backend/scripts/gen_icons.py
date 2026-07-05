"""Regenerate the "MV" monogram PWA icons from the brand palette.

Requires Pillow (`pip install Pillow` — not a runtime dependency of the app itself,
so it's not in requirements.txt):

    python scripts/gen_icons.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

INK = (34, 29, 24, 255)
CREAM = (242, 236, 225, 255)
TERRACOTTA = (184, 92, 56, 255)

# A serif system font stands in for Playfair Display here — good enough at icon size.
# Adjust this path if it doesn't exist on your machine (e.g. macOS: "/Library/Fonts/Georgia.ttf").
FONT_PATH = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"

OUT_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "icons"


def make_icon(size: int, path: Path, ring_width_ratio: float = 0.028) -> None:
    img = Image.new("RGBA", (size, size), INK)
    draw = ImageDraw.Draw(img)

    margin = size * 0.09
    ring_width = max(2, int(size * ring_width_ratio))
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        outline=TERRACOTTA,
        width=ring_width,
    )

    text = "MV"
    font = ImageFont.truetype(FONT_PATH, int(size * 0.34))
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pos = ((size - text_w) / 2 - bbox[0], (size - text_h) / 2 - bbox[1])
    draw.text(pos, text, font=font, fill=CREAM)

    img.save(path)
    print(f"wrote {path} ({size}x{size})")


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    make_icon(512, OUT_DIR / "icon-512.png")
    make_icon(192, OUT_DIR / "icon-192.png")
    make_icon(180, OUT_DIR / "apple-touch-icon.png")
