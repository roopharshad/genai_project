"""Create test inputs: a scratched black-and-white photo and a stained, faded document."""
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

out = Path("samples")
out.mkdir(exist_ok=True)
random.seed(4)

# Damaged B&W photo
photo = Image.open("GFPGAN-master/inputs/whole_imgs/Blake_Lively.jpg").convert("L")
photo = photo.filter(ImageFilter.GaussianBlur(1.2))
d = ImageDraw.Draw(photo)
for _ in range(14):
    x = random.randint(0, photo.width); y = random.randint(0, photo.height)
    d.line((x, y, x + random.randint(-120, 120), y + random.randint(-260, 260)), fill=random.choice((235, 250, 25)), width=random.choice((1, 2)))
for _ in range(220):
    x = random.randint(0, photo.width); y = random.randint(0, photo.height); r = random.randint(1, 3)
    d.ellipse((x, y, x + r, y + r), fill=random.choice((245, 15)))
arr = np.asarray(photo).astype(np.float32)
arr = arr + np.random.default_rng(1).normal(0, 9, arr.shape)
Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(out / "damaged_bw_photo.jpg", quality=55)

# Faded, stained document
W, H = 900, 640
doc = Image.new("RGB", (W, H), (226, 211, 178))
d = ImageDraw.Draw(doc)
try:
    font = ImageFont.truetype("C:/Windows/Fonts/times.ttf", 24); big = ImageFont.truetype("C:/Windows/Fonts/timesbd.ttf", 34)
except OSError:
    font = big = ImageFont.load_default()
d.text((60, 50), "Legacy System Operations Manual", fill=(92, 80, 62), font=big)
lines = ["Section 4.2  Restoring archived user interface assets.",
         "All toolbar icons must be exported at 32 x 32 pixels before migration.",
         "Screens recorded in 1998 use the original 256-colour palette.",
         "Contact the systems office for access to the backup tapes.",
         "Reference: DOC-1998-114, revision C, approved by the review board."]
for i, t in enumerate(lines):
    d.text((60, 130 + i * 52), t, fill=(105, 92, 72), font=font)
grad = np.linspace(0.75, 1.05, W)[None, :, None]
arr = np.asarray(doc).astype(np.float32) * grad
yy, xx = np.mgrid[0:H, 0:W]
for cx, cy, rad in ((700, 480, 120), (180, 520, 80)):
    arr *= (1 - 0.18 * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * rad ** 2)))[..., None]
arr += np.random.default_rng(2).normal(0, 7, arr.shape)
img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.9))
d = ImageDraw.Draw(img)
for _ in range(150):
    x = random.randint(0, W); y = random.randint(0, H)
    d.ellipse((x, y, x + 2, y + 2), fill=(70, 60, 45))
img.save(out / "faded_document.jpg", quality=60)
print("created", [p.name for p in out.iterdir()])
