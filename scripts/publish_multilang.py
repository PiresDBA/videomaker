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
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_PROJECTS_DIR = Path("E:/videomaker/projects")

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


def get_title_lang(proj_dir, lang):
    """Título no idioma, lido do roteiro traduzido (script_<lang>.json).

    Retorna None quando o roteiro traduzido não existe — o chamador deve
    abortar o upload em vez de publicar o título em português no canal
    estrangeiro.
    """
    if lang == "pt":
        return get_title_pt(proj_dir)
    p = proj_dir / "artifacts" / f"script_{lang}.json"
    if not p.exists():
        return None
    try:
        return (load_json(p).get("title") or "").strip() or None
    except Exception:
        return None


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
    """Extrai o enredo (seções de conteúdo) do script para a descrição.

    Retorna uma LISTA de strings (uma por seção de conteúdo), para que
    build_description/_fit_storyline itere sobre parágrafos e não caractere
    por caractere.
    """
    script_path = proj_dir / "artifacts" / f"script_{lang}.json" if lang != "pt" else proj_dir / "artifacts" / "script.json"
    if not script_path.exists():
        return []
    s = load_json(script_path)
    partes = []
    for sec in s.get("sections", []):
        if sec.get("id") in ("s_intro", "s0", "s_outro"):
            continue
        text = sec.get("text", "")
        # Remove quebras de linha e espaços extras (evita letras uma abaixo da outra)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            partes.append(text)
    return partes[:8]  # limita a 8 secoes para nao estourar o limite de 5000 chars


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
        "--projects-dir", str(projects_dir),
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


# Mapeamento de idioma -> arquivos de credenciais do YouTube
# Cada canal tem seu próprio client_secret e token OAuth2
LANG_CREDENTIALS = {
    "pt": {
        "client_secret": HERE / "client_secret_pt.json",
        "token": HERE / "youtube_token_pt.json",
    },
    "en": {
        "client_secret": HERE / "client_secret_en.json",
        "token": HERE / "youtube_token_en.json",
    },
    "es": {
        "client_secret": HERE / "client_secret_es.json",
        "token": HERE / "youtube_token_es.json",
    },
}


def get_credentials(lang, client_secret=None, token=None):
    """Retorna (client_secret, token) para o idioma, usando credenciais
    específicas do idioma quando existirem, senão cai de volta para as
    credenciais globais passadas por argumento."""
    creds = LANG_CREDENTIALS.get(lang, {})
    cs = creds.get("client_secret")
    tk = creds.get("token")
    if cs and cs.exists():
        client_secret = cs
    if tk and tk.exists():
        token = tk
    return client_secret, token


def upload_and_caption(proj_slug, lang, mp4_file, title, storyline, dry_run=False,
                       client_secret=None, token=None, proj_dir=None):
    """Faz upload do vídeo e envia legendas para o YouTube."""
    if not mp4_file.exists():
        print(f"    pulado (arquivo não existe): {mp4_file.name}", flush=True)
        return None

    if dry_run:
        print(f"    [DRY-RUN] upload {lang}: {mp4_file.name}")
        return None

    # Usa credenciais específicas do idioma quando disponíveis
    client_secret, token = get_credentials(lang, client_secret, token)

    from description_template import build_description as bd
    lang_code = {"pt": "pt-BR", "en": "en-US", "es": "es-ES"}[lang]
    desc = build_description_i18n(title, storyline, lang)
    tags = "cachorro,animacao,infantil,frida,luna,cachorrinho,desenhoanimado,videoengraçado,conteúdocriativo,petspride,familia,criancas"

    # Executa upload capturando stdout para extrair video_id
    cmd = [
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
    ]
    if client_secret:
        cmd += ["--client-secret", str(client_secret)]
    if token:
        cmd += ["--token", str(token)]

    print(f"    enviando {lang}...", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:] if len(r.stdout) > 2000 else r.stdout)
        print(r.stderr[-2000:] if len(r.stderr) > 2000 else r.stderr)
        raise RuntimeError(f"upload {lang} falhou com rc={r.returncode}")

    # Extrai video_id do stdout do youtube_upload.py
    video_id = None
    for line in r.stdout.splitlines():
        if "video_id" in line.lower() or ("youtu.be/" in line):
            import re
            m = re.search(r'([0-9A-Za-z_-]{11})', line)
            if m:
                video_id = m.group(1)
                break

    # Grava video_id no project-control.json
    if video_id and proj_dir:
        ctrl = proj_dir / "project-control.json"
        if ctrl.exists():
            try:
                c = load_json(ctrl)
                c.setdefault("publish", {})["video_id"] = video_id
                c["publish"]["done"] = True
                save_json(ctrl, c)
                print(f"    video_id gravado: {video_id}", flush=True)
            except Exception as e:
                print(f"    AVISO: não foi possível gravar video_id: {e}", flush=True)

    for line in r.stdout.splitlines():
        s = line.strip()
        if s.startswith(("UPLOAD", "VIDEO", "STATUS")):
            print(f"    {s}", flush=True)

    # Envia legendas SRT para o YouTube
    if proj_dir:
        srt = proj_dir / "assets" / "subtitles" / lang / f"{proj_slug}.srt"
        if srt.exists():
            cap_cmd = [
                sys.executable, str(CAPTIONS),
                "--proj", str(proj_dir),
                "--lang", lang,
                "--srt", str(srt),
            ]
            if client_secret:
                cap_cmd += ["--client-secret", str(client_secret)]
            if token:
                cap_cmd += ["--token", str(token)]
            cap_r = subprocess.run(cap_cmd, capture_output=True, text=True)
            if cap_r.returncode != 0:
                print(cap_r.stdout[-1000:] if len(cap_r.stdout) > 1000 else cap_r.stdout)
                print(cap_r.stderr[-1000:] if len(cap_r.stderr) > 1000 else cap_r.stderr)
                print(f"    AVISO: legenda {lang} falhou (vídeo foi uploadado)", flush=True)
            else:
                for line in cap_r.stdout.splitlines():
                    if line.strip():
                        print(f"    {line.strip()}", flush=True)
        else:
            print(f"    AVISO: sem SRT para {lang}: {srt}", flush=True)

    return video_id


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
            "--projects-dir", str(projects_dir),
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

    # 5) Títulos POR IDIOMA — vêm do roteiro já traduzido (script_<lang>.json).
    # NUNCA traduzir "on the fly": se a tradução falha, o título em português
    # ia para o canal em inglês/espanhol (bug real de produção).
    title_en = get_title_lang(proj_dir, "en")
    title_es = get_title_lang(proj_dir, "es")
    if not dry_run and (not title_en or not title_es):
        faltando = [l for l, t in (("en", title_en), ("es", title_es)) if not t]
        print(f"  ABORTADO: sem título localizado para {', '.join(faltando)} "
              f"(falta artifacts/script_<lang>.json neste projeto)", flush=True)
        return 1

    # 6) Upload de cada vídeo + legendas
    print("  [4/4] Upload para o YouTube...", flush=True)
    uploads = [
        ("pt", mp4_pt, title_pt),
        ("en", output / f"{proj_slug}_en.mp4", title_en or title_pt + " (EN)"),
        ("es", output / f"{proj_slug}_es.mp4", title_es or title_pt + " (ES)"),
    ]
    for lang, mp4_file, title in uploads:
        storyline = get_storyline(proj_dir, lang)
        upload_and_caption(proj_slug, lang, mp4_file, title, storyline, dry_run,
                           client_secret, token, proj_dir)

    mark_project_done(hist, proj_slug)
    save_history(hist)

    print(f"  concluído: {proj_slug}", flush=True)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default=None, help="projeto específico")
    ap.add_argument("--projects-dir", default=None, help="pasta de projetos (padrão: E:/videomaker/projects)")
    ap.add_argument("--dry-run", action="store_true", help="só mostra o que faria")
    ap.add_argument("--status", action="store_true", help="lista o status de cada projeto (processado ou pendente)")
    ap.add_argument("--client-secret", default=None, help="caminho do client_secret.json")
    ap.add_argument("--token", default=None, help="caminho do youtube_token.json")
    args = ap.parse_args()

    projects_dir = Path(args.projects_dir) if args.projects_dir else DEFAULT_PROJECTS_DIR
    client_secret = Path(args.client_secret) if args.client_secret else None
    token = Path(args.token) if args.token else None

    hist = load_history()

    if args.status:
        print(f"\nStatus de projetos em {projects_dir}:", flush=True)
        print(f"{'Projeto':<60} | {'MP4':<6} | {'PT':<4} | {'EN':<4} | {'ES':<4} | {'Historico':<10}", flush=True)
        print("-" * 100, flush=True)
        for proj in sorted([d for d in projects_dir.iterdir() if d.is_dir()]):
            output = proj / "output"
            mp4_pt = output / f"{proj.name}.mp4"
            mp4_en = output / f"{proj.name}_en.mp4"
            mp4_es = output / f"{proj.name}_es.mp4"
            has_mp4 = "SIM" if mp4_pt.exists() else "NAO"
            has_pt = "SIM" if mp4_pt.exists() else "NAO"
            has_en = "SIM" if mp4_en.exists() else "NAO"
            has_es = "SIM" if mp4_es.exists() else "NAO"
            done = "SIM" if is_project_done(hist, proj.name) else "NAO"
            print(f"{proj.name:<60} | {has_mp4:<6} | {has_pt:<4} | {has_en:<4} | {has_es:<4} | {done:<10}", flush=True)
        return 0

    if args.slug:
        return publish_project(args.slug, args.dry_run, projects_dir, client_secret, token, hist)

    projetos = sorted([d for d in projects_dir.iterdir() if d.is_dir()])
    total = 0
    pendentes = 0
    for proj in projetos:
        output = proj / "output"
        if output.exists() and list(output.glob("*.mp4")):
            total += 1
            if not is_project_done(hist, proj.name):
                pendentes += 1

    print(f"Encontrados {total} projeto(s) com MP4 final em {projects_dir}.", flush=True)
    print(f"Pendentes de processamento: {pendentes}", flush=True)
    for proj in projetos:
        output = proj / "output"
        if output.exists() and list(output.glob("*.mp4")):
            publish_project(proj.name, args.dry_run, projects_dir, client_secret, token, hist)

    print(f"\n== Publicação multilíngue concluída.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
