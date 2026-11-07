#!/usr/bin/env python3
"""Teste de pipeline - seleciona um topico aleatorio e executa o pipeline completo.

Este script simula a execucao de um pipeline completo para um novo topico,
checa se nao existe projeto local ou entrega anterior, e depois executa
o pipeline.

Uso:
    python scripts/run_pipeline_test.py
"""

import json
import os
import random
import subprocess
import sys
from pathlib import Path

# Defini��es de caminhos
ROOT = Path("C:/videomaker")

# Carrega topicos da fila de topics.txt
with open(ROOT / "scripts" / "topics.txt", encoding="utf-8") as f:
    raw = f.read()

tops = []
for line in raw.splitlines():
    line = line.strip()
    if line and not line.startswith("#"):
        tops.append(line)

if not tops:
    print("Nenhum topico valido encontrado em scripts/topics.txt")
    sys.exit(1)

# Carrega entregas existentes
with open(ROOT / "projects-deliveries.json", encoding="utf-8") as f:
    entregas = json.load(f).get("delivered", [])

print("FILA DE TOPICOS: %d" % len(tops))
print("PROJETOS ENTREGUES: %d" % len(entregas))
print()

# Para cada topico, checa se ja existe projeto local ou foi entregue
a_usar = []
for t in tops:
    # Normaliza o t��pico para compara��o (sem acentos, min�sculas, sem s�mbolos especiais)
    t_norm = "".join(c for c in t.lower() if c.isalnum() or c.isspace())
    t_norm = " ".join(t_norm.split())
    
    # Nome do slug: removed acentos e s�mbolos especiais
    s = t_norm.replace(" ", "-")
    
    # Verifica se o projeto ja existe localmente
    existe = os.path.exists(ROOT / "projects" / s)
    # Verifica se o t��pico j� foi entregue (por prompt ou slug)
    entregue = any(
        (x.get("slug") or "") == s
        or (x.get("prompt") or "").strip().lower() == t.lower()
        for x in entregas
    )
    if existe or entregue:
        continue
    a_usar.append(t)

if not a_usar:
    print("Todos os topicos ja estao em uso (projeto local ou entregue).")
    sys.exit(1)

# Escolhe aleatoriamente um topico para o teste
new_topic = random.choice(a_usar)
print("TOPICO ESCOLHIDO para o teste:", new_topic)

# Verifica novamente
if not new_topic:
    print("Erro inesperado: nenhum topico selecionado.")
    sys.exit(1)

print("\nExecutando o pipeline para topico:", new_topic)

# Executa o pipeline com o topico escolhido
print("\n===============================================")
print("EXECUTANDO O PIPELINE COMPLETO")
print("===============================================")
result = subprocess.run(
    [
        sys.executable,
        "scripts/pipeline.py",
        "full",
        "--prompt", new_topic,
        "--publish",
        "--wait", "420",
        "--pause", "8",
        "--narration-provider", "gemini",
        "--yt-title", new_topic,
        "--skip-check",
    ],
    capture_output=True,
    text=True,
)

print(result.stdout)
if result.stderr:
    print("STDERR:")
    print(result.stderr)

if result.returncode != 0:
    print("\nPIPELINE FALHOU (exit code: %d)" % result.returncode)
    sys.exit(result.returncode)
else:
    print("\nSUCESSO: O pipeline concluiu com sucesso!")
    print("Um novo v�deo foi publicado no YouTube com a descri��o no padr�o.")

print("\nFim do teste de pipeline. Parabens!")
