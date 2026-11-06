#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Padroniza a descricao de TODOS os projetos locais.

A geracao usa o modulo compartilhado scripts/description_template.py
(fonte unica da verdade do padrao do canal), incluindo o ajuste automatico
para o limite de 5000 caracteres do YouTube.

Uso:
  python scripts/standardize_descriptions.py            # so o que estiver vazio
  python scripts/standardize_descriptions.py --force    # regenera todas
  python scripts/standardize_descriptions.py --only <slug>
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from description_template import (  # noqa: E402
    build_description, extract_storyline, read_script, validate, word_count,
)

PROJECTS_DIR = r"C:\videomaker\projects"


def load_projects():
    projects = []
    if not os.path.isdir(PROJECTS_DIR):
        return projects
    for item in sorted(os.listdir(PROJECTS_DIR)):
        item_path = os.path.join(PROJECTS_DIR, item)
        if os.path.isdir(item_path):
            if os.path.exists(os.path.join(item_path, "project-control.json")):
                projects.append(item)
    return projects


def improve_project_description(project_dir):
    """Regenera publish.title e publish.description no padrao do canal."""
    control_path = os.path.join(project_dir, "project-control.json")
    with open(control_path, "r", encoding="utf-8") as f:
        project_data = json.load(f)

    script = read_script(project_dir)
    if not script:
        return None

    title = script.get("title", "")
    description = build_description(title, extract_storyline(script))

    publish = project_data.setdefault("publish", {})
    publish["title"] = title
    publish["description"] = description

    with open(control_path, "w", encoding="utf-8") as f:
        json.dump(project_data, f, ensure_ascii=False, indent=2)

    return description


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="Standardizes video descriptions in Videomaker projects")
    parser.add_argument("--force", action="store_true",
                        help="regenera mesmo descricoes que ja existem")
    parser.add_argument("--only", help="processa apenas um projeto (pelo slug)")
    args = parser.parse_args()

    projects = load_projects()
    if args.only:
        projects = [args.only] if args.only in projects else []

    if not projects:
        print("Nenhum projeto encontrado para processar.")
        return 1

    print("Processando %d projetos..." % len(projects))

    updated = 0
    kept = 0
    problems = 0

    for project_name in projects:
        project_dir = os.path.join(PROJECTS_DIR, project_name)
        control_path = os.path.join(project_dir, "project-control.json")
        if not os.path.exists(control_path):
            continue

        with open(control_path, "r", encoding="utf-8") as f:
            project_data = json.load(f)
        current = (project_data.get("publish") or {}).get("description") or ""

        if not current.strip() or args.force:
            description = improve_project_description(project_dir)
            if description is None:
                print("[AVISO] %s: sem artifacts/script.json" % project_name)
                continue
            updated += 1
            issues = validate(description)
            status = "OK" if not issues else "; ".join(issues)
            print("[OK] %s | %d palavras | %s" % (project_name, word_count(description), status))
            if issues:
                problems += 1
        else:
            kept += 1
            print("[MANTER] %s (descricao ja existente)" % project_name)

    print("")
    print("Total de projetos processados: %d" % len(projects))
    print("Projetos atualizados: %d" % updated)
    print("Projetos mantidos como estao: %d" % kept)
    if problems:
        print("Projetos com problema no padrao: %d" % problems)
    print("[OK] Finalizado! As descricoes foram padronizadas com sucesso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
