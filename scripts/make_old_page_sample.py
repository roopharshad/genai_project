"""Create a test image like a photo of an old book page: dark table, yellowed, creased, stained paper."""
import random

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

random.seed(7)
rng = np.random.default_rng(7)
W, H = 1024, 576
table = (rng.normal(35, 10, (H, W, 3))).clip(0, 255).astype(np.uint8)

pw, ph = 760, 520
page = Image.new("RGB", (pw, ph), (190, 165, 120))
d = ImageDraw.Draw(page)
try:
    f = ImageFont.truetype("C:/Windows/Fonts/times.ttf", 22); fb = ImageFont.truetype("C:/Windows/Fonts/timesbd.ttf", 30)
except OSError:
    f = fb = ImageFont.load_default()
d.text((40, 30), "Chapter III. The Old Archive", fill=(80, 62, 40), font=fb)
words = "the records of the old office were kept in leather books and every page was written by hand with care".split()
for i in range(15):
    d.text((40, 85 + i * 28), " ".join(random.choice(words) for _ in range(11)), fill=(95, 76, 52), font=f)
arr = np.asarray(page).astype(np.float32)
yy, xx = np.mgrid[0:ph, 0:pw]
for _ in range(6):  # stains
    cx, cy, r = random.randint(0, pw), random.randint(0, ph), random.randint(40, 140)
    arr *= (1 - 0.25 * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r)))[..., None]
for _ in range(5):  # creases: dark/light ridges
    x0 = random.randint(0, pw); ang = random.uniform(-0.6, 0.6)
    dist = (xx - x0 - (yy - ph / 2) * ang)
    arr *= (1 - 0.18 * np.exp(-dist ** 2 / 30) + 0.08 * np.exp(-(dist - 4) ** 2 / 20))[..., None]
arr *= np.linspace(1.0, 0.8, pw)[None, :, None]  # shading
arr += rng.normal(0, 8, arr.shape)
page = np.clip(arr, 0, 255).astype(np.uint8)
page = cv2.GaussianBlur(page, (0, 0), 1.1)
for _ in range(250):
    cv2.circle(page, (random.randint(0, pw), random.randint(0, ph)), random.randint(1, 2), (60, 45, 30), -1)

src = np.float32([[0, 0], [pw, 0], [pw, ph], [0, ph]])
dst = np.float32([[140, 30], [900, 20], [930, 560], [120, 550]])
M = cv2.getPerspectiveTransform(src, dst)
warped = cv2.warpPerspective(page, M, (W, H))
mask = cv2.warpPerspective(np.full((ph, pw), 255, np.uint8), M, (W, H))
out = np.where(mask[..., None] > 0, warped, table)
Image.fromarray(out).save("samples/old_book_page.jpg", quality=70)
print("samples/old_book_page.jpg")
