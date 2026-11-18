# -*- coding: utf-8 -*-
"""auditoria_aplicar.py - Aplica os novos 'at' propostos pelo auditor no
scenes.json. Faz backup antes. Também ajusta 'split' para cenas de 2 imagens.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = Path(r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia")
A = P / "artifacts"
AUD = A / "auditoria"

sc_path = A / "scenes.json"
sc = json.load(open(sc_path, encoding="utf-8"))
novos = json.load(open(AUD / "proposta_novos_at.json", encoding="utf-8"))

# backup
(A / "scenes.json.bak-auditoria").write_text(
    json.dumps(sc, ensure_ascii=False, indent=2), encoding="utf-8")

alteradas = 0
for sid, ats in novos.items():
    cfg = sc.get(sid)
    if not isinstance(cfg, dict) or not ats:
        continue
    imgs = [i for i in cfg.get("images", []) if not i.endswith(".mp4")]
    # so aplica se bater a quantidade de imagens (ignora clipes mp4 no meio)
    if len(ats) != len(cfg.get("images", [])):
        # ajusta: mantem at so para imagens (nao mp4)
        ats_img = []
        k = 0
        for im in cfg.get("images", []):
            if im.endswith(".mp4"):
                ats_img.append(0.0)
            else:
                ats_img.append(ats[k] if k < len(ats) else 0.0)
                k += 1
        ats = ats_img
    cfg["at"] = ats
    if len(ats) == 2:
        cfg["split"] = ats[1]
    alteradas += 1
    print(f"{sid}: {len(ats)} imagens reposicionadas -> {[round(x,3) for x in ats[:4]]}...")

json.dump(sc, open(sc_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"\nOK: {alteradas} cenas atualizadas. Backup: scenes.json.bak-auditoria")
