# -*- coding: utf-8 -*-
"""
Sobe TODOS os vídeos de UM idioma para o canal do YouTube daquele idioma.

Título e descrição vêm SEMPRE de artifacts/script_<lang>.json (roteiro já
traduzido). Se esse arquivo não existir, o upload é abortado (não sobe no
idioma errado).

Uso:
  python scripts/upload_por_idioma.py en          # sobe até 5 (cota diária)
  python scripts/upload_por_idioma.py en --all    # ignora o limite de 5
  python scripts/upload_por_idioma.py es --all
  python scripts/upload_por_idioma.py en --slug frida-e-luna-em-marte
  python scripts/upload_por_idioma.py en --dry-run

O progresso fica em scripts/.publish_history_idioma.json (feito + cota
estimada gasta hoje). Se bater a cota da API (quotaExceeded), o script pára
e você roda de novo amanhã.
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_PADRAO = Path(r"E:\videomaker\projects")

LANG_CREDS = {
    "en": {
        "client_secret": HERE / "client_secret_en.json",
        "token": HERE / "youtube_token_en.json",
        "code": "en-US",
    },
    "es": {
        "client_secret": HERE / "client_secret_es.json",
        "token": HERE / "youtube_token_es.json",
        "code": "es-ES",
    },
    "pt": {
        "client_secret": HERE / "client_secret_pt.json",
        "token": HERE / "youtube_token_pt.json",
        "code": "pt-BR",
    },
}

TAGS = {
    "pt": ["cachorro", "animacao", "infantil", "frida", "luna", "cachorrinho",
           "desenhoanimado", "videoengracado", "conteudocriativo", "pets",
           "familia", "criancas", "aprendizado", "diversao"],
    "en": ["dog", "animation", "kids", "frida", "luna", "puppy", "cartoon",
           "funnydog", "creativecontent", "pets", "family", "children",
           "learning", "fun"],
    "es": ["perro", "animacion", "infantil", "frida", "luna", "cachorro",
           "dibujosanimados", "videodivertido", "contenidocreativo", "mascotas",
           "familia", "ninos", "aprendizaje", "diversion"],
}

UPLOAD = HERE / "youtube_upload.py"
CAPTIONS = HERE / "youtube_captions.py"
HIST_FILE = HERE / ".publish_history_idioma.json"

CUSTO_UPLOAD = 1600   # unidades da cota YouTube Data API por vídeo
CUSTO_LEGENDA = 50    # por legenda
COTA_DIARIA = 10000   # unidades por projeto Google por dia


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_json(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def load_history():
    if HIST_FILE.exists():
        try:
            return load_json(HIST_FILE)
        except Exception:
            pass
    return {"done": [], "uso": {}}


def save_history(hist):
    save_json(HIST_FILE, hist)


def hoje():
    return time.strftime("%Y-%m-%d")


def uso_hoje(hist, lang):
    return int(hist.get("uso", {}).get(hoje(), {}).get(lang, 0))


def registrar_uso(hist, lang, unidades):
    dia = hist.setdefault("uso", {}).setdefault(hoje(), {})
    dia[lang] = int(dia.get(lang, 0)) + int(unidades)
    save_history(hist)


def is_done(hist, slug, lang):
    for e in hist.get("done", []):
        if e.get("slug") == slug and e.get("lang") == lang and e.get("video_id"):
            return True
    return False


def mark_done(hist, slug, lang, video_id, titulo):
    hist.setdefault("done", []).append({
        "slug": slug, "lang": lang, "video_id": video_id,
        "titulo": titulo,
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    save_history(hist)


def titulo_localizado(proj_dir, lang):
    """Título do roteiro no idioma. Aborta se não existir (não cai no PT)."""
    nome = "script.json" if lang == "pt" else f"script_{lang}.json"
    p = proj_dir / "artifacts" / nome
    if not p.is_file():
        return None
    try:
        t = (load_json(p).get("title") or "").strip()
    except Exception:
        return None
    return t or None


def enredo_localizado(proj_dir, lang):
    """Lista de parágrafos do enredo no idioma (sem s0/intro/outro)."""
    nome = "script.json" if lang == "pt" else f"script_{lang}.json"
    p = proj_dir / "artifacts" / nome
    if not p.is_file():
        return []
    try:
        script = load_json(p)
    except Exception:
        return []
    partes = []
    for sec in script.get("sections", []):
        if sec.get("id") in ("s_intro", "s0", "s_outro"):
            continue
        text = re.sub(r"\s+", " ", sec.get("text", "") or "").strip()
        if text:
            partes.append(text)
    return partes[:8]


def descricao_localizada(proj_dir, lang, titulo):
    from description_template import build_description
    hook_index = {"pt": 0, "en": 1, "es": 2}.get(lang, 0)
    return build_description(titulo, enredo_localizado(proj_dir, lang),
                             hook_index=hook_index, lang=lang)


def credenciais(lang):
    c = LANG_CREDS[lang]
    if lang == "pt" and not c["token"].is_file():
        # canal principal histórico
        if (HERE / "youtube_token.json").is_file() and (HERE / "client_secret.json").is_file():
            return HERE / "client_secret.json", HERE / "youtube_token.json"
    if not c["client_secret"].is_file():
        raise SystemExit(f"ERRO: {c['client_secret']} não existe.")
    if not c["token"].is_file():
        raise SystemExit(
            f"ERRO: {c['token']} não existe.\n"
            f"Autorize uma vez:\n"
            f"  python scripts/youtube_upload.py --client-secret {c['client_secret']} "
            f"--token {c['token']} --video <algum.mp4>"
        )
    return c["client_secret"], c["token"]


def upload(proj_slug, lang, mp4, titulo, desc, proj_dir, cs, tk, dry_run=False):
    cmd = [
        sys.executable, str(UPLOAD),
        "--video", str(mp4),
        "--title", titulo,
        "--description", desc,
        "--tags", ",".join(TAGS[lang]),
        "--category", "24",
        "--privacy", "public",
        "--made-for-kids",
        "--default-language", LANG_CREDS[lang]["code"],
        "--default-audio-language", LANG_CREDS[lang]["code"],
        "--client-secret", str(cs),
        "--token", str(tk),
    ]
    if dry_run:
        print(f"    [DRY-RUN] upload {lang}: {mp4.name}")
        print(f"    [DRY-RUN] título: {titulo}")
        return None

    print(f"    enviando {lang}: {mp4.name}", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = (r.stdout or "") + "\n" + (r.stderr or "")
    if r.returncode != 0:
        print(out[-3000:])
        return "ERRO_QUOTA" if "quotaExceeded" in out else None

    vid = None
    m = re.search(r"youtu\.be/([0-9A-Za-z_-]{11})", out)
    if m:
        vid = m.group(1)
    print(f"    vídeo no YouTube: https://youtu.be/{vid}", flush=True)
    return vid


def enviar_legendas(proj_slug, lang, proj_dir, vid, cs, tk):
    srt = proj_dir / "assets" / "subtitles" / lang / f"{proj_slug}.srt"
    if not srt.is_file():
        print(f"    AVISO: sem legenda {lang}: {srt.name}", flush=True)
        return
    cmd = [
        sys.executable, str(CAPTIONS),
        "--video-id", vid,
        "--lang", lang,
        "--srt", str(srt),
        "--client-secret", str(cs),
        "--token", str(tk),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        msg = ((r.stdout or "") + (r.stderr or ""))[-800:]
        print(f"    AVISO: legenda {lang} falhou: {msg}", flush=True)
    else:
        print(f"    legenda {lang}: OK", flush=True)


def gravar_no_projeto(proj_dir, lang, vid, titulo):
    ctrl = proj_dir / "project-control.json"
    if not ctrl.is_file():
        return
    try:
        c = load_json(ctrl)
    except Exception:
        return
    pub = c.setdefault("publish", {})
    pub.setdefault("videos", {})[lang] = {"video_id": vid, "titulo": titulo}
    pub["done"] = True
    save_json(ctrl, c)


def main():
    ap = argparse.ArgumentParser(description="Sobe todos os vídeos de um idioma para o canal daquele idioma")
    ap.add_argument("lang", choices=["pt", "en", "es"])
    ap.add_argument("--projects-dir", default=str(BASE_PADRAO))
    ap.add_argument("--slug", default=None)
    ap.add_argument("--limit", type=int, default=5,
                    help="máximo de uploads nesta execução (padrão 5; use --all para ignorar)")
    ap.add_argument("--all", action="store_true", help="ignora --limit (sobe tudo até a cota da API)")
    ap.add_argument("--force", action="store_true", help="reenvia mesmo se já publicado")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    lang = a.lang
    base = Path(a.projects_dir)
    cs, tk = credenciais(lang)

    limite = 9999 if a.all else a.limit
    hist = load_history()
    custo = uso_hoje(hist, lang)
    if custo:
        print(f"Cota já usada hoje neste canal (estimativa): {custo}/{COTA_DIARIA}")

    projetos = sorted([d for d in base.iterdir() if d.is_dir()])
    if a.slug:
        projetos = [p for p in projetos if p.name == a.slug]

    print(f"\n=== Canal {lang.upper()} | {len(projetos)} projeto(s) | limite {limite} upload(s) ===")
    print(f"Credenciais: {cs.name} + {tk.name}\n")

    enviados, pulados_sem_mp4, pulados_sem_script = [], [], []
    pulados_feitos, erros = [], []

    for proj in projetos:
        if len(enviados) >= limite:
            print(f"\nLimite de {limite} upload(s) nesta execução.")
            break
        slug = proj.name
        mp4 = proj / "output" / f"{slug}_{lang}.mp4"

        if not mp4.is_file():
            pulados_sem_mp4.append(slug)
            continue
        if not a.force and is_done(hist, slug, lang):
            pulados_feitos.append(slug)
            continue

        titulo = titulo_localizado(proj, lang)
        if not titulo:
            print(f"  !! {slug}: SEM artifacts/script_{lang}.json — abortado (não sobe no idioma errado)")
            pulados_sem_script.append(slug)
            continue

        print(f"\n{'='*68}")
        print(f"{slug} [{lang.upper()}]")
        print(f"  título: {titulo}")
        desc = descricao_localizada(proj, lang, titulo)
        print(f"  descrição: {len(desc)} chars | {len(desc.split())} palavras")

        vid = upload(slug, lang, mp4, titulo, desc, proj, cs, tk, a.dry_run)
        if vid == "ERRO_QUOTA":
            print("  COTA DA API ESGOTADA. Pare e continue amanhã.")
            erros.append((slug, "quota"))
            break
        if not vid:
            if a.dry_run:
                # dry-run: upload() sempre devolve None (nao envia de verdade).
                # Nao e falha - e so simulacao.
                enviados.append(slug)
                continue
            erros.append((slug, "falha no upload"))
            continue

        custo += CUSTO_UPLOAD
        if not a.dry_run:
            enviados.append(slug)
            mark_done(hist, slug, lang, vid, titulo)
            gravar_no_projeto(proj, lang, vid, titulo)
            enviar_legendas(slug, lang, proj, vid, cs, tk)
            custo += CUSTO_LEGENDA
            registrar_uso(hist, lang, CUSTO_UPLOAD + CUSTO_LEGENDA)

    print(f"\n{'='*68}")
    print(f"RELATÓRIO — {lang.upper()}")
    print(f"{'='*68}")
    print(f"enviados agora .......... {len(enviados)}")
    for s in enviados:
        print(f"   OK  {s}")
    print(f"já publicados antes ..... {len(pulados_feitos)}")
    print(f"sem MP4 _{lang} .......... {len(pulados_sem_mp4)}")
    print(f"sem script_{lang}.json ... {len(pulados_sem_script)}")
    for s in pulados_sem_script:
        print(f"   FALTA SCRIPT  {s}")
    print(f"erros ................... {len(erros)}")
    for s, e in erros:
        print(f"   ERRO  {s}: {e}")
    print(f"cota estimada usada ..... {custo}/{COTA_DIARIA} unidades")
    return 0


if __name__ == "__main__":
    sys.exit(main())
