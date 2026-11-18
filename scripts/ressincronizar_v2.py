# -*- coding: utf-8 -*-
r"""ressincronizar_v2.py - REGRA DE OURO: imagem = fala, no MESMO instante.

Corrige o ressincronizar anterior:
 - remove beats DUPLICADOS (o agregar_imagens_extras copiou beats);
 - cada imagem casa com o beat de texto correspondente (por ordem apos
   remover duplicatas), e 'at' = posicao real do fim do beat no texto cheio;
 - imagens extras SEM beat proprio ganham o at do beat vizinho mais proximo;
 - imagem 0 entra em 0 (ou no lead real se houver silencio inicial).
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
    (P / "artifacts/scenes.json.bak-ressync2").write_text(
        json.dumps(sc, ensure_ascii=False, indent=2), encoding="utf-8")

    for s in scr["sections"]:
        sid = s["id"]
        cfg = sc.get(sid, {})
        if not isinstance(cfg, dict):
            continue
        full = texto.get(sid, "")
        imgs = [i for i in cfg.get("images", []) if not i.endswith(".mp4")]
        beats = list(cfg.get("beats", []))
        if not imgs or not full:
            continue

        # 1) remove beats duplicados consecutivos (mesmo texto)
        uniq = []
        for b in beats:
            t = b.get("text", "").strip()
            if not uniq or uniq[-1].get("text", "").strip() != t:
                uniq.append(b)
        beats = uniq

        # 2) posicao de cada BEAT no texto completo
        posicoes = []
        busca = 0
        for b in beats:
            bt = b.get("text", "")
            idx = full.find(bt, busca)
            if idx < 0 and len(bt) > 12:
                idx = full.find(bt[:12], busca)
            if idx >= 0:
                frac = min(1.0, (idx + len(bt)) / len(full))
                busca = idx + len(bt)
            else:
                frac = 0.0
            posicoes.append(frac)

        # 3) para cada IMAGEM, escolhe o at:
        #    se ha tantos beats quanto imagens -> at do beat
        #    senao -> distribui as imagens entre as posicoes dos beats
        n = len(imgs)
        ats = []
        if len(beats) == n:
            ats = [round(p, 4) for p in posicoes]
        else:
            # mapeia imagem i para o beat proporcional
            for i in range(n):
                bi = min(int(i * len(beats) / n), len(beats) - 1) if beats else 0
                ats.append(round(posicoes[bi] if posicoes else i / n, 4))
        # imagem 0 sempre no inicio
        if ats:
            ats[0] = 0.0
        # ordem crescente suave (sem saltos artificiais de 0.02)
        for i in range(1, n):
            if ats[i] <= ats[i - 1]:
                ats[i] = min(0.95, ats[i - 1] + 0.015)
        if ats and ats[-1] > 0.95:
            ats[-1] = 0.95

        cfg["beats"] = beats
        cfg["at"] = ats
        if len(ats) == 2:
            cfg["split"] = ats[1]
        print(f"{sid}: {n} imgs, {len(beats)} beats -> at {ats[:5]}...{ats[-1] if ats else '-'}")
    json.dump(sc, open(sc_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("OK")


if __name__ == "__main__":
    main()
