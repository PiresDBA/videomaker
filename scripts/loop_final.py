# -*- coding: utf-8 -*-
"""
Loop automatizado: narração -> timeline -> mix -> composicao -> render
para todos os projetos em E:\videomaker\projects que faltam en/es.

Usa fallback Edge-TTS quando o Gemini TTS nao tem cota.
Gera arquivos por idioma (timeline_<lang>.json, final_mix_<lang>.m4a,
composition_<lang>.html) para nao sobrescrever o PT.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_DEFAULT = Path(r"E:\videomaker\projects")

TIMEOUT_NARRACAO = 600
TIMEOUT_OUTRO = 120


def run(cmd, label, timeout=TIMEOUT_OUTRO):
    print("== %s: %s" % (label, " ".join(str(c) for c in cmd)), flush=True)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print("   TIMEOUT (%ds) - pulando" % timeout, flush=True)
        return -1
    if r.stdout:
        for line in r.stdout.splitlines():
            if line.strip() and not line.startswith("@hf-progress"):
                print("   " + line[:160], flush=True)
    if r.stderr:
        for line in r.stderr.splitlines():
            if line.strip():
                print("   ERR: " + line[:160], flush=True)
    if r.returncode != 0:
        print("   FALHA (rc=%d)" % r.returncode, flush=True)
    return r.returncode


def has_file(p):
    return p.exists() and p.stat().st_size > 0


def missing_for_lang(proj, lang):
    art = proj / "artifacts"
    missing = []
    script_path = art / ("script_%s.json" % lang)
    timing_path = art / ("narration_timing_%s.json" % lang)
    timeline_lang = art / ("timeline_%s.json" % lang)
    narr_dir = proj / "assets" / "audio" / "narration" / lang
    out_d = proj / "output"
    mp4s = [f for f in os.listdir(out_d) if f.endswith("_%s.mp4" % lang)] if out_d.is_dir() else []
    if not has_file(script_path):
        missing.append("script")
    if not has_file(timing_path):
        missing.append("timing")
    if not timeline_lang.exists():
        missing.append("timeline_lang")
    if not narr_dir.is_dir() or not any(f.endswith((".wav", ".mp3")) for f in os.listdir(narr_dir)):
        missing.append("narracao")
    if not mp4s:
        missing.append("mp4")
    return missing


def process_lang(proj, lang):
    faltando = missing_for_lang(proj, lang)
    if not faltando:
        print("  %s: ja completo" % lang, flush=True)
        return True
    print("  %s: faltando %s" % (lang, ", ".join(faltando)), flush=True)

    art = proj / "artifacts"
    script_path = art / ("script_%s.json" % lang)
    audio_dir = proj / "assets" / "audio"

    # 1. Narração (Gemini TTS com fallback Edge-TTS)
    if "narracao" in faltando:
        rc = run([sys.executable, str(HERE / "gen_narration_gemini_sections.py"),
                  "--proj", str(proj), "--lang", lang, "--no-verify"],
                 "narração %s (Gemini)" % lang, timeout=TIMEOUT_NARRACAO)
        if rc != 0:
            print("  %s: Gemini falhou, tentando Edge-TTS fallback" % lang, flush=True)
            rc2 = run([sys.executable, str(HERE / "gen_narration_edge.py"),
                       "--proj", str(proj), "--lang", lang,
                       "--script", str(script_path)],
                      "narração %s (Edge-TTS)" % lang, timeout=TIMEOUT_NARRACAO)
            if rc2 != 0:
                print("  %s: falhou narração (Gemini + Edge)" % lang, flush=True)
                return False
            print("  %s: narração via Edge-TTS OK" % lang, flush=True)
        else:
            print("  %s: narração via Gemini OK" % lang, flush=True)

    # 2. Timeline (sempre regenerar para o idioma correto, se faltar)
    if "timeline_lang" in faltando or "timing" in faltando or "narracao" in faltando:
        rc = run([sys.executable, str(HERE / "build_timeline.py"),
                  "--proj", str(proj), "--lang", lang], "timeline %s" % lang)
        if rc != 0:
            print("  %s: falhou timeline" % lang, flush=True)
            return False
        shutil.copy2(art / "timeline.json", art / ("timeline_%s.json" % lang))
        # Copia narration_full para o idioma
        nf = audio_dir / "narration_full.wav"
        if nf.exists():
            shutil.copy2(nf, audio_dir / ("narration_full_%s.wav" % lang))

    # 3. Mix
    if "mp4" in faltando:
        rc = run([sys.executable, str(HERE / "mix_audio.py"),
                  "--proj", str(proj), "--lang", lang], "mix %s" % lang)
        if rc != 0:
            print("  %s: falhou mix" % lang, flush=True)
            return False
        shutil.copy2(audio_dir / "final_mix.m4a", audio_dir / ("final_mix_%s.m4a" % lang))
        if (proj / "final_mix.m4a").exists():
            shutil.copy2(proj / "final_mix.m4a", proj / ("final_mix_%s.m4a" % lang))

        # 4. Composição
        comp_out = proj / ("composition_%s.html" % lang)
        rc = run([sys.executable, str(HERE / "build_composition.py"),
                  "--timeline", str(art / ("timeline_%s.json" % lang)),
                  "--scenes", str(art / "scenes.json"),
                  "--scenes-dir", str(proj / "scenes"),
                  "--proj", str(proj),
                  "--out", str(comp_out),
                  "--lang", lang], "composicao %s" % lang)
        if rc != 0:
            print("  %s: falhou composicao" % lang, flush=True)
            return False

        # 5. Render
        rc = run(["powershell", "-ExecutionPolicy", "Bypass", "-File",
                  str(HERE / "render.ps1"),
                  "-ProjectDir", str(proj),
                  "-Slug", proj.name + "_" + lang,
                  "-CompFile", str(comp_out),
                  "-MixFile", str(audio_dir / ("final_mix_%s.m4a" % lang)),
                  "-SkipCheck"], "render %s" % lang, timeout=900)
        if rc != 0:
            print("  %s: falhou render" % lang, flush=True)
            return False

        print("  %s: CONCLUIDO" % lang, flush=True)
    return True


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--projects-dir", default=str(BASE_DEFAULT),
                    help="pasta de projetos (padrao: E:\\videomaker\\projects)")
    args = ap.parse_args()
    BASE = Path(args.projects_dir)

    if not BASE.exists():
        print("pasta projects/ nao encontrada: %s" % BASE, flush=True)
        return 1

    projects = sorted([d for d in os.listdir(BASE) if (BASE / d).is_dir()])
    print("Projetos encontrados: %d\n" % len(projects), flush=True)
    concl = falh = pul = 0
    for pname in projects:
        proj = BASE / pname
        art = proj / "artifacts"
        if not art.is_dir():
            print("=== %s ===" % pname)
            print("  SEM artifacts/ -> pulando", flush=True)
            pul += 1
            print()
            continue
        script_pt = art / "script.json"
        if not has_file(script_pt):
            print("=== %s ===" % pname)
            print("  SEM script.json -> pulando", flush=True)
            pul += 1
            print()
            continue
        print("=== %s ===" % pname, flush=True)
        fez = False
        for lang in ("en", "es"):
            faltando = missing_for_lang(proj, lang)
            if not faltando:
                print("  %s: ja completo" % lang, flush=True)
                continue
            fez = True
            ok = process_lang(proj, lang)
            if ok:
                concl += 1
            else:
                falh += 1
        if not fez:
            print("  (sem nada para fazer)", flush=True)
            pul += 1
        print()
        time.sleep(2)
    print("=" * 50, flush=True)
    print("Concluidos: %d | Falharam: %d | Pulados: %d" % (concl, falh, pul), flush=True)


if __name__ == "__main__":
    main()
