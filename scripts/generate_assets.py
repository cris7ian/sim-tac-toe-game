#!/usr/bin/env python3
"""Regenerate the favicon family and social card. Requires Pillow, not at runtime."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "TemplateData"
PAPER = "#f4f1e7"
RED = "#b2232b"
TEAL = "#1bbbb0"


def icon(size=1024):
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    s = size / 64
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=14 * s, fill=PAPER)
    for a, b in [((12, 23), (29, 40)), ((12, 40), (29, 23))]:
        draw.line(tuple(v * s for point in (a, b) for v in point), fill=RED, width=round(5 * s))
        for x, y in (a, b):
            draw.ellipse(((x - 2.5) * s, (y - 2.5) * s, (x + 2.5) * s, (y + 2.5) * s), fill=RED)
    draw.ellipse((35 * s, 20 * s, 58 * s, 43 * s), fill=TEAL)
    draw.ellipse((40 * s, 25 * s, 53 * s, 38 * s), fill=PAPER)
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-image", type=Path, required=True, help="An actual 960×600 game screenshot")
    args = parser.parse_args()
    screenshot = Image.open(args.game_image).convert("RGB")
    if screenshot.size != (960, 600):
        parser.error("game screenshot must be 960×600")
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#f4f1e7"/><path d="m12 23 17 17m-17 0 17-17" fill="none" stroke="#b2232b" stroke-width="5" stroke-linecap="round"/><circle cx="46.5" cy="31.5" r="9" fill="none" stroke="#1bbbb0" stroke-width="5"/></svg>'''
    (ASSETS / "favicon.svg").write_text(svg + "\n")
    master = icon()
    for name, size in [("favicon-96.png", 96), ("apple-touch-icon.png", 180)]:
        master.resize((size, size), Image.Resampling.LANCZOS).save(ASSETS / name)
    master.save(ROOT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    # Preserve the old Unity template icon URL for bookmarks and stale browser requests.
    (ASSETS / "favicon.ico").write_bytes((ROOT / "favicon.ico").read_bytes())

    card = Image.new("RGB", (1200, 630), PAPER)
    draw = ImageDraw.Draw(card)
    title_font = ImageFont.truetype(str(ASSETS / "fonts/FreeSerif.ttf"), 52)
    draw.text((190, 20), "Sim Tac Toe", font=title_font, fill="#33362f")
    badge = master.resize((64, 64), Image.Resampling.LANCZOS)
    card.paste(badge, (940, 19), badge)
    draw.rounded_rectangle((180, 91, 1020, 621), radius=13, fill="#e9e7d9", outline="#d5d4c3", width=1)
    card.paste(screenshot.resize((816, 510), Image.Resampling.LANCZOS), (192, 101))
    card.save(ASSETS / "social-preview.jpg", quality=90, optimize=True)
    print("Generated SVG, ICO, 96px and 180px icons, and a 1200×630 social preview.")


if __name__ == "__main__":
    main()
