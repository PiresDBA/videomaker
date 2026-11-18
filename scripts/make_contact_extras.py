# -*- coding: utf-8 -*-
"""Folha de contato das imagens extras (roteiro antigo) para inspecao."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SCENES = Path(r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia\assets\images\gemini\scenes")
names = ["apresentacao_do_canal_scene","o_inicio_da_fala_scene","o_inicio_da_fala_scene_b",
         "reclamacoes_sobre_a_racao_scene","reclamacoes_sobre_a_racao_scene_b",
         "o_misterio_dos_pssios_scene","o_misterio_dos_pssios_scene_b",
         "o_terror_do_veterinario_scene","o_terror_do_veterinario_scene_b",
         "a_verdade_sobre_o_sofa_scene","a_verdade_sobre_o_sofa_scene_b",
         "declaracoes_de_amor_scene","declaracoes_de_amor_scene_b",
         "a_volta_ao_silencio_scene","a_volta_ao_silencio_scene_b"]
cols, rows = 5, 3
tw, th, lh = 340, 220, 40
sheet = Image.new("RGB",(cols*tw, rows*(th+lh)),(20,20,20))
d = ImageDraw.Draw(sheet)
font = ImageFont.load_default()
for i,n in enumerate(names):
    r,c = divmod(i,cols)
    x,y = c*tw, r*(th+lh)
    f = SCENES/(n+".jpg")
    if f.exists():
        im=Image.open(f).convert("RGB"); im.thumbnail((tw-6,th-6))
        sheet.paste(im,(x+3,y+3))
    d.rectangle([x,y+th,x+tw,y+th+lh],fill=(0,0,0))
    d.text((x+4,y+th+4),n[:46],font=font,fill=(255,255,255))
out=SCENES.parent/"contato_extras.jpg"
sheet.save(out,quality=88)
print(out)
