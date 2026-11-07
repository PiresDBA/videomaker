# -*- coding: utf-8 -*-
"""Verifica que o pipeline gera a descricao no padrao do canal.

Simula o caminho do phase_youtube (sem fazer upload) e confere:
  - descricao com >= 100 palavras
  - contexto de IA, aviso de sem promocao, CTA e >= 8 hashtags
  - titulo e tags no padrao
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from description_template import (  # noqa: E402
    build_description, extract_storyline, read_script, validate, word_count,
)
from pipeline import YT_TAGS_PADRAO  # noqa: E402

falhas = []


def check(nome, cond, detalhe=""):
    print("[%s] %s%s" % ("OK" if cond else "FALHA", nome,
                          "" if cond else " -> %s" % detalhe))
    if not cond:
        falhas.append(nome)


proj = HERE.parent / "projects" / "a-escola-dos-cachorros-o-primeiro-dia-de"
script = read_script(proj)
title = script.get("title", "")

# mesmo caminho do phase_youtube
desc = build_description(title, extract_storyline(script))
tags = YT_TAGS_PADRAO

check("descricao gerada", bool(desc))
check("sem problemas no padrao", not validate(desc), str(validate(desc)))
check(">= 100 palavras", word_count(desc) >= 100, str(word_count(desc)))
check("<= 5000 chars", len(desc) <= 5000, str(len(desc)))
check("15 tags padrao", len([t for t in tags.split(",") if t.strip()]) == 15,
      tags)
check("tags sem duplicata",
      len({t.strip().lower() for t in tags.split(",")}) == 15, tags)

# a descricao NAO pode mais ser a antiga curta
check("nao e a descricao curta antiga",
      "Idioma da narração e das legendas" not in desc)
check("tem o titulo no inicio", desc.startswith(title), desc[:60])

print("")
if falhas:
    print("FALHAS: %s" % falhas)
    raise SystemExit(1)
print("Pipeline gera descricao no padrao do canal.")
