"""Sorteia um tema NOVO da fila oficial `scripts/topics.txt`.

A lista tem tres partes:
  * fila comum (uma linha por tema, na ordem do arquivo);
  * `# ----- USADOS -----` (temas ja viraram video; nunca sorteia de novo);
  * `# ----- datas especiais -----` (@MM-DD; so saem na data, nao no sorteio).

Uso:
  python scripts/select_topic.py                    # sorteia tema + slug
  python scripts/select_topic.py --list             # mostra fila e usados
  python scripts/select_topic.py --check "um tema"  # confere duplicidade
  python scripts/select_topic.py --seed 42          # sorteio reproduzivel
"""

from __future__ import annotations

import argparse
import difflib
import random
import re
import sys
import unicodedata
from pathlib import Path

TOPICS_FILE = Path(__file__).resolve().parent / "topics.txt"


def normalize(text: str) -> str:
    """Minusculo, sem acento e sem pontuacao (para comparar temas)."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", normalize(text)).strip("-")
    return slug[:50].strip("-")


def load_topics(path: Path = TOPICS_FILE):
    """Devolve (fila, usados). Ignora comentarios, blanks, datas e usados."""
    if not path.exists():
        raise FileNotFoundError(f"fila de temas nao encontrada: {path}")

    fila: list[str] = []
    usados: list[str] = []
    secao = "fila"

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            upper = normalize(line)
            if upper.startswith("usados"):
                secao = "usados"
            elif upper.startswith("datas especiais"):
                secao = "datas"
            continue
        if secao == "usados":
            usados.append(line.split("|", 1)[0].strip())
        elif secao == "fila" and not line.startswith("@"):
            fila.append(line)

    return fila, usados


def temas_novos(fila, usados):
    ja_usados = {normalize(t) for t in usados}
    return [t for t in fila if normalize(t) not in ja_usados]


def parecidos(tema: str, candidatos: list[str], limite: float = 0.86):
    """Temas iguais ou muito parecidos (para barrar repeticao)."""
    alvo = normalize(tema)
    achados = []
    for cand in candidatos:
        atual = normalize(cand)
        if atual == alvo:
            achados.append((1.0, cand))
            continue
        if alvo in atual or atual in alvo:
            achados.append((0.99, cand))
            continue
        ratio = difflib.SequenceMatcher(None, alvo, atual).ratio()
        if ratio >= limite:
            achados.append((ratio, cand))
    return sorted(achados, reverse=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Sorteia tema novo da fila oficial")
    ap.add_argument("--list", action="store_true", help="lista fila e usados")
    ap.add_argument("--check", default="", help="confere se o tema ja existe")
    ap.add_argument("--seed", type=int, default=None, help="semente do sorteio")
    ap.add_argument("--limit", type=int, default=15, help="itens no --list")
    args = ap.parse_args(argv)

    fila, usados = load_topics()
    novos = temas_novos(fila, usados)

    if args.list:
        print(f"fila: {len(fila)} temas | usados: {len(usados)} | "
              f"disponiveis: {len(novos)}")
        print("\nUSADOS:")
        for tema in usados or ["(nenhum)"]:
            print(f"  - {tema}")
        print("\nPROXIMOS DA FILA:")
        for tema in novos[:args.limit]:
            print(f"  - {tema}")
        return 0

    if args.check:
        achados = parecidos(args.check, fila + usados)
        if not achados:
            print(f"OK: nenhum tema parecido com '{args.check}'.")
            print("Acrescente o tema novo na fila (antes de '# ----- USADOS -----').")
            return 0
        print(f"ATENCAO: '{args.check}' parece repetido:")
        for ratio, tema in achados[:8]:
            print(f"  {ratio:.0%}  {tema}")
        return 2

    if not novos:
        print("ERRO: todos os temas da fila ja foram usados. "
              "Acrescente novos temas em scripts/topics.txt.", file=sys.stderr)
        return 1

    rng = random.Random(args.seed)
    tema = rng.choice(novos)
    print("Topico selecionado:")
    print(tema)
    print(f"\nDisponiveis: {len(novos)} de {len(fila)}")
    print("Slug sugerido:")
    print(slugify(tema))
    print("\nAo terminar o video, registre em '# ----- USADOS -----':")
    print(f"{tema} | {slugify(tema)} | AAAA-MM-DD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
