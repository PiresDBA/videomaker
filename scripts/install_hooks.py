# -*- coding: utf-8 -*-
"""
Instala os hooks do Videomaker (`.githooks/`) no clone atual.

Os hooks travam os erros que ja aconteceram de verdade:
  * prompt mandando copiar a imagem de referencia (CONTRATO.md 5.8);
  * video com a mesma figura repetida em varias pausas (MANUAL_GRAFOS.md 58.6);
  * MANUAL_GRAFOS.md fora de sincronia com o codigo;
  * .py commitado com erro de sintaxe.

Uso:
  python scripts/install_hooks.py            # instala
  python scripts/install_hooks.py --status   # so mostra o estado
"""
import argparse
import os
import stat
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
HOOKS = ROOT / ".githooks"
ESPERADOS = ("pre-commit", "pre-push")


def _git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(ROOT),
                       capture_output=True, text=True)
    return (r.stdout or "").strip()


def status() -> int:
    atual = _git("config", "--get", "core.hooksPath")
    print(f"core.hooksPath = {atual or '(nao definido)'}")
    problemas = 0
    if atual.replace("\\", "/") != ".githooks":
        print("  -> hooks NAO estao ativos (esperado: .githooks)")
        problemas += 1
    for nome in ESPERADOS:
        arq = HOOKS / nome
        if not arq.exists():
            print(f"  -> falta {arq}")
            problemas += 1
        elif os.name != "nt" and not (arq.stat().st_mode & stat.S_IEXEC):
            print(f"  -> sem permissao de execucao: {arq}")
            problemas += 1
    return 0 if problemas == 0 else 1


def instalar() -> int:
    if not (ROOT / ".git").exists():
        print("ERRO: nao e um repositorio git.")
        return 1
    if _git("config", "--get", "core.hooksPath").replace("\\", "/") == ".githooks":
        print("[OK] hooks ja instalados (core.hooksPath = .githooks)")
    else:
        subprocess.run(["git", "config", "core.hooksPath", ".githooks"],
                       cwd=str(ROOT), check=True)
        print("[OK] core.hooksPath = .githooks")

    for nome in ESPERADOS:
        arq = HOOKS / nome
        if not arq.exists():
            print(f"ERRO: hook ausente: {arq}")
            return 1
        arq.chmod(arq.stat().st_mode | stat.S_IEXEC)

    print("[OK] hooks ativos: " + ", ".join(ESPERADOS))
    print("Nao use 'git commit --no-verify' nem 'git push --no-verify' para furar.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Instala os hooks do .githooks")
    ap.add_argument("--status", action="store_true", help="so mostra o estado")
    args = ap.parse_args()
    return status() if args.status else instalar()


if __name__ == "__main__":
    sys.exit(main())
