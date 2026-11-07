# -*- coding: utf-8 -*-
"""
check_manual.py - confere se o MANUAL_GRAFOS.md esta em dia com o codigo.

Este script existe para transformar a regra do CONTRATO.md em algo verificavel:
antes de dar push, rode

    python scripts/check_manual.py

Ele checa:
  1. os arquivos do contrato existem (CONTRATO.md, AGENTS.md, MANUAL_GRAFOS.md);
  2. as secoes obrigatorias do manual existem (grafo, dependencias, CLI, etc.);
  3. todas as fases do pipeline.py aparecem no grafo do manual;
  4. todas as dependencias do pipeline.py aparecem no grafo de dependencias;
  5. as referencias "arquivo.py:linha" do manual apontam para linhas validas;
  6. as secoes do manual estao em ordem crescente.

Saida: 0 = tudo em dia. 1 = desync (o manual precisa ser atualizado).
"""

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANUAL = ROOT / "MANUAL_GRAFOS.md"
CONTRATO = ROOT / "CONTRATO.md"
AGENTS = ROOT / "AGENTS.md"
PIPELINE = ROOT / "scripts" / "pipeline.py"

# Secoes que o CONTRATO.md exige que existam no manual.
SECOES_OBRIGATORIAS = [
    "0. CONTRATO",
    "3. Grafo do pipeline",
    "4. Grafo de depend",
    "30.7",
    "36.",
    "37.",
    "38.",
    "39.",
]


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    problemas = []
    avisos = []

    # ---- 1. arquivos do contrato ----------------------------------------
    for arquivo, obrigatorio in ((MANUAL, True), (CONTRATO, True), (AGENTS, True)):
        if not arquivo.is_file():
            msg = "%s ausente" % arquivo.name
            (problemas if obrigatorio else avisos).append(msg)

    if not MANUAL.is_file():
        print("ERRO: %s nao encontrado." % MANUAL)
        return 1

    texto = MANUAL.read_text(encoding="utf-8")

    # ---- 2. secoes obrigatorias -----------------------------------------
    for secao in SECOES_OBRIGATORIAS:
        if secao not in texto:
            problemas.append("manual sem a secao '%s'" % secao)

    # ---- 3. e 4. fases e dependencias do codigo no manual ----------------
    fases, deps = [], {}
    if PIPELINE.is_file():
        arvore = ast.parse(PIPELINE.read_text(encoding="utf-8"))
        fases, deps = [], {}
        for node in ast.walk(arvore):
            if not isinstance(node, ast.Assign):
                continue
            for alvo in node.targets:
                if not isinstance(alvo, ast.Name):
                    continue
                if alvo.id == "PHASES" and isinstance(node.value, (ast.List, ast.Tuple)):
                    fases = [e.value for e in node.value.elts
                             if isinstance(e, ast.Constant)]
                elif alvo.id == "DEPS" and isinstance(node.value, ast.Dict):
                    for k, v in zip(node.value.keys, node.value.values):
                        if isinstance(k, ast.Constant) and isinstance(v, ast.List):
                            deps[k.value] = [e.value for e in v.elts
                                             if isinstance(e, ast.Constant)]

        # o grafo do manual (secao 3) precisa citar cada fase
        for fase in fases:
            if fase not in texto:
                problemas.append("fase '%s' do codigo nao aparece no manual" % fase)

        # o grafo de dependencias (secao 4) precisa ter as mesmas arestas
        for pai, filhos in deps.items():
            for filho in filhos:
                if not re.search(r"%s\s*-->\s*%s" % (pai, filho), texto):
                    problemas.append(
                        "dependencia %s -> %s ausente no grafo do manual" % (pai, filho))

        # a fase youtube (extra) precisa estar documentada
        if "youtube" in texto and "--publish" not in texto:
            avisos.append("fase youtube citada, mas '--publish' nao é explicado")
    else:
        avisos.append("scripts/pipeline.py ausente: pulou a checagem de fases")
    # ---- 5. referencias arquivo.py:linha --------------------------------
    for arquivo_ref, linha in re.findall(
            r"`([A-Za-z0-9_/\\.\-]+\.py):(\d+)`", texto):
        caminho = ROOT / arquivo_ref.replace("\\", "/")
        if not caminho.is_file():
            continue
        total = len(caminho.read_text(encoding="utf-8",
                                      errors="replace").splitlines())
        if int(linha) > total:
            problemas.append(
                "manual referencia %s:%s, mas o arquivo tem %d linhas"
                % (arquivo_ref, linha, total))

    # ---- 6. ordem das secoes --------------------------------------------
    numeros = [int(n) for n in re.findall(r"^## (\d+)\. ", texto, re.M)]
    for anterior, atual in zip(numeros, numeros[1:]):
        if atual < anterior:
            problemas.append("secoes fora de ordem: %d depois de %d"
                             % (atual, anterior))
            break

    # ---- resultado -------------------------------------------------------
    print("=" * 70)
    print("CHECK DO MANUAL - MANUAL_GRAFOS.md x codigo")
    print("=" * 70)
    print("Fases do pipeline conferidas: %d" % len(fases))
    print("Dependencias conferidas:      %d" % sum(len(v) for v in deps.values()))
    print("Linhas do manual:              %d" % len(texto.splitlines()))
    print("")

    for a in avisos:
        print("AVISO: %s" % a)
    if problemas:
        for p in problemas:
            print("[DESYNC] %s" % p)
        print("")
        print("MANUAL DESATUALIZADO (%d problema(s)). Atualize antes do push."
              % len(problemas))
        return 1

    print("[OK] Manual em dia com o codigo.")
    print("Proximo passo: commit + push da branch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
