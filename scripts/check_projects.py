#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica a descricao de todos os projetos locais contra o padrao do canal.

Usa o modulo compartilhado scripts/description_template.py, entao o resultado
bate exatamente com o que o youtube_upload.py vai publicar.

Uso:
  python scripts/check_projects.py
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from description_template import validate, word_count  # noqa: E402

PROJECTS_DIR = r"C:\videomaker\projects"


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    if not os.path.isdir(PROJECTS_DIR):
        print("Diretorio de projetos nao encontrado: %s" % PROJECTS_DIR)
        return 1

    projects = sorted(
        name for name in os.listdir(PROJECTS_DIR)
        if os.path.isfile(os.path.join(PROJECTS_DIR, name, "project-control.json"))
    )

    print("Verificacao dos %d projetos" % len(projects))
    print("=" * 70)

    ok_count = 0
    for proj_name in projects:
        control_path = os.path.join(PROJECTS_DIR, proj_name, "project-control.json")
        with open(control_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        publish = data.get("publish") or {}
        desc = publish.get("description") or ""
        title = publish.get("title") or ""

        issues = validate(desc)
        status = "OK" if not issues else "PROBLEMA - " + "; ".join(issues)
        if not issues:
            ok_count += 1

        print("%s" % proj_name)
        print("  Titulo (%d chars): %s" % (len(title), title[:60]))
        print("  Descricao (%d chars, %d palavras): %s"
              % (len(desc), word_count(desc), desc[:80]))
        print("  Status: %s" % status)
        print()

    total = len(projects)
    pct = int(ok_count / total * 100) if total else 0
    print("=== Resumo ===")
    print("Projetos no padrao: %d/%d (%d%%)" % (ok_count, total, pct))
    return 0 if ok_count == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
