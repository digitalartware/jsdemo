import sys, random, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

DATE = sys.argv[1]
TITLE = sys.argv[2]

W, H = 1024, 1024
img = Image.new("RGB", (W, H), (0, 0, 0))
d = ImageDraw.Draw(img)
cx, cy = W // 2, H // 2

# deterministic palette by date
seed = int(DATE) if DATE.isdigit() else 0
random.seed(seed)

# geometric strokes
for k in range(24):
    hue = (k * 15 + int(DATE[-2:]) * 3) % 360 if DATE.isdigit() else (k * 15) % 360
    r = 80 + k * 16
    n = 3 + (k % 9)
    rot = k * 7
    pts = []
    for i in range(n):
        a = (rot + i * 360 / n) * math.pi / 180.0
        rr = r * (0.78 + 0.22 * abs(math.cos(n * a / 2)) ** 0.7)
        x = cx + math.cos(a) * rr
        y = cy + math.sin(a) * rr
        pts.append((x, y))
    col = (
        int(128 + 127 * math.sin((hue + 0) * math.pi / 180)),
        int(128 + 127 * math.sin((hue + 120) * math.pi / 180)),
        int(128 + 127 * math.sin((hue + 240) * math.pi / 180)),
    )
    d.polygon(pts, outline=col)

# caption
try:
    font = ImageFont.truetype("DejaVuSans.ttf", 26)
except Exception:
    font = ImageFont.load_default()

cap = f"{TITLE} — {DATE}"

def text_size(draw, text, font):
    # Pillow 10+: textbbox exists; older versions fallback
    if hasattr(draw, "textbbox"):
        l, t, r, b = draw.textbbox((0, 0), text, font=font)
        return r - l, b - t
    if hasattr(font, "getsize"):
        return font.getsize(text)
    return (len(text) * 8, 16)

tw, th = text_size(d, cap, font)
d.text((W - 20 - tw, H - 30 - th), cap, fill=(235, 235, 235), font=font)

Path("dist").mkdir(exist_ok=True)
out_path = f"dist/cover-{DATE}.png"
img.save(out_path)
print(out_path)