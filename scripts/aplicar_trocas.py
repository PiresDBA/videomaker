# -*- coding: utf-8 -*-
"""aplicar_trocas.py - aplica plano_trocas.json:
- move a imagem errada para _erradas_2026-11-17/ (preservada)
- copia a nova imagem com o nome da cena
NAO apaga nada.
"""
import json, shutil, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCENES = Path(r"C:\videomaker\projects\a-caminha-nova-que-ninguem-quer-usar\assets\images\gemini\scenes")
NOVAS = SCENES.parent / "_novas_baixadas"
BK = SCENES / "_erradas_2026-11-17"
plano = json.load(open(r"C:\videomaker\plano_trocas.json", encoding="utf-8"))
BK.mkdir(parents=True, exist_ok=True)

for x in plano:
    errada = SCENES / x["errada"]
    nova = SCENES / x["nova"]
    if not nova.exists():
        nova = NOVAS / x["nova"]
    if not nova.exists():
        print("FALTA nova:", nova.name); continue
    if errada.exists():
        shutil.move(str(errada), str(BK / x["errada"]))
    shutil.copy2(str(nova), str(errada))
    print(f"TROCADA {x['errada']} <- {x['nova'][:44]} ({x['secao']}[{x['beat']}])")
print("total:", len(plano))
