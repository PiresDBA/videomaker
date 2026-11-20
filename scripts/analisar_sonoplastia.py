# -*- coding: utf-8 -*-
"""analisar_sonoplastia.py - Auditoria de engenharia de som.

Cruza os CUES da sonoplastia com os SEGMENTOS DE VOZ detectados pelo EARSHOT
(relatorio_earshot.json) e aponta melhorias concretas: buracos de efeitos,
sopa de sons, ganhos inaudiveis/mascarantes e desequilibrio por minuto.
"""
from __future__ import annotations
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = Path(r"C:\videomaker\projects\bulldogue-ingles-frida-e-dachshund-marrom-luna-fic")
CUES_JSON = P / "artifacts" / "cues_sonoplastia_pt.json"
VOZ_JSON = Path(r"C:\videomaker\relatorio_earshot.json")
OUT = Path(r"C:\videomaker\relatorio_sonoplastia_melhorias.txt")


def main() -> int:
    linhas: list[str] = []
    def emit(s=""):
        print(s, flush=True)
        linhas.append(str(s))

    if not CUES_JSON.exists():
        emit(f"ERRO: {CUES_JSON} nao encontrado (rode sonoplastia_por_idioma.py)")
        return 2
    if not VOZ_JSON.exists():
        emit(f"ERRO: {VOZ_JSON} nao encontrado (rode analisar_earshot_vad.py)")
        return 2

    cues = json.loads(CUES_JSON.read_text(encoding="utf-8"))
    voz = json.loads(VOZ_JSON.read_text(encoding="utf-8"))
    dur = float(voz.get("duracao", 628.9))
    segs_voz = voz.get("segmentos", [])

    tempos = sorted(float(c["t"]) for c in cues)
    emit("=" * 74)
    emit("AUDITORIA DE SONOPLASTIA - ENGENHARIA DE SOM")
    emit("=" * 74)
    emit(f"Cues analisados      : {len(cues)}")
    emit(f"Duracao do video     : {dur:.2f}s")
    emit(f"Segmentos de voz     : {len(segs_voz)} (earshot)")

    if not tempos:
        emit("ERRO: nenhum cue para analisar")
        return 2

    # densidade por minuto
    emit("\n--- DENSIDADE POR MINUTO ---")
    mins = Counter(int(t // 60) for t in tempos)
    max_m = max(mins) if mins else 0
    for m in range(0, int(dur // 60) + 1):
        n = mins.get(m, 0)
        barra = "#" * min(50, n // 3)
        emit(f"{m:>2}min {n:>3} cues |{barra}")
    emit(f"Media: {len(cues)/(dur/60):.1f} cues/min | pico: {max(mins.values())}/min")

    # buracos sem efeito
    emit("\n--- BURACOS SEM EFEITO (> 5s) ---")
    buracos = []
    cursor = 0.0
    for t in tempos:
        if t - cursor > 5.0:
            buracos.append((cursor, t, t - cursor))
        cursor = max(cursor, t + 0.25)
    if dur - cursor > 5.0:
        buracos.append((cursor, dur, dur - cursor))
    if buracos:
        for ini, fim, tam in sorted(buracos, key=lambda x: -x[2])[:12]:
            emit(f"  {ini:7.1f}s - {fim:7.1f}s  ({tam:5.1f}s SEM EFEITO)")
    else:
        emit("  nenhum buraco > 5s")
    emit(f"Total: {len(buracos)} buracos > 5s")

    # sopa de sons (cues muito juntos)
    emit("\n--- SOPA DE SONS (cues a < 0.08s) ---")
    juntos = [(tempos[i-1], tempos[i]) for i in range(1, len(tempos))
              if tempos[i] - tempos[i-1] < 0.08]
    emit(f"  {len(juntos)} pares muito proximos")
    for a, b in juntos[:6]:
        emit(f"    {a:.2f}s e {b:.2f}s (delta {b-a:.3f}s)")

    # ganhos
    emit("\n--- GANHOS ---")
    ganhos = np.array([float(c["gain"]) for c in cues])
    emit(f"  media={ganhos.mean():.3f} min={ganhos.min():.3f} max={ganhos.max():.3f}")
    baixos = int((ganhos < 0.08).sum())
    altos = int((ganhos > 0.60).sum())
    emit(f"  inaudiveis (<0.08): {baixos} | agressivos (>0.60): {altos}")

    # IDs mais usados
    emit("\n--- IDS MAIS USADOS ---")
    ids = Counter(str(c["id"]) for c in cues)
    for sid, n in ids.most_common(15):
        emit(f"  {sid:32s} {n:>4}")

    # cobertura: janelas de 5s com efeito
    emit("\n--- COBERTURA (janelas de 5s) ---")
    janelas = int(dur // 5) + 1
    com_efeito = 0
    for j in range(janelas):
        ini, fim = j * 5.0, (j + 1) * 5.0
        if any(ini <= t < fim for t in tempos):
            com_efeito += 1
    emit(f"  janelas com efeito: {com_efeito}/{janelas} ({com_efeito/janelas*100:.1f}%)")

    # cruzamento com voz
    emit("\n--- CRUZAMENTO COM VOZ (earshot) ---")
    def em_voz(t: float) -> bool:
        return any(s["inicio"] - 0.1 <= t <= s["fim"] + 0.1 for s in segs_voz)
    dentro = sum(1 for t in tempos if em_voz(t))
    fora = len(tempos) - dentro
    emit(f"  cues DENTRO da fala : {dentro} ({dentro/len(cues)*100:.1f}%)")
    emit(f"  cues FORA da fala   : {fora} ({fora/len(cues)*100:.1f}%)")
    emit("  (cues dentro da fala precisam de DUCKING para nao mascarar a narração)")

    # sugestoes
    emit("\n" + "=" * 74)
    emit("SUGESTOES DE MELHORIA (ENGENHEIRO DE SOM)")
    emit("=" * 74)
    n = 0
    if buracos:
        n += 1
        piores = sorted(buracos, key=lambda x: -x[2])[:3]
        emit(f"{n}. Preencher os {len(buracos)} buracos: " +
             ", ".join(f"{a:.0f}-{b:.0f}s" for a, b, _ in piores) +
             " com bed de ambiente (brisa/passarinhos) em ganho 0.04-0.07.")
    if baixos:
        n += 1
        emit(f"{n}. Subir {baixos} cues inaudiveis (<0.08) para 0.12-0.18 ou removelos.")
    if altos:
        n += 1
        emit(f"{n}. Aplicar DUCKING nos {altos} cues agressivos (>0.60) durante a fala.")
    if len(juntos) > 20:
        n += 1
        emit(f"{n}. Reduzir sopa de sons: {len(juntos)} pares <0.08s. Aumentar dedup para 0.10s.")
    if com_efeito / janelas < 0.85:
        n += 1
        emit(f"{n}. Aumentar cobertura: apenas {com_efeito/janelas*100:.1f}% das janelas tem efeito.")
    n += 1
    emit(f"{n}. Usar earshot para VALIDAR o resultado: re-extrair o mix final e conferir "
         "que os segmentos de voz continuam com confianca > 0.8 (efeitos nao mascaram).")

    OUT.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    emit(f"\nRelatorio salvo: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
