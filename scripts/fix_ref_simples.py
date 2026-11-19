# -*- coding: utf-8 -*-
"""fix_ref_simples.py - Converte @Frida/@Luna para @Frida/@Luna (sem colchetes).

Regra do usuario (corrigida 2026-11-19): a sintaxe do Flow e SO a arroba,
sem colchetes. Aplicar em prompts, scenes e scripts.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SLUG = "bulldogue-ingles-frida-e-dachshund-marrom-luna-fic"
P = Path(r"C:\videomaker\projects") / SLUG


def aplicar(t):
    if not isinstance(t, str):
        return t
    t = re.sub(r"@\[(Frida|Frid[oó]ca)\]", "@Frida", t, flags=re.I)
    t = re.sub(r"@\[(Luna|Luninha)\]", "@Luna", t, flags=re.I)
    return t


# 1) image_prompts.json
p = P / "artifacts/image_prompts.json"
if p.exists():
    d = json.loads(p.read_text(encoding="utf-8"))
    n = sum(1 for k, v in d.items() if aplicar(v) != v)
    d = {k: aplicar(v) for k, v in d.items()}
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"image_prompts.json: {n} corrigidos")

# 2) scenes.json (beats)
p = P / "artifacts/scenes.json"
if p.exists():
    d = json.loads(p.read_text(encoding="utf-8"))
    n = 0
    for k, v in d.items():
        if isinstance(v, dict):
            for b in v.get("beats", []):
                if isinstance(b, dict) and "text" in b:
                    novo = aplicar(b["text"])
                    if novo != b["text"]:
                        b["text"] = novo
                        n += 1
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"scenes.json: {n} beats corrigidos")

# 3) scripts
for nome, padrao in [
    ("flow_fetch.py", r'DEFAULT_CHARACTERS = "@\[Frida\] e @\[Luna\]"'),
    ("flow_agent_batch.py", r'@\[Frida\]|@\[Luna\]'),
]:
    sp = Path(r"C:\videomaker\scripts") / nome
    if not sp.exists():
        continue
    t = sp.read_text(encoding="utf-8")
    novo = t.replace('@Frida', '@Frida').replace('@Luna', '@Luna')
    if novo != t:
        sp.write_text(novo, encoding="utf-8")
        print(f"{nome}: corrigido")
