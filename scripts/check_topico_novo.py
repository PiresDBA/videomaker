"""Lembrete/trava da fila de temas: todo video novo sai de scripts/topics.txt.

Este script roda no pre-commit (e pode ser chamado a mao). Ele NAO cria video:
so garante que a fila existe, tem temas livres e lembra o fluxo obrigatorio:

  1. ler scripts/topics.txt;
  2. sortear com `python scripts/select_topic.py`;
  3. conferir duplicidade com `--tema "..."`;
  4. registrar o tema usado em `# ----- USADOS -----`.

Falha (exit 1) se a fila nao existe/esta vazia ou se todos os temas ja foram
usados - nesse caso, acrescente temas novos antes de criar o proximo video.
"""

from __future__ import annotations

import argparse
import sys

from select_topic import load_topics, normalize, parecidos, temas_novos


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Confere a fila de temas de video")
    ap.add_argument("--tema", default="", help="tema que sera usado no video")
    ap.add_argument("--quiet", action="store_true", help="sem lembrete na tela")
    args = ap.parse_args(argv)

    try:
        fila, usados = load_topics()
    except FileNotFoundError as exc:
        print(f"BLOQUEADO: {exc}", file=sys.stderr)
        print("Recrie a fila em scripts/topics.txt (CONTRATO.md 5.11).",
              file=sys.stderr)
        return 1

    if not fila:
        print("BLOQUEADO: scripts/topics.txt esta sem temas na fila.",
              file=sys.stderr)
        return 1

    novos = temas_novos(fila, usados)
    if not novos:
        print("BLOQUEADO: todos os temas da fila ja foram usados. "
              "Acrescente temas novos antes do proximo video.", file=sys.stderr)
        return 1

    if args.tema:
        achados = parecidos(args.tema, fila + usados)
        if achados:
            print(f"BLOQUEADO: '{args.tema}' repete um tema da lista:",
                  file=sys.stderr)
            for ratio, tema in achados[:8]:
                print(f"  {ratio:.0%}  {tema}", file=sys.stderr)
            return 1
        if normalize(args.tema) not in {normalize(t) for t in fila}:
            print(f"AVISO: '{args.tema}' nao esta na fila. "
                  "Acrescente antes de usar (CONTRATO.md 5.11).")

    if not args.quiet:
        print(f"[temas] fila ok: {len(novos)} tema(s) livre(s) de {len(fila)}.")
        print("[temas] Video novo? Leia scripts/topics.txt, rode "
              "`python scripts/select_topic.py` e registre o usado em "
              "'# ----- USADOS -----'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
