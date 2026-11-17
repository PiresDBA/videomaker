# -*- coding: utf-8 -*-
"""
TRAVA DE IDIOMA DO VIDEO (bug 2026-11-16).

O que aconteceu: os 3 videos (PT/EN/ES) do "Campeonato de caes mais maluco"
sairam IDENTICOS - o PT foi renderizado com o MIX em espanhol e o EN/ES com a
composicao em portugues. Causa: o render foi disparado na mao, reaproveitando
composicao/mix ja prontos de outro idioma.

Esta trava confere, por idioma:
  1. output/<slug>_<lang>.mp4 tem ficha (.meta.json) com o idioma certo;
  2. os videos dos 3 idiomas nao sao byte-a-byte iguais (iguais = idioma errado);
  3. a composicao e o mix do projeto sao do MESMO idioma.

Uso:
  python scripts/check_video_idioma.py --slug o-campeonato-de-caes-mais-maluco-do-mundo
  python scripts/check_video_idioma.py --slug <slug> --lang es --strict
  python scripts/check_video_idioma.py --all
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
IDIOMAS = ["pt", "en", "es"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sidecar_lang(path):
    """Idioma declarado no carimbo .lang (ou em data-lang do HTML)."""
    if not path:
        return None
    path = Path(path)
    sc = Path(str(path) + ".lang")
    if sc.exists():
        try:
            return sc.read_text(encoding="utf-8").strip().lower()
        except Exception:
            return None
    if path.suffix.lower() in (".html", ".htm"):
        try:
            html = path.read_text(encoding="utf-8")
        except Exception:
            return None
        if 'data-lang="' in html:
            return html.split('data-lang="', 1)[1].split('"', 1)[0].strip().lower()
    return None


def check_project(p_dir: Path, args) -> int:
    slug = p_dir.name
    out_dir = p_dir / "output"
    idiomas = [args.lang.strip().lower()] if args.lang else IDIOMAS
    erros = []
    avisos = []
    hashes = {}

    print("== TRAVA: idioma do video (%s)" % slug)

    for lang in idiomas:
        video = out_dir / ("%s_%s.mp4" % (slug, lang))
        meta_path = Path(str(video) + ".meta.json")
        if not video.exists():
            msg = "[%s] VIDEO AUSENTE: %s" % (lang, video.name)
            (erros if args.strict else avisos).append(msg)
            print("  .. " + msg)
            continue
        if not meta_path.exists():
            # Videos antigos (antes da ficha) nao bloqueiam - so avisam.
            msg = ("[%s] FICHA AUSENTE: %s (render antigo, sem carimbo de idioma)"
                   % (lang, meta_path.name))
            avisos.append(msg)
            print("  .. " + msg)
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception as e:
            erros.append("[%s] ficha ilegivel: %s" % (lang, e))
            print("  !! ficha ilegivel: %s" % e)
            continue
        got = str(meta.get("lang", "")).strip().lower()
        if got != lang:
            msg = ("[%s] IDIOMA ERRADO no video: a ficha diz '%s'. "
                   "O arquivo %s foi renderizado com o conteudo de outro idioma."
                   % (lang, got or "?", video.name))
            erros.append(msg)
            print("  !! " + msg)
            continue
        hashes[lang] = sha256(video)
        print("  ok [%s] %s (idioma=%s, %d MB)"
              % (lang, video.name, got, video.stat().st_size // (1024 * 1024)))

    # videos com o mesmo sha256 = copias do mesmo idioma (bug 2026-11-16)
    if len(hashes) > 1:
        itens = sorted(hashes.items())
        for i in range(len(itens)):
            for j in range(i + 1, len(itens)):
                if itens[i][1] == itens[j][1]:
                    msg = ("VIDEO DUPLICADO: %s e %s sao byte-a-byte iguais "
                           "(sha256 %s) - os dois tem o mesmo idioma."
                           % (itens[i][0], itens[j][0], itens[i][1][:16]))
                    erros.append(msg)
                    print("  !! " + msg)

    # composicao e mix do projeto tem que ser do mesmo idioma
    comp = p_dir / "composition.html"
    mix = p_dir / "assets" / "audio" / "final_mix.m4a"
    c_lang = sidecar_lang(comp)
    m_lang = sidecar_lang(mix)
    if c_lang and m_lang and c_lang != m_lang:
        msg = ("COMPOSICAO (%s) e MIX (%s) de idiomas diferentes - "
               "refaca compose+mix do mesmo idioma." % (c_lang, m_lang))
        erros.append(msg)
        print("  !! " + msg)
    elif c_lang:
        print("  ok composicao=%s mix=%s" % (c_lang, m_lang or "sem carimbo"))

    if erros:
        print("\n" + "!" * 70)
        print("ABORTADO pela trava de idioma do video (%s):" % slug)
        for e in erros:
            print(" - " + e)
        print("Nao publique video com idioma trocado.")
        print("!" * 70)
        return 1
    for a in avisos:
        print(" - aviso: " + a)
    print("OK: idioma dos videos de %s confere." % slug)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default="", help="slug do projeto (vazio = todos)")
    ap.add_argument("--all", action="store_true", help="checar todos os projetos")
    ap.add_argument("--lang", default="", help="checar so este idioma")
    ap.add_argument("--projects-dir", default=str(ROOT / "projects"))
    ap.add_argument("--strict", action="store_true",
                    help="falha se algum idioma estiver faltando")
    args = ap.parse_args()

    projects_dir = Path(args.projects_dir)
    if args.all or not args.slug:
        slugs = sorted(p.name for p in projects_dir.iterdir()
                       if p.is_dir() and (p / "output").is_dir()
                       and any((p / "output").glob("*.mp4")))
    else:
        slugs = [args.slug]

    rc = 0
    for slug in slugs:
        rc |= check_project(projects_dir / slug, args)
    return rc


if __name__ == "__main__":
    sys.exit(main())
