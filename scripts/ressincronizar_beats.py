# -*- coding: utf-8 -*-
r"""ressincronizar_beats.py - REGRA DE OURO (MANUAL §65): imagem = fala no mesmo instante.

Recalcula o campo 'at' de cada cena usando a posicao REAL de cada beat no
texto COMPLETO falado (script.json), em vez de distribuir uniformemente.

Para cada beat i:
  - localiza o texto do beat no texto completo da secao;
  - at[i] = (posicao_do_fim_do_beat / tamanho_do_texto)
  - imagem 0 entra em 0 (inicio da cena)
  - garante ordem crescente e ultimo <= 0.95
"""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SLUG = sys.argv[1] if len(sys.argv) > 1 else "e-se-os-cachorros-pudessem-falar-por-um-dia"
P = Path(r"C:\videomaker\projects") / SLUG


def main():
    sc_path = P / "artifacts/scenes.json"
    sc = json.load(open(sc_path, encoding="utf-8"))
    scr = json.load(open(P / "artifacts/script.json", encoding="utf-8"))
    texto = {s["id"]: s.get("text", "") for s in scr["sections"]}
    (P / "artifacts/scenes.json.bak-ressync").write_text(
        json.dumps(sc, ensure_ascii=False, indent=2), encoding="utf-8")

    for s in scr["sections"]:
        sid = s["id"]
        cfg = sc.get(sid, {})
        if not isinstance(cfg, dict):
            continue
        full = texto.get(sid, "")
        beats = cfg.get("beats", [])
        imgs = [i for i in cfg.get("images", []) if not i.endswith(".mp4")]
        if not beats or not imgs or not full:
            continue
        novos = []
        busca = 0
        for i in range(len(imgs)):
            if i == 0:
                novos.append(0.0)
                continue
            bt = beats[min(i, len(beats) - 1)].get("text", "")
            idx = full.find(bt, busca)
            if idx < 0 and len(bt) > 12:
                idx = full.find(bt[:12], busca)
            if idx < 0:
                # fallback uniforme
                frac = i / len(imgs)
            else:
                frac = min(1.0, (idx + len(bt)) / len(full))
                busca = idx + len(bt)
            novos.append(round(frac, 4))
        # ordem crescente (cada imagem pelo menos 0.02 depois da anterior)
        for i in range(1, len(novos)):
            if novos[i] <= novos[i - 1] + 0.01:
                novos[i] = min(0.95, novos[i - 1] + 0.02)
        if novos and novos[-1] > 0.95:
            novos[-1] = 0.95
        cfg["at"] = novos
        if len(novos) == 2:
            cfg["split"] = novos[1]
        print(f"{sid}: {len(imgs)} imgs -> at {novos[:4]}...{novos[-1] if novos else '-'}")
    json.dump(sc, open(sc_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("ressincronizado")


if __name__ == "__main__":
    main()
