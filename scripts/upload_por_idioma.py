# -*- coding: utf-8 -*-
"""Upload de UM idioma para o canal do YouTube daquele idioma.

FONTE DA VERDADE DO TITULO E DA DESCRICAO
-----------------------------------------
Titulo e enredo vem SEMPRE de artifacts/script_<lang>.json (o roteiro ja
traduzido do projeto). Nunca de traducao "on the fly" (Gemini Web), que
falhava e caia no titulo em portugues — era esse o bug dos videos em
ingles/espanhol subirem com titulo e gancho em portugues.

Se o projeto nao tiver script_<lang>.json, o upload e ABORTADO com erro
claro: melhor nao publicar do que publicar no idioma errado.

Uso:
  python scripts/upload_por_idioma.py en              # sobe ate 5 (cota)
  python scripts/upload_por_idioma.py es --limit 3
  python scripts/upload_por_idioma.py en --all        # ignora o limite
  python scripts/upload_por_idioma.py en --slug frida-e-luna-em-marte
  python scripts/upload_por_idioma.py en --dry-run
  python scripts/upload_por_idioma.py en --force      # reenvia ja publicados

Cota da API: cada upload custa ~1600 unidades de 10.000/dia por projeto
Google. Ou seja, ~6 uploads por canal por dia. Legendas custam ~50.
O script para sozinho quando a cota estoura e grava o progresso.
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

# Custo aproximado de videos.insert na cota diaria (unidades)
CUSTO_UPLOAD = 1600
CUSTO_LEGENDA = 50
COTA_DIARIA = 10000


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
    return {"done": []}


def save_history(hist):
    save_json(HIST_FILE, hist)


def is_done(hist, slug, lang):
    for e in hist.get("done", []):
        if e.get("slug") == slug and e.get("lang") == lang and e.get("video_id"):
            return True
    return False


def hoje():
    return time.strftime("%Y-%m-%d")


def uso_hoje(hist, lang):
    """Unidades de cota ja gastas hoje neste canal (estimativa)."""
    return int(hist.get("uso", {}).get(hoje(), {}).get(lang, 0))


def registrar_uso(hist, lang, unidades):
    dia = hist.setdefault("uso", {}).setdefault(hoje(), {})
    dia[lang] = int(dia.get(lang, 0)) + int(unidades)
    save_history(hist)


def mark_done(hist, slug, lang, video_id, title):
    hist.setdefault("done", []).append({
        "slug": slug,
        "lang": lang,
        "video_id": video_id,
        "title": title,
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    save_history(hist)


def script_path(proj_dir, lang):
    nome = "script.json" if lang == "pt" else f"script_{lang}.json"
    return proj_dir / "artifacts" / nome


def titulo_localizado(proj_dir, lang):
    """Titulo do roteiro no idioma. None se nao existir (NUNCA cai no PT)."""
    p = script_path(proj_dir, lang)
    if not p.is_file():
        return None
    try:
        t = (load_json(p).get("title") or "").strip()
    except Exception:
        return None
    return t or None


def enredo_localizado(proj_dir, lang):
    """Lista de paragrafos do enredo no idioma (sem s0/intro/outro)."""
    p = script_path(proj_dir, lang)
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
    cs, tk = c["client_secret"], c["token"]
    # Canal PT: o token historico (youtube_token.json) ja e o canal principal.
    # Usa ele quando o token _pt ainda nao foi criado, para nao exigir nova
    # autorizacao do canal que ja funciona.
    if lang == "pt" and not tk.is_file():
        tk_hist = HERE / "youtube_token.json"
        cs_hist = HERE / "client_secret.json"
        if tk_hist.is_file() and cs_hist.is_file():
            return cs_hist, tk_hist
    if not cs.is_file():
        raise SystemExit(f"ERRO: {cs} nao existe (client_secret do canal {lang.upper()}).")
    if not tk.is_file():
        raise SystemExit(
            f"ERRO: {tk} nao existe.\n"
            f"Rode uma vez para autorizar o canal {lang.upper()}:\n"
            f"  python scripts/youtube_upload.py --client-secret {cs} "
            f"--token {tk} --video <algum.mp4>"
        )
    return cs, tk


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
        print(f"    [DRY-RUN] titulo: {titulo}")
        print(f"    [DRY-RUN] descricao ({len(desc)} chars): {desc[:160]}...")
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
    print(f"    video_id: {vid}", flush=True)
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
    pub.setdefault("videos", {})[lang] = {"video_id": vid, "title": titulo}
    pub["done"] = True
    save_json(ctrl, c)


def main():
    ap = argparse.ArgumentParser(description="Sobe os videos de um idioma para o canal daquele idioma")
    ap.add_argument("lang", choices=["pt", "en", "es"])
    ap.add_argument("--projects-dir", default=str(BASE_PADRAO))
    ap.add_argument("--slug", default=None)
    ap.add_argument("--limit", type=int, default=5,
                    help="maximo de uploads nesta execucao (padrao 5, por causa da cota)")
    ap.add_argument("--all", action="store_true", help="ignora --limit")
    ap.add_argument("--force", action="store_true", help="reenvia mesmo se ja publicado")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    lang = a.lang
    base = Path(a.projects_dir)
    cs, tk = credenciais(lang)

    limite = 999 if a.all else a.limit
    hist = load_history()

    projetos = sorted([d for d in base.iterdir() if d.is_dir()])
    if a.slug:
        projetos = [p for p in projetos if p.name == a.slug]

    print(f"=== Canal {lang.upper()} | {len(projetos)} projeto(s) | limite {limite} upload(s) ===")
    print(f"Credenciais: {cs.name} + {tk.name}\n")

    enviados, pulados_sem_mp4, pulados_sem_script = [], [], []
    pulados_feitos, erros = [], []
    custo = uso_hoje(hist, lang)
    if custo:
        print(f"Cota ja usada hoje neste canal (estimativa): {custo}/{COTA_DIARIA}\n")

    for proj in projetos:
        if len(enviados) >= limite:
            print(f"\nLimite de {limite} upload(s) atingido nesta execucao.")
            break
        slug = proj.name
        mp4 = proj / "output" / f"{slug}_{lang}.mp4"
        if not mp4.is_file() and lang == "pt":
            # publish_multilang renomeia o PT original para <slug>_pt.mp4
            alt = proj / "output" / f"{slug}_pt.mp4"
            if alt.is_file():
                mp4 = alt

        if not mp4.is_file():
            pulados_sem_mp4.append(slug)
            continue
        if is_done(hist, slug, lang) and not a.force:
            pulados_feitos.append(slug)
            continue

        titulo = titulo_localizado(proj, lang)
        if not titulo:
            print(f"  !! {slug}: SEM artifacts/script_{lang}.json — abortado (nao subir no idioma errado)")
            pulados_sem_script.append(slug)
            continue

        # Cota: para antes de estourar
        if custo + CUSTO_UPLOAD + CUSTO_LEGENDA > COTA_DIARIA:
            print(f"\nCota diaria estimada atingida ({custo}/{COTA_DIARIA}) — pare e continue amanha.")
            break

        print(f"\n{'='*68}")
        print(f"{slug} [{lang.upper()}]")
        print(f"  titulo: {titulo}")
        desc = descricao_localizada(proj, lang, titulo)
        print(f"  descricao: {len(desc)} chars | {len(desc.split())} palavras")

        vid = upload(slug, lang, mp4, titulo, desc, proj, cs, tk, a.dry_run)
        if vid == "ERRO_QUOTA":
            print("  COTA DA API ESGOTADA neste projeto Google. Rode de novo amanha.")
            erros.append((slug, "quota"))
            break
        if not vid:
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
    print(f"RELATORIO — {lang.upper()}")
    print(f"{'='*68}")
    print(f"enviados agora .......... {len(enviados)}")
    for s in enviados:
        print(f"   OK  {s}")
    print(f"ja publicados antes ..... {len(pulados_feitos)}")
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
