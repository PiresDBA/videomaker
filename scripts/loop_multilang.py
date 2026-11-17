# -*- coding: utf-8 -*-
"""
Loop de reprocessamento multi-idioma para o historico de projetos (E:\\videomaker\\projects).

Para cada projeto que falta en/es:
  1. Traduzir roteiro (translate_script.py)  -> script_en.json / script_es.json  (pula se ja existir)
  2. Narração en/es (Gemini TTS)             -> narration/<lang>/sN.wav + timing_<lang>.json
  3. Timeline en/es                          -> timeline.json (reescrito por idioma)
  4. Mix en/es                               -> final_mix_<lang>.m4a
  5. Composição en/es                        -> composition_<lang>.html (titulo no idioma)
  6. Render MP4 en/es                        -> output/<slug>_<lang>.mp4

Nao faz upload ao YouTube (requer credenciais OAuth2).
Nao reprocessa projetos que ja tenham todos os artefatos de um idioma.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = Path(r"E:\videomaker\projects")
FFMPEG_DIR = Path(r"C:\videomaker\ffmpeg\bin")

TRANSLATE = HERE / "translate_script.py"
NARRATION = HERE / "gen_narration_gemini_sections.py"
TIMELINE = HERE / "build_timeline.py"
MIX = HERE / "mix_audio.py"
COMPOSE = HERE / "build_composition.py"
RENDER = HERE / "render.ps1"

TIMEOUT_TRADUCAO = 300  # 5 min (Gemini Web via Chrome CDP)
TIMEOUT_NARRACAO = 600  # 10 min (Gemini TTS)
TIMEOUT_OUTRO = 120  # 2 min (timeline, mix, compose, render)


def run(cmd, label, timeout=TIMEOUT_OUTRO):
    print("== %s: %s" % (label, " ".join(str(c) for c in cmd)), flush=True)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print("   TIMEOUT (%ds) - pulando" % timeout, flush=True)
        return -1
    if r.stdout:
        for line in r.stdout.splitlines():
            if line.strip():
                print("   " + line[:200], flush=True)
    if r.stderr:
        for line in r.stderr.splitlines():
            if line.strip():
                print("   ERR: " + line[:200], flush=True)
    if r.returncode != 0:
        print("   FALHA (rc=%d)" % r.returncode, flush=True)
    return r.returncode


def has_file(p):
    return p.exists() and p.stat().st_size > 0


def missing_for_lang(proj, lang):
    art = proj / "artifacts"
    missing = []
    script_path = art / ("script_%s.json" % lang) if lang != "pt" else art / "script.json"
    timing_path = art / ("narration_timing_%s.json" % lang) if lang != "pt" else art / "narration_timing.json"
    narr_dir = proj / "assets" / "audio" / "narration" / lang
    out_d = proj / "output"
    mp4s = []
    if out_d.is_dir():
        mp4s = [f for f in os.listdir(out_d) if f.endswith("_%s.mp4" % lang)]
    if not has_file(script_path):
        missing.append("script")
    if not has_file(timing_path):
        missing.append("timing")
    if not narr_dir.is_dir() or not any(f.endswith((".wav", ".mp3")) for f in os.listdir(narr_dir)):
        missing.append("narracao")
    if not mp4s:
        missing.append("mp4")
    return missing


def translate(proj, lang):
    art = proj / "artifacts"
    script_pt = art / "script.json"
    out_dir = art
    cmd = [
        sys.executable, str(TRANSLATE),
        "--script", str(script_pt), "--lang", lang, "--out-dir", str(out_dir),
        "--topic", proj.name,
        "--wait", "60",
    ]
    return run(cmd, "traducao %s" % lang, timeout=TIMEOUT_TRADUCAO)


def narration(proj, lang):
    cmd = [
        sys.executable, str(NARRATION),
        "--proj", str(proj), "--lang", lang, "--no-verify",
    ]
    return run(cmd, "narração %s" % lang, timeout=TIMEOUT_NARRACAO)


def timeline(proj, lang):
    cmd = [
        sys.executable, str(TIMELINE),
        "--proj", str(proj), "--lang", lang,
    ]
    return run(cmd, "timeline %s" % lang)


def mix(proj, lang):
    cmd = [
        sys.executable, str(MIX),
        "--proj", str(proj), "--lang", lang,
    ]
    return run(cmd, "mix %s" % lang)


def compose(proj, lang):
    cmd = [
        sys.executable, str(COMPOSE),
        "--timeline", str(proj / "artifacts" / "timeline.json"),
        "--scenes", str(proj / "artifacts" / "scenes.json"),
        "--scenes-dir", str(proj / "scenes"),
        "--proj", str(proj),
        "--out", str(proj / ("composition_%s.html" % lang)),
        "--lang", lang,
    ]
    return run(cmd, "composicao %s" % lang)


def render(proj, lang):
    cmd = [
        "powershell", "-ExecutionPolicy", "Bypass", "-File",
        str(RENDER),
        "-ProjectDir", str(proj),
        "-Slug", proj.name + "_" + lang,
        "-CompFile", str(proj / ("composition_%s.html" % lang)),
        "-MixFile", str(proj / "assets" / "audio" / ("final_mix_%s.m4a" % lang)),
        "-SkipCheck",
    ]
    return run(cmd, "render %s" % lang, timeout=TIMEOUT_OUTRO)


def process_lang(proj, lang):
    """Processa um idioma para um projeto. Retorna True se concluiu."""
    faltando = missing_for_lang(proj, lang)
    if not faltando:
        print("  %s: ja completo" % lang, flush=True)
        return True

    print("  %s: faltando %s" % (lang, ", ".join(faltando)), flush=True)

    if "script" in faltando:
        rc = translate(proj, lang)
        if rc != 0:
            print("  %s: falhou traducao" % lang, flush=True)
            return False

    if "narracao" in faltando:
        rc = narration(proj, lang)
        if rc != 0:
            print("  %s: falhou narracao" % lang, flush=True)
            return False

    if "timing" in faltando:
        rc = timeline(proj, lang)
        if rc != 0:
            print("  %s: falhou timeline" % lang, flush=True)
            return False

    if "mp4" in faltando:
        rc = mix(proj, lang)
        if rc != 0:
            print("  %s: falhou mix" % lang, flush=True)
            return False
        rc = compose(proj, lang)
        if rc != 0:
            print("  %s: falhou composicao" % lang, flush=True)
            return False
        rc = render(proj, lang)
        if rc != 0:
            print("  %s: falhou render" % lang, flush=True)
            return False
        print("  %s: CONCLUIDO" % lang, flush=True)

    return True


def main():
    projects = sorted([d for d in os.listdir(BASE) if (BASE / d).is_dir()])
    print("Projetos encontrados: %d\n" % len(projects), flush=True)

    total_concluidos = 0
    total_falharam = 0
    total_pulados = 0

    for pname in projects:
        proj = BASE / pname
        art = proj / "artifacts"
        if not art.is_dir():
            print("=== %s ===" % pname)
            print("  SEM artifacts/ -> pulando", flush=True)
            print()
            total_pulados += 1
            continue

        script_pt = art / "script.json"
        if not has_file(script_pt):
            print("=== %s ===" % pname)
            print("  SEM script.json (pt) -> nao pode traduzir, pulando", flush=True)
            print()
            total_pulados += 1
            continue

        print("=== %s ===" % pname, flush=True)
        fez_algo = False
        for lang in ("en", "es"):
            faltando = missing_for_lang(proj, lang)
            if not faltando:
                print("  %s: ja completo" % lang, flush=True)
                continue
            fez_algo = True
            ok = process_lang(proj, lang)
            if ok:
                total_concluidos += 1
            else:
                total_falharam += 1

        if not fez_algo:
            print("  (sem nada para fazer)", flush=True)
            total_pulados += 1
        print()
        time.sleep(2)  # pausa entre projetos para nao sobrecarregar a API

    print("=" * 50, flush=True)
    print("Concluidos: %d | Falharam: %d | Pulados: %d" % (total_concluidos, total_falharam, total_pulados), flush=True)


if __name__ == "__main__":
    main()
