# -*- coding: utf-8 -*-
"""
Gera arquivos de legenda (.srt) a partir do script.json e do
narration_timing_<lang>.json (duracao real de cada secao).

Cada secao vira um bloco de legenda com timestamp de inicio/fim calculado
a partir do cursor acumulado (duracoes + gap entre secoes).

Uso:
  python scripts/gen_subtitles.py --script artifacts/script_pt.json --timing artifacts/narration_timing_pt.json --out assets/subtitles/pt/video.srt --lang pt
  python scripts/gen_subtitles.py --proj projects/<slug> --lang en,es --out-dir assets/subtitles

Saida:
  assets/subtitles/<lang>/<slug>.srt
"""
import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def fmt_srt(seconds):
    """Converte segundos para formato SRT: HH:MM:SS,mmm"""
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def limpar_legenda(text):
    """Limpa texto para legenda: remove espacos duplicados, normaliza."""
    if not text:
        return ""
    text = " ".join(text.split())
    return text


def gerar_srt(script_path, timing_path, out_path, gap_seconds=0.6):
    script = load_json(script_path)
    timing = load_json(timing_path)

    # Mapa id -> duracao
    dur_map = {item["id"]: float(item.get("duration", 0)) for item in timing}

    sections = script.get("sections", [])
    blocos = []
    cursor = 0.0
    indice = 1

    for s in sections:
        sid = s.get("id", "")
        texto = limpar_legenda(s.get("text", ""))
        if not texto:
            continue
        dur = dur_map.get(sid, 0.0)
        if dur <= 0:
            # sem duracao real, pula (nao pode criar legenda sem tempo)
            continue
        start = cursor
        end = cursor + dur
        bloco = (
            f"{indice}\n"
            f"{fmt_srt(start)} --> {fmt_srt(end)}\n"
            f"{texto}\n"
        )
        blocos.append(bloco)
        indice += 1
        cursor = end + gap_seconds

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(blocos).strip() + "\n", encoding="utf-8")
    print(f"== Legenda gerada: {out_path} ({len(blocos)} blocos)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proj", default=None, help="diretorio do projeto (senao vem de config.json)")
    ap.add_argument("--script", default=None, help="caminho do script JSON (padrao: artifacts/script_<lang>.json)")
    ap.add_argument("--timing", default=None, help="caminho do narration_timing_<lang>.json")
    ap.add_argument("--out", default=None, help="caminho do arquivo .srt de saida")
    ap.add_argument("--out-dir", default=None, help="pasta de saida dos .srt (padrao: assets/subtitles/<lang>/)")
    ap.add_argument("--lang", required=True, help="idioma (pt, en, es)")
    ap.add_argument("--gap", type=float, default=0.6, help="gap entre secoes (s)")
    args = ap.parse_args()

    cfg = load_json(HERE / "config.json")
    proj = (Path(args.proj) if args.proj else (HERE / cfg.get("project_dir", ".."))).resolve()
    lang = args.lang.lower().strip()
    artifacts = proj / "artifacts"

    if args.script:
        script_path = Path(args.script)
    else:
        script_path = artifacts / f"script_{lang}.json" if lang != "pt" else artifacts / "script.json"
    if not script_path.exists():
        print(f"FALTA script: {script_path}")
        return 2

    if args.timing:
        timing_path = Path(args.timing)
    else:
        timing_path = artifacts / f"narration_timing_{lang}.json"
    if not timing_path.exists():
        print(f"FALTA timing: {timing_path}")
        return 2

    if args.out:
        out_path = Path(args.out)
    elif args.out_dir:
        out_path = Path(args.out_dir) / lang / f"{proj.name}.srt"
    else:
        out_path = proj / "assets" / "subtitles" / lang / f"{proj.name}.srt"

    return gerar_srt(script_path, timing_path, out_path, args.gap)


if __name__ == "__main__":
    import sys
    sys.exit(main())
