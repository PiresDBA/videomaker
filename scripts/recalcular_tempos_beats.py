# -*- coding: utf-8 -*-
r"""recalcular_tempos_beats.py - recalcula os tempos 'at' dos beats para que
cada imagem apareca no instante em que sua FALA e dita na narracao.

Problema: generate_scenes_and_prompts trunca o texto a 400 chars para criar
os beats, mas a narracao fala o texto INTEIRO (~700 chars). Resultado: as
imagens ficam ATRASADAS em relacao a voz (ate ~13s no fim de cada cena).

Solucao: para cada cena, localiza cada beat no texto COMPLETO e recalcula
'at' = posicao do texto / tamanho total. Assim a imagem troca quando a fala
daquele trecho termina.

NAO apaga nem troca imagens: so reescreve o campo 'at' (e 'split') em
artifacts/scenes.json. Faz backup antes.
"""
from __future__ import annotations
import json, sys, shutil
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"C:\videomaker")


def main():
    P = ROOT / "projects/a-caminha-nova-que-ninguem-quer-usar"
    sc_path = P / "artifacts/scenes.json"
    scr = json.load(open(P / "artifacts/script.json", encoding="utf-8"))
    sc = json.load(open(sc_path, encoding="utf-8"))
    shutil.copy2(sc_path, P / "artifacts/scenes.json.bak-tempos")

    texto = {s["id"]: s.get("text", "") for s in scr["sections"]}
    ajustes = 0
    for s in scr["sections"]:
        sid = s["id"]
        cfg = sc.get(sid, {})
        if not isinstance(cfg, dict):
            continue
        full = texto.get(sid, "")
        beats = cfg.get("beats", [])
        at = cfg.get("at", [])
        if not beats or not at or not full:
            continue
        novos_at = []
        busca = 0
        for i, b in enumerate(beats):
            bt = (b.get("text") or "").strip()
            # localiza o beat no texto completo a partir de 'busca'
            idx = full.find(bt, busca)
            if idx < 0 and len(bt) > 20:
                idx = full.find(bt[:20], busca)
            if idx < 0:
                # fallback: distribui uniformemente
                frac = (i + 1) / len(beats)
            else:
                # fim do trecho falado
                fim = idx + len(bt)
                frac = min(1.0, fim / len(full))
                busca = fim
            novos_at.append(round(frac, 4))
        # A PRIMEIRA imagem entra no inicio da cena (at=0). As demais sao
        # deslocadas para manter a ordem e ate 0.92.
        if novos_at:
            novos_at[0] = 0.0
        for i in range(1, len(novos_at)):
            if novos_at[i] <= novos_at[i - 1]:
                novos_at[i] = min(0.95, novos_at[i - 1] + 0.02)
        if novos_at and novos_at[-1] > 0.92:
            novos_at[-1] = 0.92
        if novos_at != at:
            ajustes += 1
            print(f"{sid}: {at} -> {novos_at}")
        cfg["at"] = novos_at
        if len(novos_at) == 2:
            cfg["split"] = novos_at[1]

    json.dump(sc, open(sc_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("secoes ajustadas:", ajustes)


if __name__ == "__main__":
    main()
