# -*- coding: utf-8 -*-
"""criar_bolha_png.py - cria PNGs de bolha redonda, folha e passaro (transparente)."""
from PIL import Image, ImageDraw
import pathlib
OUT = pathlib.Path(r"C:\videomaker\efeitos_teste2")
OUT.mkdir(exist_ok=True)

# 1) bolha de sabao redonda (40x40)
S = 48
b = Image.new("RGBA", (S, S), (0,0,0,0))
d = ImageDraw.Draw(b)
d.ellipse([2,2,S-3,S-3], fill=(220,240,255,55), outline=(255,255,255,150), width=2)
d.ellipse([10,10,20,20], fill=(255,255,255,160))  # brilho
b.save(OUT/"bolha.png")

# 2) folhinha (verde, 24x14)
f = Image.new("RGBA",(24,14),(0,0,0,0))
d = ImageDraw.Draw(f)
d.ellipse([1,3,22,11], fill=(124,179,66,190), outline=(80,140,40,220))
d.line([3,7,21,7], fill=(60,110,30,200), width=1)
f.save(OUT/"folha.png")

# 3) passarinho (formato de V, 20x10)
p = Image.new("RGBA",(20,10),(0,0,0,0))
d = ImageDraw.Draw(p)
d.line([1,2,10,7], fill=(30,30,30,170), width=2)
d.line([10,7,19,2], fill=(30,30,30,170), width=2)
p.save(OUT/"passaro.png")

# 4) brilho dourado (8x8)
g = Image.new("RGBA",(8,8),(0,0,0,0))
d = ImageDraw.Draw(g)
d.ellipse([1,1,7,7], fill=(255,215,0,200))
g.save(OUT/"brilho.png")
print("PNGs criados")
