# -*- coding: utf-8 -*-
"""make_contact_sheet.py - monta folhas de contato com miniatureas rotuladas.

Uso: python make_contact_sheet.py <padrao_glob> <prefixo_saida> [cols] [rows]
Ex.: python make_contact_sheet.py "*.jpg" contato 5 4
"""
from __future__ import annotations
import sys
from pathlib import Path
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

SCENES = Path(r"C:\videomaker\projects\a-caminha-nova-que-ninguem-quer-usar\assets\images\gemini\scenes")

def main():
    pattern = sys.argv[1] if len(sys.argv) > 1 else "*.jpg"
    prefix = sys.argv[2] if len(sys.argv) > 2 else "contato"
    cols = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    rows = int(sys.argv[4]) if len(sys.argv) > 4 else 4
    per = cols * rows
    files = sorted(SCENES.glob(pattern))
    font = ImageFont.load_default()
    tw, th = 300, 200
    label_h = 46
    page = 0
    for start in range(0, len(files), per):
        chunk = files[start:start+per]
        sheet = Image.new("RGB", (cols*tw, rows*(th+label_h)), (20,20,20))
        d = ImageDraw.Draw(sheet)
        for j, f in enumerate(chunk):
            r, c = divmod(j, cols)
            x, y = c*tw, r*(th+label_h)
            try:
                im = Image.open(f).convert("RGB")
                im.thumbnail((tw-6, th-6))
                sheet.paste(im, (x+3, y+3))
            except Exception:
                pass
            # rotulo: nome curto + indice global
            idx = start + j
            name = f.name
            if len(name) > 42:
                name = name[:39] + "..."
            d.rectangle([x, y+th, x+tw, y+th+label_h], fill=(0,0,0))
            d.text((x+4, y+th+3), f"#{idx:03d}", font=font, fill=(255,220,80))
            d.text((x+4, y+th+20), name, font=font, fill=(255,255,255))
        out = SCENES.parent / f"{prefix}_{page:02d}.jpg"
        sheet.save(out, quality=88)
        print(out)
        page += 1

if __name__ == "__main__":
    main()
