# -*- coding: utf-8 -*-
"""criar_patch.py - patch opaco (gramado + bolinha) para cobrir a marca d'agua."""
from PIL import Image, ImageDraw

W, H = 140, 55
img = Image.new("RGBA", (W, H), (92, 128, 48, 255))  # verde gramado
d = ImageDraw.Draw(img)
# textura simples de grama
import random
random.seed(42)
for _ in range(120):
    x = random.randint(0, W); y = random.randint(0, H)
    d.line([x, y, x+random.randint(-3,3), y-random.randint(3,8)],
           fill=(random.randint(70,130), random.randint(110,160), random.randint(30,70), 255), width=1)
# bolinha amarela
cx, cy, r = W//2, H//2, 17
d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(255, 215, 95, 255), outline=(255,255,255,230), width=2)
d.ellipse([cx-r+5, cy-r+5, cx-2, cy-2], fill=(255, 242, 185, 200))
img.save(r"C:\videomaker\patch_bolinha.png")
print("patch opaco criado")
