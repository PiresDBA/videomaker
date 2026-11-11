# -*- coding: utf-8 -*-
"""
Publicação multilíngue (PT / EN / ES) para projetos já renderizados.

Fluxo por projeto:
  1. Backfill de narração + legendas em EN e ES (backfill_languages.py)
  2. Re-render do vídeo em EN  (--mix-lang en) -> output/<slug>_en.mp4
  3. Re-render do vídeo em ES  (--mix-lang es) -> output/<slug>_es.mp4
  4. Upload de cada vídeo para o YouTube com título/descrição/tags no idioma

O vídeo PT original (output/<slug>.mp4) é mantido como está.

Uso:
  python scripts/publish_multilang.py                      # todos os projetos com MP4
  python scripts/publish_multilang.py --slug frida-luna-fazenda
  python scripts/publish_multilang.py --dry-run            # só mostra o que faria
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECTS_DIR = HERE.parent / "projects"

BACKFILL = HERE / "backfill_languages.py"
PIPELINE = HERE / "pipeline.py"
UPLOAD = HERE / "youtube_upload.py"


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def run(cmd, label):
    print(f"== {label}", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:] if len(r.stdout) > 2000 else r.stdout)
        print(r.stderr[-2000:] if len(r.stderr) > 2000 else r.stderr)
        raise RuntimeError(f"{label} falhou com rc={r.returncode}")
    for line in r.stdout.splitlines():
        s = line.strip()
        if s.startswith(("==", "   salvo", "TOTAL", "== Legenda", "== FASE", "== PIPELINE", "== VIDEO", "UPLOAD", "VIDEO", "STATUS")):
            print(line)
    return r


def get_title_pt(proj_dir):
    script_pt = proj_dir / "artifacts" / "script.json"
    if script_pt.exists():
        s = load_json(script_pt)
        return s.get("title", proj_dir.name) or proj_dir.name
    return proj_dir.name


def get_storyline(proj_dir, lang):
    """Extrai o enredo (seções de conteúdo) do script para a descrição."""
    script_path = proj_dir / "artifacts" / f"script_{lang}.json" if lang != "pt" else proj_dir / "artifacts" / "script.json"
    if not script_path.exists():
        return ""
    s = load_json(script_path)
    partes = [sec.get("text", "") for sec in s.get("sections", [])
              if sec.get("id") not in ("s_intro", "s0", "s_outro")]
    return " ".join(partes)[:500]


def build_description(title, storyline, lang):
    """Gera descrição no padrão do canal para um idioma."""
    from description_template import build_description as bd
    hook_index = {"pt": 0, "en": 1, "es": 2}.get(lang, 0)
    return bd(title, storyline, hook_index=hook_index)


def render_lang(proj_slug, lang, dry_run=False):
    """Re-renderiza o projeto para um idioma específico."""
    proj_dir = PROJECTS_DIR / proj_slug
    output = proj_dir / "output"
    mp4_current = output / f"{proj_slug}.mp4"
    mp4_lang = output / f"{proj_slug}_{lang}.mp4"

    if dry_run:
        print(f"    [DRY-RUN] re-render {lang}: {mp4_lang.name}")
        return

    # Primeiro, garante que o MP4 atual está no disco (o pipeline pode sobrescrever)
    # O pipeline sempre grava output/<slug>.mp4
    run([
        sys.executable, str(PIPELINE),
        "resume", "--slug", proj_slug,
        "--from", "narration",
        "--force",
        "--languages", lang,
        "--subtitle-languages", lang,
        "--mix-lang", lang,
        "--provider", "procedural",
        "--narration-provider", "edge",
        "--skip-check",
    ], f"render {lang} {proj_slug}")

    # O pipeline gravou output/<slug>.mp4 com o áudio do idioma
    if mp4_current.exists() and not mp4_lang.exists():
        shutil.move(str(mp4_current), str(mp4_lang))
        print(f"    renomeado para {mp4_lang.name}", flush=True)


def publish_lang(proj_slug, lang, mp4_file, title, storyline, dry_run=False):
    """Faz upload de um vídeo para o YouTube."""
    if not mp4_file.exists():
        print(f"    pulado (arquivo não existe): {mp4_file.name}", flush=True)
        return

    if dry_run:
        print(f"    [DRY-RUN] upload {lang}: {mp4_file.name}")
        return

    lang_code = {"pt": "pt-BR", "en": "en-US", "es": "es-ES"}[lang]
    desc = build_description(title, storyline, lang)
    tags = "cachorro,animacao,infantil,frida,luna,cachorrinho,desenhoanimado,videoengraçado,conteúdocriativo,petspride,familia,criancas"

    run([
        sys.executable, str(UPLOAD),
        "--video", str(mp4_file),
        "--title", title,
        "--description", desc,
        "--tags", tags,
        "--category", "24",
        "--privacy", "public",
        "--made-for-kids",
        "--default-language", lang_code,
        "--default-audio-language", lang_code,
    ], f"upload {lang} {mp4_file.name}")


def publish_project(proj_slug, dry_run=False):
    proj_dir = PROJECTS_DIR / proj_slug
    if not proj_dir.exists():
        print(f"Projeto não encontrado: {proj_slug}", flush=True)
        return 1

    output = proj_dir / "output"
    mp4_pt = output / f"{proj_slug}.mp4"
    if not mp4_pt.exists():
        print(f"  pulado (sem MP4 final): {proj_slug}", flush=True)
        return 0

    print(f"\n{'='*70}")
    print(f"PROJETO: {proj_slug}")
    print(f"{'='*70}", flush=True)

    title_pt = get_title_pt(proj_dir)

    # Se ja tem os 3 MP4s, considera o projeto ja processado e pula.
    mp4_en = output / f"{proj_slug}_en.mp4"
    mp4_es = output / f"{proj_slug}_es.mp4"
    if mp4_pt.exists() and mp4_en.exists() and mp4_es.exists():
        print(f"  pulado (ja processado: PT, EN e ES ja existem)", flush=True)
        return 0

    # 1) Backfill de narração + legendas EN e ES
    print("  [1/4] Backfill de idiomas EN e ES...", flush=True)
    if not dry_run:
        run([
            sys.executable, str(BACKFILL),
            "--slug", proj_slug,
            "--languages", "en,es",
            "--workers", "4",
        ], f"backfill {proj_slug}")

    # 2) Fazer backup do PT antes de re-renderizar
    mp4_pt_backup = output / f"{proj_slug}_pt.mp4"
    if dry_run:
        print(f"    [DRY-RUN] backup PT: {mp4_pt_backup.name}")
    else:
        if not mp4_pt_backup.exists():
            shutil.copy2(str(mp4_pt), str(mp4_pt_backup))
            print(f"    backup PT salvo: {mp4_pt_backup.name}", flush=True)

    # 3) Re-render em EN
    print("  [2/4] Re-render em inglês...", flush=True)
    render_lang(proj_slug, "en", dry_run)

    # 4) Re-render em ES
    print("  [3/4] Re-render em espanhol...", flush=True)
    render_lang(proj_slug, "es", dry_run)

    # 5) Restaurar o MP4 PT original
    if not dry_run and mp4_pt_backup.exists() and not mp4_pt.exists():
        shutil.copy2(str(mp4_pt_backup), str(mp4_pt))
        print(f"    PT restaurado: {mp4_pt.name}", flush=True)

    # 6) Upload de cada vídeo
    print("  [4/4] Upload para o YouTube...", flush=True)
    for lang, mp4_file in [("pt", mp4_pt), ("en", output / f"{proj_slug}_en.mp4"), ("es", output / f"{proj_slug}_es.mp4")]:
        storyline = get_storyline(proj_dir, lang)
        publish_lang(proj_slug, lang, mp4_file, title_pt, storyline, dry_run)

    print(f"  concluído: {proj_slug}", flush=True)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default=None, help="projeto específico")
    ap.add_argument("--dry-run", action="store_true", help="só mostra o que faria")
    args = ap.parse_args()

    if args.slug:
        return publish_project(args.slug, args.dry_run)

    projetos = sorted([d for d in PROJECTS_DIR.iterdir() if d.is_dir()])
    total = 0
    for proj in projetos:
        output = proj / "output"
        if output.exists() and list(output.glob("*.mp4")):
            total += 1

    print(f"Encontrados {total} projeto(s) com MP4 final.", flush=True)
    for proj in projetos:
        output = proj / "output"
        if output.exists() and list(output.glob("*.mp4")):
            publish_project(proj.name, args.dry_run)

    print(f"\n== Publicação multilíngue concluída ({total} projeto(s)).", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
