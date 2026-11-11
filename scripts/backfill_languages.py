# -*- coding: utf-8 -*-
"""
Backfill de narracao e legendas em idiomas adicionais para projetos ja gerados.

O portugues brasileiro continua sendo o idioma padrao (mix-lang = pt) e o
video final nao e refeito. Este script so adiciona, para cada projeto:
  - traducao do roteiro (script_en.json, script_es.json) via Gemini Web
  - narracao Edge-TTS local em assets/audio/narration/<lang>/sN.mp3
  - artifacts/narration_timing_<lang>.json
  - assets/subtitles/<lang>/<slug>.srt

Uso:
  python scripts/backfill_languages.py                    # todos os projetos
  python scripts/backfill_languages.py --slug frida-luna-fazenda
  python scripts/backfill_languages.py --languages en,es --workers 2
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HERE = Path(__file__).resolve().parent
DEFAULT_PROJECTS_DIR = Path("E:/videomaker/projects")

TRANSLATE = HERE / "translate_script.py"
NARRATION = HERE / "gen_narration_edge.py"
SUBTITLES = HERE / "gen_subtitles.py"

DEFAULT_LANGUAGES = ["en", "es"]


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def run(cmd, label):
    print(f"== {label}", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr)
        raise RuntimeError(f"{label} falhou com rc={r.returncode}")
    for line in r.stdout.splitlines():
        s = line.strip()
        if s.startswith(("==", "   salvo", "TOTAL", "== Legenda", "AVISO")):
            print(line)
    return r


def backfill_project(proj_dir, languages, wait_s=120, workers=4):
    proj_dir = Path(proj_dir)
    script_pt = proj_dir / "artifacts" / "script.json"
    if not script_pt.exists():
        print(f"  pulado (sem script.json): {proj_dir.name}", flush=True)
        return

    print(f"\n## Projeto: {proj_dir.name}", flush=True)

    for lang in languages:
        lang = lang.strip().lower()
        if lang == "pt":
            continue

        script_lang = proj_dir / "artifacts" / f"script_{lang}.json"
        timing_lang = proj_dir / "artifacts" / f"narration_timing_{lang}.json"

        # 1) Traduzir roteiro se nao existir
        if not script_lang.exists():
            print(f"  -> traduzindo roteiro para {lang}...", flush=True)
            run([
                sys.executable, str(TRANSLATE),
                "--script", str(script_pt),
                "--lang", lang,
                "--out-dir", str(proj_dir / "artifacts"),
                "--topic", proj_dir.name,
                "--wait", str(wait_s),
            ], f"traducao {lang}")
        else:
            print(f"  -> script_{lang}.json ja existe, pulando traducao.", flush=True)

        # 2) Narracao Edge-TTS
        print(f"  -> gerando narracao {lang}...", flush=True)
        run([
            sys.executable, str(NARRATION),
            "--proj", str(proj_dir),
            "--lang", lang,
            "--script", str(script_lang),
            "--workers", str(workers),
        ], f"narracao {lang}")

        # 3) Legendas
        out_srt = proj_dir / "assets" / "subtitles" / lang / f"{proj_dir.name}.srt"
        print(f"  -> gerando legenda {lang}...", flush=True)
        run([
            sys.executable, str(SUBTITLES),
            "--script", str(script_lang),
            "--timing", str(timing_lang),
            "--out", str(out_srt),
            "--lang", lang,
        ], f"legenda {lang}")

    print(f"  concluido: {proj_dir.name}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default=None, help="slug de um projeto específico")
    ap.add_argument("--projects-dir", default=None, help="pasta de projetos (padrão: E:/videomaker/projects)")
    ap.add_argument("--languages", default="en,es", help="idiomas a gerar (padrao: en,es)")
    ap.add_argument("--wait", type=int, default=120, help="espera por resposta do Gemini Web (s)")
    ap.add_argument("--workers", type=int, default=4, help="workers para narracao")
    args = ap.parse_args()

    projects_dir = Path(args.projects_dir) if args.projects_dir else DEFAULT_PROJECTS_DIR
    languages = [l.strip().lower() for l in args.languages.split(",") if l.strip()]

    if args.slug:
        proj = projects_dir / args.slug
        if not proj.exists():
            print(f"projeto nao encontrado: {proj}", flush=True)
            return 1
        backfill_project(proj, languages, args.wait, args.workers)
    else:
        if not projects_dir.exists():
            print("pasta projects/ nao encontrada", flush=True)
            return 1
        projetos = sorted([d for d in projects_dir.iterdir() if d.is_dir()])
        print(f"encontrados {len(projetos)} projeto(s) em {projects_dir}", flush=True)
        for proj in projetos:
            backfill_project(proj, languages, args.wait, args.workers)
        for proj in projetos:
            backfill_project(proj, languages, args.wait, args.workers)

    print("\n== Backfill concluido.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
