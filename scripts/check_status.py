#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mostra o status (titulo/descricao) de projetos recentes.

Uso:
  python scripts/check_status.py                    # todos os projetos
  python scripts/check_status.py <slug> [<slug>...] # so os indicados
"""

import json
import os
import sys

PROJECTS_DIR = r"C:\videomaker\projects"

# projetos usados por padrao (a lista mais recente pode ser atualizada aqui)
DEFAULT_PROJECTS = [
    "a-escola-dos-cachorros-o-primeiro-dia-de",
    "husky-siberiano-o-cachorro-que-conversa",
    "caes-de-resgate-como-eles-encontram-pess",
    "a-bulldogue-ingles-frida-decide-fazer-dieta-e-o-petisco-some-do-pote",
    "por-que-o-cachorro-lambe-o-seu-rosto",
]


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if args:
        projects = args
    elif os.path.isdir(PROJECTS_DIR):
        projects = sorted(
            name for name in os.listdir(PROJECTS_DIR)
            if os.path.isfile(os.path.join(PROJECTS_DIR, name, "project-control.json"))
        )
    else:
        projects = []

    print("=== RESUMO DE STATUS ATUAL (%d projetos) ===" % len(projects))
    print()

    problemas = 0
    for proj_name in projects:
        control_path = os.path.join(
            PROJECTS_DIR, proj_name, "project-control.json")

        if not os.path.exists(control_path):
            print("[PROBLEMA] %s: project-control.json NAO ENCONTRADO" % proj_name)
            print()
            problemas += 1
            continue

        try:
            with open(control_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            print("[PROBLEMA] %s: nao deu para ler (%s)" % (proj_name, exc))
            print()
            problemas += 1
            continue

        publish = data.get("publish") or {}
        desc = publish.get("description") or ""
        title = publish.get("title") or ""
        video_id = publish.get("video_id") or "-"

        status = "OK" if desc.strip() and title.strip() else "PROBLEMA"
        if status == "PROBLEMA":
            problemas += 1

        print("[%s] %s" % (status, proj_name))
        print("   Titulo (%d chars): %s" % (len(title), title))
        print("   Descricao (%d chars, %d palavras): %s%s"
              % (len(desc), len(desc.split()), desc[:100],
                 "..." if len(desc) > 100 else ""))
        print("   YouTube video_id: %s" % video_id)
        print()

    print("Projetos com problema: %d" % problemas)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
