# -*- coding: utf-8 -*-
"""
Publicação multilíngue (PT / EN / ES) para projetos já renderizados.

Fluxo por projeto:
  1. Backfill de narração + legendas em EN e ES (backfill_languages.py)
  2. Re-render do vídeo em EN  (--mix-lang en) -> output/<slug>_en.mp4
  3. Re-render do vídeo em ES  (--mix-lang es) -> output/<slug>_es.mp4
  4. Upload de cada vídeo para o YouTube com título/descrição/tags no idioma
  5. Envio de legendas .srt para o YouTube (captions.insert)

O vídeo PT original (output/<slug>.mp4) é mantido como está — NÃO é re-renderizado.

Uso:
  python scripts/publish_multilang.py                      # todos os projetos com MP4
  python scripts/publish_multilang.py --slug frida-luna-fazenda
  python scripts/publish_multilang.py --projects-dir D:/videomaker/projects
  python scripts/publish_multilang.py --dry-run            # só mostra o que faria
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_PROJECTS_DIR = HERE.parent / "projects"

BACKFILL = HERE / "backfill_languages.py"
PIPELINE = HERE / "pipeline.py"
UPLOAD = HERE / "youtube_upload.py"
CAPTIONS = HERE / "youtube_captions.py"

TRACK_FILE = HERE / ".publish_history.json"


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_json(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


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


def translate_title(title, target_lang, proj_dir, wait_s=60):
    """Traduz o título para outro idioma via Gemini Web (kind=text)."""
    if target_lang == "pt":
        return title
    # Tenta usar translate_script.py lógica simplificada: chamar gemini_fetch diretamente
    import tempfile
    prompt = (
        f"Traduza para o {target_lang} (tom infantil, natural). "
        f"Contexto: vídeo infantil sobre cachorros Frida e Luna. "
        f"Mantenha nomes próprios (Frida, Luna, Luninha, Fridoca) inalterados. "
        f"Responda APENAS com o título traduzido, sem aspas, sem explicações.\n\n"
        f"TÍTULO: {title}"
    )
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cmd = [
            sys.executable, str(HERE / "gemini_fetch.py"),
            "--kind", "text",
            "--prompt", prompt,
            "--name", "title_" + target_lang,
            "--out-dir", str(td),
            "--wait", str(wait_s),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  AVISO: falha ao traduzir título para {target_lang}, usando original.", flush=True)
            return title
        md_files = list(td.glob("*.md"))
        if not md_files:
            return title
        trad = md_files[0].read_text(encoding="utf-8").strip().strip('"').strip("'").strip()
        return trad if trad else title


def get_storyline(proj_dir, lang):
    """Extrai o enredo (seções de conteúdo) do script para a descrição."""
    script_path = proj_dir / "artifacts" / f"script_{lang}.json" if lang != "pt" else proj_dir / "artifacts" / "script.json"
    if not script_path.exists():
        return ""
    s = load_json(script_path)
    partes = [sec.get("text", "") for sec in s.get("sections", [])
              if sec.get("id") not in ("s_intro", "s0", "s_outro")]
    return " ".join(partes)[:500]


def build_description_i18n(title, storyline, lang):
    """Gera descrição no padrão do canal para um idioma específico."""
    from description_template import build_description as bd
    hook_index = {"pt": 0, "en": 1, "es": 2}.get(lang, 0)
    return bd(title, storyline, hook_index=hook_index, lang=lang)


def load_history():
    if TRACK_FILE.exists():
        try:
            return load_json(TRACK_FILE)
        except Exception:
            pass
    return {"done": []}


def save_history(hist):
    save_json(TRACK_FILE, hist)


def is_project_done(hist, proj_slug):
    return proj_slug in hist.get("done", [])


def mark_project_done(hist, proj_slug):
    hist.setdefault("done", [])
    if proj_slug not in hist["done"]:
        hist["done"].append(proj_slug)


def render_lang(proj_slug, lang, dry_run=False, projects_dir=DEFAULT_PROJECTS_DIR):
    """Re-renderiza o projeto para um idioma específico."""
    proj_dir = projects_dir / proj_slug
    output = proj_dir / "output"
    mp4_lang = output / f"{proj_slug}_{lang}.mp4"

    if dry_run:
        print(f"    [DRY-RUN] re-render {lang}: {mp4_lang.name}")
        return

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

    # O pipeline grava output/<slug>.mp4 com o áudio do idioma
    mp4_current = output / f"{proj_slug}.mp4"
    if mp4_current.exists() and not mp4_lang.exists():
        shutil.move(str(mp4_current), str(mp4_lang))
        print(f"    renomeado para {mp4_lang.name}", flush=True)


def upload_and_caption(proj_slug, lang, mp4_file, title, storyline, dry_run=False,
                       client_secret=None, token=None):
    """Faz upload do vídeo e envia legendas para o YouTube."""
    if not mp4_file.exists():
        print(f"    pulado (arquivo não existe): {mp4_file.name}", flush=True)
        return

    if dry_run:
        print(f"    [DRY-RUN] upload {lang}: {mp4_file.name}")
        return

    from description_template import build_description as bd
    lang_code = {"pt": "pt-BR", "en": "en-US", "es": "es-ES"}[lang]
    desc = build_description_i18n(title, storyline, lang)
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

    # Envia legendas SRT para o YouTube
    proj_dir = Path(mp4_file).parent.parent
    srt = proj_dir / "assets" / "subtitles" / lang / f"{proj_slug}.srt"
    if srt.exists():
        run([
            sys.executable, str(CAPTIONS),
            "--proj", str(proj_dir),
            "--lang", lang,
            "--srt", str(srt),
            "--client-secret", str(client_secret) if client_secret else str(HERE / "client_secret.json"),
            "--token", str(token) if token else str(HERE / "youtube_token.json"),
        ], f"legenda YouTube {lang} {proj_slug}")
    else:
        print(f"    AVISO: sem SRT para {lang}: {srt}", flush=True)


def publish_project(proj_slug, dry_run=False, projects_dir=DEFAULT_PROJECTS_DIR,
                    client_secret=None, token=None, hist=None):
    proj_dir = projects_dir / proj_slug
    if not proj_dir.exists():
        print(f"Projeto não encontrado: {proj_slug}", flush=True)
        return 1

    output = proj_dir / "output"
    mp4_pt = output / f"{proj_slug}.mp4"
    if not mp4_pt.exists():
        print(f"  pulado (sem MP4 final): {proj_slug}", flush=True)
        return 0

    # Já processado?
    if hist and is_project_done(hist, proj_slug):
        print(f"  pulado (já processado no histórico)", flush=True)
        return 0

    print(f"\n{'='*70}")
    print(f"PROJETO: {proj_slug}")
    print(f"{'='*70}", flush=True)

    title_pt = get_title_pt(proj_dir)

    mp4_en = output / f"{proj_slug}_en.mp4"
    mp4_es = output / f"{proj_slug}_es.mp4"

    # Se ja tem os 3 MP4s, considera concluído
    if mp4_pt.exists() and mp4_en.exists() and mp4_es.exists():
        print(f"  pulado (PT, EN e ES já existem)", flush=True)
        mark_project_done(hist, proj_slug)
        return 0

    # 1) Backfill de narração + legendas EN e ES
    print("  [1/4] Backfill de idiomas EN e ES...", flush=True)
    if not dry_run:
        run([
            sys.executable, str(BACKFILL),
            "--slug", proj_slug,
            "--languages", "en,es",
            "--workers", "4",
        ], f"backfill {proj_slug}", )

    # 2) Renomear PT para _pt.mp4 (apenas backup, NÃO re-renderiza)
    mp4_pt_backup = output / f"{proj_slug}_pt.mp4"
    if dry_run:
        print(f"    [DRY-RUN] renomear PT para {mp4_pt_backup.name}")
    else:
        if not mp4_pt_backup.exists():
            shutil.copy2(str(mp4_pt), str(mp4_pt_backup))
            print(f"    PT copiado para {mp4_pt_backup.name}", flush=True)

    # 3) Re-render em EN
    print("  [2/4] Re-render em inglês...", flush=True)
    render_lang(proj_slug, "en", dry_run, projects_dir)

    # 4) Re-render em ES
    print("  [3/4] Re-render em espanhol...", flush=True)
    render_lang(proj_slug, "es", dry_run, projects_dir)

    # 5) Traduzir títulos
    title_en = translate_title(title_pt, "en", proj_dir) if not dry_run else title_pt + " (EN)"
    title_es = translate_title(title_pt, "es", proj_dir) if not dry_run else title_pt + " (ES)"

    # 6) Upload de cada vídeo + legendas
    print("  [4/4] Upload para o YouTube...", flush=True)
    uploads = [
        ("pt", mp4_pt, title_pt),
        ("en", output / f"{proj_slug}_en.mp4", title_en),
        ("es", output / f"{proj_slug}_es.mp4", title_es),
    ]
    for lang, mp4_file, title in uploads:
        storyline = get_storyline(proj_dir, lang)
        upload_and_caption(proj_slug, lang, mp4_file, title, storyline, dry_run,
                           client_secret, token)

    mark_project_done(hist, proj_slug)
    save_history(hist)

    print(f"  concluído: {proj_slug}", flush=True)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default=None, help="projeto específico")
    ap.add_argument("--projects-dir", default=None, help="pasta de projetos (padrão: ./projects)")
    ap.add_argument("--dry-run", action="store_true", help="só mostra o que faria")
    ap.add_argument("--client-secret", default=None, help="caminho do client_secret.json")
    ap.add_argument("--token", default=None, help="caminho do youtube_token.json")
    args = ap.parse_args()

    projects_dir = Path(args.projects_dir) if args.projects_dir else DEFAULT_PROJECTS_DIR
    client_secret = Path(args.client_secret) if args.client_secret else None
    token = Path(args.token) if args.token else None

    hist = load_history()

    if args.slug:
        return publish_project(args.slug, args.dry_run, projects_dir, client_secret, token, hist)

    projetos = sorted([d for d in projects_dir.iterdir() if d.is_dir()])
    total = 0
    for proj in projetos:
        output = proj / "output"
        if output.exists() and list(output.glob("*.mp4")):
            total += 1

    print(f"Encontrados {total} projeto(s) com MP4 final em {projects_dir}.", flush=True)
    for proj in projetos:
        output = proj / "output"
        if output.exists() and list(output.glob("*.mp4")):
            publish_project(proj.name, args.dry_run, projects_dir, client_secret, token, hist)

    print(f"\n== Publicação multilíngue concluída.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
