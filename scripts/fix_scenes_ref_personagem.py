# -*- coding: utf-8 -*-
"""Adiciona @[Frida]/@[Luna] nos beats do scenes.json (usados pelo lote Flow)."""
from __future__ import annotations
import json, re, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = Path(sys.argv[1] if len(sys.argv) > 1 else
         r"C:\videomaker\projects\bulldogue-ingles-frida-e-dachshund-marrom-luna-fic\artifacts\scenes.json")


def aplicar(t):
    t = re.sub(r"@?\[?(?:Frid[oó]ca|Frida)\]?", "@[Frida]", t, flags=re.I)
    t = re.sub(r"@?\[?(?:Luninha|Luna)\]?", "@[Luna]", t, flags=re.I)
    return t


d = json.loads(P.read_text(encoding="utf-8"))
n = 0
for k, v in d.items():
    if not isinstance(v, dict):
        continue
    for b in v.get("beats", []):
        if isinstance(b, dict) and "text" in b:
            novo = aplicar(b["text"])
            if novo != b["text"]:
                b["text"] = novo
                n += 1
backup = P.with_suffix(".json.bak-refscenes")
if not backup.exists():
    backup.write_text(P.read_text(encoding="utf-8"), encoding="utf-8")
P.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"beats atualizados: {n} -> {P}")
