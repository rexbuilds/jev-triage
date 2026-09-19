#!/usr/bin/env python3
"""Wide banner for jev-triage README (1600x840, GitHub-dark terminal style)."""
from PIL import Image, ImageDraw, ImageFont

W, H = 1600, 840
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
d.rectangle([24, 24, W - 24, H - 24], outline=(33, 38, 45), width=2)

def center(y, text, font, fill):
    bb = d.textbbox((0, 0), text, font=font)
    d.text(((W - (bb[2] - bb[0])) / 2, y), text, font=font, fill=fill)

center(120, "$ pip install jev-triage", mono(40), GRAY)
center(205, "jev-triage", mono(150), GREEN)
center(415, "fast triage for deep-research agents", mono(52), WHITE)
d.line([(300, 520), (W - 300, 520)], fill=DIM, width=2)
center(565, "query -->> [ jev scores N results ] -->> top-k -->> fetch -->> answer",
       mono(32), ACCENT)
center(635, "70-500ms  |  ~$0.0001  |  the frontier model reads only the shortlist",
       mono(34), GRAY)

badges = ["MIT", "python 3.10+", "typesafe jev", "mock mode, no keys needed"]
fnt = mono(32)
widths = []
for b in badges:
    bb = d.textbbox((0, 0), b, font=fnt)
    widths.append(bb[2] - bb[0] + 56)
gap = 18
x = (W - sum(widths) - gap * (len(badges) - 1)) / 2
y = 730
for b, wdt in zip(badges, widths):
    d.rounded_rectangle([x, y - 12, x + wdt, y + 44], radius=18, outline=GREEN, width=2)
    bb = d.textbbox((0, 0), b, font=fnt)
    d.text((x + (wdt - (bb[2] - bb[0])) / 2, y), b, font=fnt, fill=GREEN)
    x += wdt + gap

im.save("/home/hatch/workspace/jev-triage/assets/banner.png")
print("saved assets/banner.png")
