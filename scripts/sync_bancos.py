# -*- coding: utf-8 -*-
r"""
Sincronizacao de bancos globais: varre todos os projetos e copia imagens
e músicas para as pastas do banco (se ja existirem, ignora).

Uso (manual, apos uma entrega):
    python scripts/sync_bancos.py

Destinos:
    C:\videomaker\banco de imagens\      (todas as .jpg de cena)
    C:\videomaker\banco de musicas\      (trilhas .wav e mix final .m4a)

Este script pode ser executado a qualquer momento sem danos: so copia o que
ainda nao existe no banco.
"""
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

BANCO_IMAGENS = ROOT / "banco de imagens"
BANCO_MUSICAS = ROOT / "banco de musicas"


def copy_if_missing(src: Path, dst_dir: Path, nome: str | None = None):
    """Copia src para dst_dir apenas se ainda nao existir la (ignora se existir).

    `nome` permite renomear o destino (ex.: `<slug>_musica.wav`) para evitar
    colisao entre projetos no banco.
    """
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / (nome or src.name)
    if dst.exists():
        return "ignorado (ja existe)"
    try:
        shutil.copyfile(src, dst)
        return "copiado"
    except Exception as e:
        return f"FALHA ({e})"


def sync_project(proj_dir: Path):
    """Sincroniza um unico projeto. Retorna lista de (origem, status)."""
    results = []
    scenes_dir = proj_dir / "assets" / "images" / "gemini" / "scenes"
    audio_dir = proj_dir / "assets" / "audio"

    if scenes_dir.exists():
        for jpg in sorted(scenes_dir.glob("*.jpg")):
            results.append((str(jpg), copy_if_missing(jpg, BANCO_IMAGENS)))

    # trilha bruta (gemini) apenas - nao copiar final_mix (contem narracao)
    if audio_dir.exists():
        gemini_dir = audio_dir / "gemini"
        if gemini_dir.exists():
            for idx, wav in enumerate(sorted(gemini_dir.glob("*.wav")), 1):
                sufixo = "" if idx == 1 else str(idx)
                nome = f"{proj_dir.name}_musica{sufixo}{wav.suffix}"
                results.append((str(wav), copy_if_missing(wav, BANCO_MUSICAS, nome)))

    return results


def main():
    projects_dir = ROOT / "projects"
    if not projects_dir.exists():
        print("Nenhuma pasta de projetos encontrada.")
        return 1

    BANCO_IMAGENS.mkdir(parents=True, exist_ok=True)
    BANCO_MUSICAS.mkdir(parents=True, exist_ok=True)

    total_img = 0
    total_mus = 0
    ignorados = 0
    falhas = 0

    for proj_dir in sorted(projects_dir.iterdir()):
        if not proj_dir.is_dir():
            continue
        print(f"== Varredura: {proj_dir.name}")
        for origem, status in sync_project(proj_dir):
            if status == "copiado":
                if "imagens" in origem or "scenes" in origem:
                    total_img += 1
                else:
                    total_mus += 1
                print(f"   [copiado] {Path(origem).name}")
            elif status.startswith("FALHA"):
                falhas += 1
                print(f"   [falha]   {Path(origem).name}: {status}")
            else:
                ignorados += 1

    print(f"\n== Banco de imagens: {total_img} nova(s) copiada(s)")
    print(f"== Banco de musicas: {total_mus} nova(s) copiada(s)")
    print(f"== Ignorados (ja existiam): {ignorados}")
    print(f"== Falhas: {falhas}")
    print(f"== Concluido.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
