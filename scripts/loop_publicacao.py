# -*- coding: utf-8 -*-
"""
Loop de reprocessamento multilíngue com lista de publicação.

Fluxo por projeto (E: historico lento -> C: trabalho rapido -> E:):
  1. Copiar projeto de E:\videomaker\projects para C:\videomaker\projects
  2. Processar en/es: traducao local, narracao (Gemini + fallback Edge-TTS),
     timeline, mix, composicao, render.
  3. Copiar de volta para E:\videomaker\projects (sobreescreve historico).
  4. Registrar na LISTA DE PUBLICACAO (projetos com en/es completos).

Uso:
  python scripts/loop_publicacao.py          # processa todos pendentes
  python scripts/loop_publicacao.py --only <slug>
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
E_BASE = Path(r"E:\videomaker\projects")
C_BASE = Path(r"C:\videomaker\projects")
LOG_PUB = HERE / "LISTA_PUBLICACAO.md"
LOG_PROG = HERE / "LOG_PROGRESSO_MULTILANG.md"

TIMEOUT_NARRACAO = 600
TIMEOUT_RENDER = 900


def run(cmd, label, timeout=120):
    print("== %s: %s" % (label, " ".join(str(c) for c in cmd)), flush=True)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print("   TIMEOUT (%ds)" % timeout, flush=True)
        return -1, ""
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
    return r.returncode, r.stdout


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

    if "narracao" in faltando:
        rc, _ = run([sys.executable, str(HERE / "gen_narration_gemini_sections.py"),
                     "--proj", str(proj), "--lang", lang, "--no-verify"],
                    "narração %s (Gemini)" % lang, timeout=TIMEOUT_NARRACAO)
        if rc != 0:
            print("  %s: Gemini falhou, Edge-TTS fallback" % lang, flush=True)
            rc2, _ = run([sys.executable, str(HERE / "gen_narration_edge.py"),
                          "--proj", str(proj), "--lang", lang,
                          "--script", str(script_path)],
                         "narração %s (Edge-TTS)" % lang, timeout=TIMEOUT_NARRACAO)
            if rc2 != 0:
                print("  %s: falhou narração" % lang, flush=True)
                return False
            print("  %s: Edge-TTS OK" % lang, flush=True)
        else:
            print("  %s: Gemini OK" % lang, flush=True)

    if "timeline_lang" in faltando or "timing" in faltando or "narracao" in faltando:
        rc, _ = run([sys.executable, str(HERE / "build_timeline.py"),
                     "--proj", str(proj), "--lang", lang], "timeline %s" % lang)
        if rc != 0:
            print("  %s: falhou timeline" % lang, flush=True)
            return False
        shutil.copy2(art / "timeline.json", art / ("timeline_%s.json" % lang))
        nf = audio_dir / "narration_full.wav"
        if nf.exists():
            shutil.copy2(nf, audio_dir / ("narration_full_%s.wav" % lang))

    if "mp4" in faltando:
        rc, _ = run([sys.executable, str(HERE / "mix_audio.py"),
                     "--proj", str(proj), "--lang", lang], "mix %s" % lang)
        if rc != 0:
            print("  %s: falhou mix" % lang, flush=True)
            return False
        shutil.copy2(audio_dir / "final_mix.m4a", audio_dir / ("final_mix_%s.m4a" % lang))

        comp_out = proj / ("composition_%s.html" % lang)
        rc, _ = run([sys.executable, str(HERE / "build_composition.py"),
                     "--timeline", str(art / ("timeline_%s.json" % lang)),
                     "--scenes", str(art / "scenes.json"),
                     "--scenes-dir", str(proj / "scenes"),
                     "--proj", str(proj),
                     "--out", str(comp_out),
                     "--lang", lang], "composicao %s" % lang)
        if rc != 0:
            print("  %s: falhou composicao" % lang, flush=True)
            return False

        rc, _ = run(["powershell", "-ExecutionPolicy", "Bypass", "-File",
                     str(HERE / "render.ps1"),
                     "-ProjectDir", str(proj),
                     "-Slug", proj.name + "_" + lang,
                     "-CompFile", str(comp_out),
                     "-MixFile", str(audio_dir / ("final_mix_%s.m4a" % lang)),
                     "-SkipCheck"], "render %s" % lang, timeout=TIMEOUT_RENDER)
        if rc != 0:
            print("  %s: falhou render" % lang, flush=True)
            return False
        print("  %s: CONCLUIDO" % lang, flush=True)
    return True


def processo_projeto(slug):
    """Processa um projeto completo: copia E->C, processa, copia C->E."""
    src = E_BASE / slug
    dst = C_BASE / slug
    if not src.is_dir():
        print("NAO ENCONTRADO em E: %s" % slug, flush=True)
        return False

    print("\n" + "=" * 60, flush=True)
    print("PROJETO: %s" % slug, flush=True)
    print("=" * 60, flush=True)

    # 1. Copiar E: -> C:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    print("Copiado E: -> C:", flush=True)

    proj = C_BASE / slug
    art = proj / "artifacts"
    if not art.is_dir() or not has_file(art / "script.json"):
        print("SEM script.json, pulando", flush=True)
        shutil.rmtree(dst, ignore_errors=True)
        return False

    fez = False
    ok_all = True
    for lang in ("en", "es"):
        faltando = missing_for_lang(proj, lang)
        if not faltando:
            print("  %s: ja completo" % lang, flush=True)
            continue
        fez = True
        ok = process_lang(proj, lang)
        if not ok:
            ok_all = False
            print("  %s: FALHOU" % lang, flush=True)

    if not fez:
        print("  (sem nada para fazer)", flush=True)

    # 2. Copiar C: -> E: (sobreescreve historico)
    if dst.exists():
        shutil.rmtree(src)
        shutil.copytree(dst, src)
        print("Copiado C: -> E: (historico atualizado)", flush=True)
        shutil.rmtree(dst)

    # 3. Registrar na lista de publicacao se en/es completos
    mp4_en = (src / "output" / (slug + "_en.mp4")).exists()
    mp4_es = (src / "output" / (slug + "_es.mp4")).exists()
    if ok_all and mp4_en and mp4_es:
        print("  >> ADICIONADO à LISTA DE PUBLICACAO", flush=True)
        return True
    return False


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="slug de um projeto específico")
    args = ap.parse_args()

    # Lista de projetos pendentes (do LOG_PROGRESSO ou varredura direta)
    pendentes = [
        "teste-10s-dentes-cachorro",
        "teste-gemini-1min",
        "um-dia-na-vida-de-um-cachorro-do-ponto-d",
        "video-educativo-sobre-banho-em-cachorro",
        "video-engracado-sobre-buldogue-ingles-00",
        "video-engracado-sobre-buldogue-ingles-divertido",
        "vira-lata-caramelo-o-heroi-do-brasil",
    ]
    if args.only:
        pendentes = [args.only]

    publicados = []
    falharam = []
    for slug in pendentes:
        ok = processo_projeto(slug)
        if ok:
            publicados.append(slug)
        else:
            falharam.append(slug)

    # Escrever LISTA DE PUBLICACAO
    linhas = ["# LISTA DE PUBLICACAO — Vídeos prontos para upload (EN/ES)\n"]
    linhas.append("Gerado em: %s\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
    linhas.append("Total pronto para publicar: %d\n" % len(publicados))
    for p in publicados:
        linhas.append("- %s (output/%s_en.mp4, output/%s_es.mp4)\n" % (p, p, p))
    if falharam:
        linhas.append("\n## Falharam\n")
        for p in falharam:
            linhas.append("- %s\n" % p)
    LOG_PUB.write_text("".join(linhas), encoding="utf-8")

    print("\n" + "=" * 60, flush=True)
    print("RESUMO FINAL", flush=True)
    print("=" * 60, flush=True)
    print("Publicados (prontos para upload): %d" % len(publicados), flush=True)
    for p in publicados:
        print("  OK: %s" % p, flush=True)
    print("Falharam: %d" % len(falharam), flush=True)
    for p in falharam:
        print("  FALHA: %s" % p, flush=True)
    print("\nLista de publicacao gravada em: %s" % LOG_PUB, flush=True)


if __name__ == "__main__":
    main()
