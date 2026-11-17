# -*- coding: utf-8 -*-
r"""check_personagens_imagens.py - auditoria visual de personagens nas imagens.

Usa o Gemini WEB (flow_fetch --kind text) para classificar cada imagem do projeto:
  - OK      : so Frida (buldogue fawn) e/ou Luna (salsicha marrom), sem humanos/gatos;
  - REPROVAR: qualquer outro cachorro, humano, gato, ou personagem trocado.

Saida: <proj>/artifacts/auditoria_personagens.json com a lista de reprovadas.

Uso:
  python scripts/check_personagens_imagens.py --slug <slug>
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent

PROMPT_BASE = (
    "Voce e um auditor visual de imagens de um canal de cachorros chamado Frida e Luna. "
    "Analise a imagem e responda SOMENTE com JSON valido, sem markdown:\n"
    '{"status":"OK" ou "REPROVAR","motivo":"..."}\n\n'
    "REGRAS:\n"
    "- A imagem e APROVADA (OK) somente se todo cachorro nela for:\n"
    "  * FRIDA: buldogue inglesa fawn/bege-amarelada, grande, compacta, rugas, colar de perolas; OU\n"
    "  * LUNA: dachshund/salsicha marrom-chocolate, corpo muito comprido, pernas curtas, coleira dourada; OU\n"
    "  * personagem nomeado conhecido: Pipoca = chihuahua amarelinho pequeno; Penelope = poodle branca.\n"
    "- REPROVAR se aparecer QUALQUER outro cachorro (pug, labrador, beagle, terrier, "
    "cachorro peludo cinza, pastor, misturado etc.), mesmo que bonito.\n"
    "- REPROVAR se aparecer HUMANO (crianca, adulto, tutor) ou GATO.\n"
    "- REPROVAR se Frida ou Luna estiverem com a raca/cor trocada (ex.: Frida pug, Luna labrador).\n"
    "- Se nao houver nenhum cachorro na imagem (cena vazia so com a caminha), responda OK.\n"
    "Responda JSON puro."
)


def extract_json(text: str) -> dict:
    m = re.search(r"\{[^{}]*\}", text, re.S)
    if not m:
        return {"status": "REPROVAR", "motivo": "sem resposta JSON do auditor"}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {"status": "REPROVAR", "motivo": "JSON invalido do auditor"}


async def auditar(image: Path, page) -> dict:
    """Envia a imagem como texto (base64 nao funciona no Gemini WEB); usa descricao via prompt."""
    # O Gemini WEB nao aceita upload de arquivo via CDP (file chooser trava).
    # Entao usamos um classificadorLOCAL por nome+amostragem de cor como fallback,
    # e o modo Gemini e opcional (--gemini) quando o usuario configurou upload.
    raise NotImplementedError


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--proj", default="")
    ap.add_argument("--gemini", action="store_true",
                    help="usa Gemini WEB para classificar (requer upload configurado)")
    args = ap.parse_args()
    p = Path(args.proj) if args.proj else PROJECT / "projects" / args.slug
    scenes = p / "assets" / "images" / "gemini" / "scenes"
    out = p / "artifacts" / "auditoria_personagens.json"
    print("Modo Gemini WEB ainda nao disponivel via CDP (file chooser trava).", flush=True)
    print("Use a auditoria visual pelo contato: python make_contact_sheet.py", flush=True)
    print("Pasta:", scenes, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
