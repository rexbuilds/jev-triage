#!/usr/bin/env python3
"""Wide banner for jev-triage README (1600x600, GitHub-dark terminal style)."""
from PIL import Image, ImageDraw, ImageFont

W, H = 1600, 600
BG = (13, 17, 23)
GREEN = (126, 231, 135)
GRAY = (139, 148, 158)
WHITE = (240, 246, 252)
DIM = (48, 54, 61)
ACCENT = (88, 166, 255)

def mono(size, bold=True):
    name = "DejaVuSansMono-Bold.ttf" if bold else "DejaVuSansMono.ttf"
    try:
        return ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{name}", size)
    except OSError:
        return ImageFont.load_default()

im = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(im)
d.rectangle([20, 20, W - 20, H - 20], outline=(33, 38, 45), width=2)

def center(y, text, font, fill):
    bb = d.textbbox((0, 0), text, font=font)
    d.text(((W - (bb[2] - bb[0])) / 2, y), text, font=font, fill=fill)

center(70, "$ pip install jev-triage", mono(34), GRAY)
center(130, "jev-triage", mono(120), GREEN)
center(295, "fast triage for deep-research agents", mono(44), WHITE)
d.line([(350, 380), (W - 350, 380)], fill=DIM, width=2)
center(405, "query -->> [ jev scores N results ] -->> top-k -->> fetch -->> answer",
       mono(30), ACCENT)
center(450, "70-500ms  |  ~$0.0001  |  the frontier model reads only the shortlist",
       mono(28), GRAY)

im.save("/home/hatch/workspace/jev-triage/assets/banner.png")
print("saved assets/banner.png")
