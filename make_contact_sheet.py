# -*- coding: utf-8 -*-
"""Monta contatos (grids) com 20 imagens cada, com o nome em cima, para auditoria visual."""
from pathlib import Path
from PIL import Image, ImageDraw

D = Path(r"C:\videomaker\projects\a-caminha-nova-que-ninguem-quer-usar\assets\images\gemini\scenes")
OUT = Path(r"C:\videomaker\auditoria")
OUT.mkdir(exist_ok=True)
imgs = sorted(D.glob("*.jpg"))
COLS, ROWS = 4, 5
TW, TH = 420, 270
for page in range((len(imgs) + COLS*ROWS - 1)//(COLS*ROWS)):
    sheet = Image.new("RGB", (COLS*TW, ROWS*(TH+24)), "white")
    draw = ImageDraw.Draw(sheet)
    chunk = imgs[page*COLS*ROWS:(page+1)*COLS*ROWS]
    for i, p in enumerate(chunk):
        r, c = divmod(i, COLS)
        x, y = c*TW, r*(TH+24)
        try:
            im = Image.open(p).convert("RGB")
            im.thumbnail((TW, TH))
            sheet.paste(im, (x, y+24))
        except Exception as e:
            draw.text((x+5, y+30), f"ERRO {e}", fill="red")
        draw.text((x+5, y+5), p.stem[:42], fill="black")
    dest = OUT / f"contato_{page+1}.jpg"
    sheet.save(dest, quality=88)
    print(dest, len(chunk))
