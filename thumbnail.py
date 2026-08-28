"""
Piece 5: Thumbnail Generator
------------------------------------------------------------
Auto-generates a simple, bold text thumbnail from the video title
using Pillow (free, built into Python — no external tool needed).

Output: thumbnail.jpg
"""

import json
from PIL import Image, ImageDraw, ImageFont
import textwrap
import config

def get_font(size: int):
    # Try a common bold system font; fall back to default if not found
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()

def make_thumbnail(title: str, out_path: str = "thumbnail.jpg"):
    W, H = 1080, 1920  # matches Shorts vertical format (also works as a square crop)
    img = Image.new("RGB", (W, H), color=(15, 15, 20))
    draw = ImageDraw.Draw(img)

    # simple diagonal accent for visual interest
    draw.polygon([(0, H), (W, H), (W, H - 400), (0, H - 700)], fill=(37, 99, 235))

    font = get_font(90)
    wrapped = textwrap.fill(title.upper(), width=14)
    lines = wrapped.split("\n")

    line_height = 110
    total_height = line_height * len(lines)
    y = (H - total_height) // 2 - 150

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (W - text_w) // 2
        # outline for readability
        for dx, dy in [(-3,-3),(-3,3),(3,-3),(3,3)]:
            draw.text((x+dx, y+dy), line, font=font, fill=(0,0,0))
        draw.text((x, y), line, font=font, fill=(255, 255, 255))
        y += line_height

    img.save(out_path, quality=95)
    return out_path

def main():
    with open("script.json", "r") as f:
        script_data = json.load(f)

    title = script_data["title"]
    print(f"Generating thumbnail for: {title}")
    make_thumbnail(title)
    print("Saved to thumbnail.jpg")

if __name__ == "__main__":
    main()
