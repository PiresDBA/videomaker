# -*- coding: utf-8 -*-
"""Smoke test do padrao de descricao (2026-11-06)."""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from description_template import (  # noqa: E402
    MAX_CHARS, build_description, description_for_project, extract_storyline,
    find_project_for_title, read_script, validate, word_count,
)

falhas = []


def check(nome, cond, detalhe=""):
    if cond:
        print("[OK] %s" % nome)
    else:
        print("[FALHA] %s %s" % (nome, detalhe))
        falhas.append(nome)


# 1. descricao de um projeto real
proj = HERE.parent / "projects" / "a-escola-dos-cachorros-o-primeiro-dia-de"
desc = description_for_project(proj)
check("descricao gerada", desc is not None)
check("sem problemas", not validate(desc), str(validate(desc or "")))
check(">= 100 palavras", word_count(desc) >= 100, str(word_count(desc or "")))
check("<= 5000 chars", len(desc or "") <= MAX_CHARS, str(len(desc or "")))
check("tem CTA", "Siga-nos" in (desc or ""))
check("tem 11 hashtags", (desc or "").count("#") >= 11, str((desc or "").count("#")))

# 2. enredo exclui s0 / s_intro / s_outro
script = read_script(proj)
ids = [s.get("id") for s in script.get("sections", [])]
story = " ".join(extract_storyline(script))
check("enredo sem s0", "Ola, familia" not in story[:200])
check("enredo tem s1+", "s1" in ids)

# 3. limite de 5000 chars com enredo gigante
enorme = ["Palavra " * 500 for _ in range(20)]
d2 = build_description("Teste de limite", enorme)
check("descricao longa <= 5000", len(d2) <= MAX_CHARS, str(len(d2)))
check("descricao longa sem problemas", not validate(d2), str(validate(d2)))
check("descricao longa mantem hashtags", d2.rstrip().endswith("#diversão"))
check("descricao longa mantem CTA", "Não contém promoção paga" in d2)

# 4. validate pega descricao vazia / curta
check("detecta vazia", bool(validate("")))
check("detecta curta", bool(validate("texto curto")))

# 5. casamento de projeto por titulo
p1 = find_project_for_title("Husky siberiano: o cachorro que conversa e faz drama")
check("casa husky", p1 is not None and "husky" in p1.name, str(p1))
p2 = find_project_for_title("Por que o cachorro lambe o seu rosto?")
check("casa lambe", p2 is not None and "lambe" in p2.name, str(p2))
p3 = find_project_for_title("video totalmente aleatorio que nao existe em lugar nenhum")
check("nao casa falso positivo", p3 is None, str(p3))

# 6. youtube_upload usa o template
src = (HERE / "youtube_upload.py").read_text(encoding="utf-8")
check("upload importa description_template", "description_template" in src)
check("upload usa build_description", "build_description" in src)

print("")
if falhas:
    print("FALHAS: %d -> %s" % (len(falhas), falhas))
    raise SystemExit(1)
print("Todos os testes passaram.")
