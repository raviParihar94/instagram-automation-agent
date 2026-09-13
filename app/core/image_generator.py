"""
Renders a simple classic-meme-style image (top/bottom bold caption text over
a background) entirely locally and for free using Pillow. Drop your own
background templates into data/assets/ — one is picked at random, or by
content_type-matching filename prefix if present.
"""
import os
import random
import textwrap
import time
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "assets")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "generated")
CANVAS_SIZE = (1080, 1080)  # Instagram square post size


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _pick_background() -> Image.Image:
    os.makedirs(ASSETS_DIR, exist_ok=True)
    files = [f for f in os.listdir(ASSETS_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    if files:
        img = Image.open(os.path.join(ASSETS_DIR, random.choice(files))).convert("RGB")
        return img.resize(CANVAS_SIZE)
    # No template supplied yet: fall back to a plain solid-color canvas so the
    # pipeline still works out of the box.
    color = random.choice([(30, 30, 40), (20, 60, 50), (50, 30, 60), (60, 45, 20)])
    return Image.new("RGB", CANVAS_SIZE, color)


def _draw_wrapped_text(draw, text, y, font, canvas_width, fill="white", stroke_fill="black"):
    wrapped = textwrap.fill(text.upper(), width=22)
    lines = wrapped.split("\n")
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font, stroke_width=4)
        w = bbox[2] - bbox[0]
        x = (canvas_width - w) / 2
        draw.text((x, y), line, font=font, fill=fill, stroke_width=4, stroke_fill=stroke_fill)
        y += (bbox[3] - bbox[1]) + 10
    return y


def generate_meme_image(top_text: str, bottom_text: str = "") -> str:
    img = _pick_background()
    draw = ImageDraw.Draw(img)
    font = _load_font(60)

    if top_text:
        _draw_wrapped_text(draw, top_text, y=40, font=font, canvas_width=CANVAS_SIZE[0])
    if bottom_text:
        # Rough bottom anchor; good enough for a prototype.
        _draw_wrapped_text(draw, bottom_text, y=CANVAS_SIZE[1] - 260, font=font, canvas_width=CANVAS_SIZE[0])

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, f"post_{int(time.time())}.png")
    img.save(out_path)
    return out_path
