# -*- coding: utf-8 -*-
"""auditoria_cruzar.py - AUDITOR DE SINCRONIA IMAGEM <-> FALA (FLUXO COMPLETO).

Cruza a narração REAL (Whisper) com as imagens posicionadas pelo
build_composition, RESPEITANDO AS REGRAS DO FLUXO (§65, manual):

  1. A transcrição começa em 0 (lead_ms=0 no mix_audio).
  2. O build_composition desloca TODAS as cenas em +INTRO_DUR (8s capa).
     => tempo na composição = tempo_fala + INTRO_DUR.
  3. Cenas com clipe de vídeo (meio) têm regras especiais:
       - 'middle' (s1/bolinha): imagens antes do clipe entram em
         start+frac*dur; imagens DEPOIS do clipe são empurradas +clip_dur.
       - 'hybrid' (s12/osso): inicio=start+clip_dur, dur_imgs=dur-clip_dur.
     => o 'at' precisa ser invertido conforme a regra da cena.

Gera:
  - relatorio_sincronia.txt ( auditoria legível)
  - proposta_novos_at.json (novos at JÁ corrigidos para o fluxo)
  - detalhes.json
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
vc = json.load(open(A / "video_clips.json", encoding="utf-8"))

# constantes do fluxo (MESMAS do build_composition / mix_audio)
INTRO_DUR = float(vc.get("intro_dur", 8.0))  # 8s de capa
MEIOS = {}
for key, val in vc.items():
    if (key == "meio" or key.startswith("meio")) and isinstance(val, dict) and val.get("scene"):
        MEIOS[val["scene"]] = {
            "file": val.get("file", ""),
            "mode": val.get("mode", "hybrid"),
            "clip_dur": float(val.get("clip_dur", 8.0)),
            "offset": float(val.get("offset", 0.0)),
        }


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]", " ", s).split()


# sequencia global de palavras com tempo (audio real, começa em 0)
palavras = []
for seg in tr["segments"]:
    for w in seg.get("words", []):
        for tok in norm(w["w"]):
            if tok:
                palavras.append((tok, w["s"], w["e"]))
seq = [p[0] for p in palavras]


def tempo_palavra(idx):
    if idx < len(palavras):
        return palavras[idx][1], palavras[idx][2]
    return palavras[-1][2], palavras[-1][2]


def at_para_bater(tempo_comp_alvo, sid, start_tl, dur, meio):
    """Inverte a logica do build_composition para achar o 'at' que faz a imagem
    entrar em 'tempo_comp_alvo' (tempo na composicao, ja com INTRO)."""
    start_comp = start_tl + INTRO_DUR
    if not meio:
        frac = (tempo_comp_alvo - start_comp) / dur
    elif meio["mode"] == "hybrid":
        # inicio = start+clip_dur ; dur_imgs = dur-clip_dur
        dur_imgs = dur - meio["clip_dur"]
        frac = (tempo_comp_alvo - start_comp - meio["clip_dur"]) / max(0.1, dur_imgs)
    else:  # middle
        # t = start + frac*dur ; se t >= clip_at -> t += clip_dur
        clip_at = start_comp + meio["offset"]
        if tempo_comp_alvo < clip_at:
            frac = (tempo_comp_alvo - start_comp) / dur
        else:
            frac = (tempo_comp_alvo - start_comp - meio["clip_dur"]) / dur
    return max(0.0, min(1.0, frac))


linhas = []
linhas.append("=" * 110)
linhas.append("AUDITORIA DE SINCRONIA IMAGEM <-> FALA  (FLUXO COMPLETO: +8s capa, clipes)")
linhas.append("=" * 110)
linhas.append(f"Audio real: {tr['duration']:.1f}s | Cenas: {len(tl['timeline'])} | "
              f"INTRO_DUR={INTRO_DUR}s | Clipes meio: {list(MEIOS)}")
linhas.append("")

propostas = {}
total = 0
detalhes = []

# Cenas de CAPA/ENCERRAMENTO tem logica propria no build_composition
# (sub_start usa outro_beats_at[1], textos da capa, etc.). Audita-las e
# mudar seus 'at' QUEBRA o subscribe/capa -> regua do usuario: nunca quebrar
# o fluxo. Por isso sao PULADAS (mantem o at original intacto).
CENAS_ESPECIAIS = {"s_intro", "s_final", "s_outro"}

# proposta inicial ja carrega o at original das cenas especiais (inalterado)
propostas_originais = {sid: list(sc.get(sid, {}).get("at", []))
                       for sid in CENAS_ESPECIAIS if isinstance(sc.get(sid), dict)}

for item in tl["timeline"]:
    sid = item["id"]
    if sid in CENAS_ESPECIAIS:
        propostas[sid] = list(propostas_originais[sid])  # preserva at original
        continue
    t_ini, t_fim = item["start"], item["end"]
    dur = item["duration"]
    cfg = sc.get(sid, {})
    imgs = cfg.get("images", [])
    ats = cfg.get("at")
    beats = cfg.get("beats", [])
    meio = MEIOS.get(sid)
    if not imgs:
        continue
    start_comp = t_ini + INTRO_DUR
    linhas.append(f"\n### {sid} [{start_comp:.1f}-{t_fim+INTRO_DUR:.1f}s comp] "
                  f"dur={dur:.1f} imgs={len(imgs)} beats={len(beats)} "
                  f"clipe={meio['file'] if meio else '-'}")

    # indice das palavras faladas nesta cena (tempo REAL, sem INTRO)
    idx_ini = next((i for i, p in enumerate(palavras) if p[1] >= t_ini - 1), 0)
    idx_fim = next((i for i, p in enumerate(palavras) if p[1] > t_fim + 1), len(palavras))
    sub_seq = seq[idx_ini:idx_fim]
    if not sub_seq:
        continue

    # tempo real de inicio de cada beat (casado por alinhamento de sequencias)
    beats_tempo = []
    cursor = 0
    for b in beats:
        bp = norm(b.get("text", ""))
        matches = difflib.SequenceMatcher(
            None, bp, sub_seq[cursor:], autojunk=False).get_matching_blocks()
        good = [m for m in matches if m.size >= 2]
        if good:
            m = max(good, key=lambda x: x.size)
            off = cursor + m.a
            score = m.size / max(1, len(bp))
        else:
            off = min(cursor, len(sub_seq) - 1)
            score = 0.0
            m = None
        t_real, _ = tempo_palavra(idx_ini + off)
        if beats_tempo and t_real <= beats_tempo[-1][0] + 0.1:
            t_real = beats_tempo[-1][0] + 0.3
        beats_tempo.append((t_real, score, b.get("text", "")))
        cursor = min(off + max(1, m.size if good else 1), len(sub_seq))
        if cursor >= len(sub_seq):
            cursor = len(sub_seq) - 1

    # imagem -> beat (distribui imagens extras dentro do mesmo beat)
    n_img = len(imgs)
    n_beat = len(beats_tempo)
    img_tempo = []
    for i in range(n_img):
        if n_beat == 0:
            img_tempo.append((t_ini + i * dur / max(1, n_img), 0.0, ""))
        else:
            bi = min(int(i * n_beat / n_img), n_beat - 1)
            img_tempo.append(beats_tempo[bi])

    novos_at = []
    for i, img in enumerate(imgs):
        if img.lower().endswith(".mp4"):
            novos_at.append(float(ats[i]) if ats and i < len(ats) else 0.0)
            continue
        frac_atual = float(ats[i]) if ats and i < len(ats) else (i / n_img)
        # tempo atual na composicao, simulando _reveal_time do build_composition
        if meio and meio["mode"] == "middle":
            t_comp_atual = start_comp + frac_atual * dur
            clip_at = start_comp + meio["offset"]
            if t_comp_atual >= clip_at:
                t_comp_atual += meio["clip_dur"]
        elif meio and meio["mode"] == "hybrid":
            t_comp_atual = (start_comp + meio["clip_dur"] +
                            frac_atual * (dur - meio["clip_dur"]))
        else:
            t_comp_atual = start_comp + frac_atual * dur

        t_real, score, btxt = img_tempo[i]
        t_alvo_comp = t_real + INTRO_DUR  # tempo alvo na composicao

        # distribui imagens que compartilham beat ao longo dele
        mesmo = [j for j in range(n_img) if img_tempo[j][0] == t_real]
        if len(mesmo) > 1:
            pos = mesmo.index(i)
            prox = beats_tempo[min(n_beat - 1, beats_tempo.index((t_real, score, btxt)) + 1)][0] if n_beat > 1 else t_fim
            span = max(1.0, prox - t_real)
            t_alvo_comp += span * (pos + 0.5) / len(mesmo)

        frac_novo = at_para_bater(t_alvo_comp, sid, t_ini, dur, meio)
        novos_at.append(round(frac_novo, 4))
        delta = t_comp_atual - t_alvo_comp
        flag = "OK" if abs(delta) < 2.0 else ("ADIANTADA" if delta > 0 else "ATRASADA")
        if abs(delta) >= 2.0:
            total += 1
        linhas.append(f"  [{i}] {img[:36]:36s} comp_atual={t_comp_atual:7.1f}s "
                      f"alvo={t_alvo_comp:7.1f}s delta={delta:+6.1f}s {flag:10s} "
                      f"at {frac_atual:.3f}->{frac_novo:.3f} sc={score:.2f}")
        linhas.append(f"        fala: {btxt[:80]}")
        detalhes.append({"cena": sid, "img": img, "comp_atual": round(t_comp_atual, 2),
                         "alvo": round(t_alvo_comp, 2), "delta": round(delta, 2),
                         "flag": flag, "score": round(score, 2), "fala": btxt})
    propostas[sid] = novos_at

linhas.append("")
linhas.append("=" * 110)
linhas.append(f"TOTAL DE IMAGENS FORA DO TEMPO (>2s): {total}")
linhas.append("=" * 110)

(AUD / "relatorio_sincronia.txt").write_text("\n".join(linhas), encoding="utf-8")
json.dump(propostas, open(AUD / "proposta_novos_at.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
json.dump(detalhes, open(AUD / "detalhes.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("\n".join(linhas[:50]))
print("\nTOTAL:", total)
