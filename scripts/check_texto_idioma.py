"""Trava de idioma: nenhum texto em PT pode vazar para video EN/ES.

Bug real (2026-11-14): a traducao EN do Restaurante recebeu uma RECUSA do
Gemini ("Nao posso te ajudar... sou apenas um modelo de linguagem") e ela foi
narrada no video; e o s0 do video novo ficou com "O cao de ferias" no meio da
frase em ingles.

O que este check faz:
  * erro: recusa do Gemini ou titulo em PT dentro de script_en/script_es;
  * aviso: "Frida e Luna" (badge PT) em scenes/<lang>/s0.html antigo;
  * com --strict, o aviso de overlay tambem vira erro (use antes de publicar).

Uso:
  python scripts/check_texto_idioma.py            # todos os projetos
  python scripts/check_texto_idioma.py --slug X
  python scripts/check_texto_idioma.py --strict
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

REFUSAL = (
    "modelo de linguagem",
    "modelo de lenguaje",
    "language model",
    "não tenho essas informações",
    "nao tenho essas informacoes",
)

# Palavras que so existem em PT (evita falso positivo com ES/EN).
PT_MARKERS = (
    "não", "cão", "cães", "você", "hoje", "nossa", "obrigado",
    "obrigada", "férias", "coração", "amiguinhos", "também", "enquanto",
)


def norm(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto.lower()).strip()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def checar_script(proj: Path, lang: str):
    alvo = proj / "artifacts" / f"script_{lang}.json"
    base = proj / "artifacts" / "script.json"
    if not alvo.exists() or not base.exists():
        return [], []
    erros, avisos = [], []
    original = load(base)
    traduzido = load(alvo)
    titulo_pt = norm(original.get("title", ""))
    titulo_trad = traduzido.get("title", "") or ""
    achados_titulo = [m for m in PT_MARKERS
                      if re.search(rf"\b{re.escape(norm(m))}\b", norm(titulo_trad))]
    if achados_titulo:
        erros.append(f"title: possivel PT {achados_titulo[:4]}")
    if titulo_pt:
        for sec in traduzido.get("sections", []):
            if titulo_pt and titulo_pt in norm(sec.get("text", "")):
                erros.append(f"{sec.get('id')}: titulo PT '{original.get('title')}' "
                             "dentro da narracao")
    for sec in traduzido.get("sections", []):
        low = norm(sec.get("text", ""))
        if any(norm(m) in low for m in REFUSAL):
            erros.append(f"{sec.get('id')}: recusa do Gemini no texto")
        achados = [m for m in PT_MARKERS
                   if re.search(rf"\b{re.escape(norm(m))}\b", low)]
        if achados:
            avisos.append(f"{sec.get('id')}: possivel PT {achados[:4]}")
    return erros, avisos


def checar_overlay(proj: Path, lang: str):
    p = proj / "scenes" / lang / "s0.html"
    if not p.exists():
        return []
    texto = p.read_text(encoding="utf-8")
    if "Frida e Luna" in texto:
        return ["scenes/%s/s0.html: badge 'Frida e Luna' (PT) no overlay" % lang]
    return []


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Texto PT/recusa em video EN/ES")
    ap.add_argument("--slug", default="", help="so este projeto")
    ap.add_argument("--strict", action="store_true",
                    help="overlay com badge PT tambem bloqueia")
    args = ap.parse_args(argv)

    projetos = sorted(d for d in (ROOT / "projects").iterdir() if d.is_dir())
    if args.slug:
        projetos = [p for p in projetos if p.name == args.slug]

    erros, avisos = [], []
    for proj in projetos:
        for lang in ("en", "es"):
            e, a = checar_script(proj, lang)
            erros += [f"[{proj.name}/{lang}] {x}" for x in e]
            avisos += [f"[{proj.name}/{lang}] {x}" for x in a]
            o = checar_overlay(proj, lang)
            (erros if args.strict else avisos).extend(
                f"[{proj.name}/{lang}] {x}" for x in o)

    for a in avisos:
        print(f"  ~ {a}")
    for e in erros:
        print(f"  ! {e}", file=sys.stderr)

    if erros:
        print(f"\n[BLOQUEADO] {len(erros)} problema(s) de idioma. "
              "Corrija o script/overlay antes de renderizar ou publicar.")
        return 1
    print(f"[OK] nenhum texto PT/recusa em EN/ES "
          f"({len(projetos)} projeto(s) conferido(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
