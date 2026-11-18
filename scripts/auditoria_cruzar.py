# -*- coding: utf-8 -*-
"""auditoria_cruzar.py - AUDITOR DE SINCRONIA IMAGEM <-> FALA.

Cruza a narração REAL (transcricao Whisper com timestamps de palavras) com
as imagens posicionadas pelo build_composition. Detecta imagens adiantadas/
atrasadas e propõe novos 'at' baseados no tempo REAL falado.

Metodo:
  - Concatena todas as palavras transcritas numa sequencia com tempo.
  - Para cada cena [start,end], pega a subsequencia de palavras faladas nela.
  - Para cada BEAT (texto), usa difflib para achar onde ele comeca nessa
    subsequencia (alinhamento de sequencias, respeitando a ordem).
  - Mapeia beats -> imagens: se N imagens > M beats, distribui as imagens
    extras uniformemente dentro do intervalo do beat correspondente.
  - Gera novo at[i] = (tempo_real_entrada - start_cena) / dur_cena.
"""
from __future__ import annotations
import json, sys, re, unicodedata, difflib
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = Path(r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia")
A = P / "artifacts"
AUD = A / "auditoria"
AUD.mkdir(exist_ok=True)

tl = json.load(open(A / "timeline.json", encoding="utf-8"))
sc = json.load(open(A / "scenes.json", encoding="utf-8"))
tr = json.load(open(AUD / "transcricao.json", encoding="utf-8"))


def norm(s):
    """Remove acentos e pontuacao, mantem so palavras minusculas."""
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]", " ", s).split()


# sequencia global de palavras com tempo
palavras = []
for seg in tr["segments"]:
    for w in seg.get("words", []):
        tw = norm(w["w"])
        for tok in tw:
            if len(tok) > 0:
                palavras.append((tok, w["s"], w["e"]))
seq = [p[0] for p in palavras]


def tempo_palavra(idx):
    if idx < len(palavras):
        return palavras[idx][1], palavras[idx][2]
    return palavras[-1][2], palavras[-1][2]


linhas = []
linhas.append("=" * 104)
linhas.append("AUDITORIA DE SINCRONIA IMAGEM <-> FALA  (transcricao REAL)")
linhas.append("=" * 104)
linhas.append(f"Audio real: {tr['duration']:.1f}s | Cenas: {len(tl['timeline'])} | "
              f"Palavras transcritas: {len(palavras)}")
linhas.append("")

propostas = {}
total = 0
detalhes = []

for item in tl["timeline"]:
    sid = item["id"]
    t_ini, t_fim = item["start"], item["end"]
    dur = item["duration"]
    cfg = sc.get(sid, {})
    imgs = cfg.get("images", [])
    ats = cfg.get("at")
    beats = cfg.get("beats", [])
    if not imgs:
        continue

    # indice das palavras faladas nesta cena (com margem)
    idx_ini = next((i for i, p in enumerate(palavras) if p[1] >= t_ini - 1), 0)
    idx_fim = next((i for i, p in enumerate(palavras) if p[1] > t_fim + 1), len(palavras))
    sub_seq = seq[idx_ini:idx_fim]
    if not sub_seq:
        continue

    linhas.append(f"\n### {sid} [{t_ini:.1f}-{t_fim:.1f}s] dur={dur:.1f} imgs={len(imgs)} beats={len(beats)}")

    # tempo real de inicio de cada beat, casado por alinhamento de sequencias
    beats_tempo = []
    cursor = 0
    for b in beats:
        bp = norm(b.get("text", ""))
        matches = difflib.SequenceMatcher(None, bp, sub_seq[cursor:], autojunk=False).get_matching_blocks()
        # acha o casamento com maior tamanho (ou o primeiro razoavel)
        good = [m for m in matches if m.size >= 2]
        if good:
            m = max(good, key=lambda x: x.size)
            off = cursor + m.a  # inicio do beat dentro de sub_seq
            score = m.size / max(1, len(bp))
        else:
            off = min(cursor, len(sub_seq) - 1)
            score = 0.0
        t_real, _ = tempo_palavra(idx_ini + off)
        # garante ordem crescente
        if beats_tempo and t_real <= beats_tempo[-1][0] + 0.1:
            t_real = beats_tempo[-1][0] + 0.3
        beats_tempo.append((t_real, score, b.get("text", "")))
        cursor = min(off + max(1, m.size if good else 1), len(sub_seq))
        if cursor >= len(sub_seq):
            cursor = len(sub_seq) - 1

    # mapeia beat -> lista de imagens (distribui imagens extras dentro do beat)
    n_img, n_beat = len(imgs), len(beats_tempo)
    imagem_beat = []
    for i in range(n_img):
        if n_beat == 0:
            imagem_beat.append((t_ini + i * dur / max(1, n_img), 0.0, ""))
        else:
            bi = min(int(i * n_beat / n_img), n_beat - 1)
            imagem_beat.append(beats_tempo[bi])

    novos_at = []
    for i, img in enumerate(imgs):
        if img.lower().endswith(".mp4"):
            novos_at.append(float(ats[i]) if ats and i < len(ats) else 0.0)
            continue
        frac_atual = float(ats[i]) if ats and i < len(ats) else (i / n_img)
        t_atual = t_ini + frac_atual * dur
        t_real, score, btxt = imagem_beat[i]
        # distribui imagens que compartilham o mesmo beat ao longo dele
        mesmo = [j for j in range(n_img) if imagem_beat[j][0] == t_real]
        if len(mesmo) > 1:
            pos = mesmo.index(i)
            prox = beats_tempo[min(beats_tempo.index((t_real, score, btxt)) + 1, n_beat - 1)][0] if n_beat > 1 else t_fim
            span = max(1.0, prox - t_real)
            t_real = t_real + span * (pos + 0.5) / len(mesmo)
        frac_real = max(0.0, min(1.0, (t_real - t_ini) / dur))
        novos_at.append(round(frac_real, 4))
        delta = t_atual - t_real
        flag = "OK" if abs(delta) < 2.0 else ("ADIANTADA" if delta > 0 else "ATRASADA")
        if abs(delta) >= 2.0:
            total += 1
        linhas.append(f"  [{i}] {img[:37]:37s} atual={t_atual:7.1f}s real={t_real:7.1f}s "
                      f"delta={delta:+6.1f}s {flag:10s} sc={score:.2f}")
        linhas.append(f"        fala: {btxt[:82]}")
        detalhes.append({"cena": sid, "img": img, "atual": round(t_atual, 2),
                         "real": round(t_real, 2), "delta": round(delta, 2),
                         "flag": flag, "score": round(score, 2), "fala": btxt})
    propostas[sid] = novos_at

linhas.append("")
linhas.append("=" * 104)
linhas.append(f"TOTAL DE IMAGENS FORA DO TEMPO (>2s): {total}")
linhas.append("=" * 104)

(AUD / "relatorio_sincronia.txt").write_text("\n".join(linhas), encoding="utf-8")
json.dump(propostas, open(AUD / "proposta_novos_at.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
json.dump(detalhes, open(AUD / "detalhes.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("\n".join(linhas[:55]))
print("\nTOTAL:", total)
