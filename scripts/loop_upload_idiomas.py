# -*- coding: utf-8 -*-
"""Sobe os videos de cada idioma para o canal do idioma, respeitando a cota.

Rode UMA VEZ POR DIA. A cota da YouTube Data API e 10.000 unidades por
projeto Google por dia; cada upload custa ~1.600. Ou seja, ~6 videos por
canal por dia. O script para sozinho quando a cota acaba e retoma no dia
seguinte de onde parou (historico em scripts/.publish_history_idioma.json).

Uso:
  python scripts/loop_upload_idiomas.py              # EN e ES
  python scripts/loop_upload_idiomas.py --langs en,es,pt
  python scripts/loop_upload_idiomas.py --dry-run
"""
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def rodar(lang, extra):
    cmd = [sys.executable, str(HERE / "upload_por_idioma.py"), lang, "--all"] + extra
    print("\n" + "#" * 70)
    print("# CANAL", lang.upper())
    print("#" * 70, flush=True)
    r = subprocess.run(cmd)
    return r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", default="en,es")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    langs = [x.strip() for x in a.langs.split(",") if x.strip()]
    extra = ["--dry-run"] if a.dry_run else []

    falhas = {}
    for lang in langs:
        rc = rodar(lang, extra)
        if rc != 0:
            falhas[lang] = rc

    print("\n" + "=" * 70)
    print("RESUMO FINAL")
    print("=" * 70)
    for lang in langs:
        print(f"  {lang.upper()}: {'ok' if lang not in falhas else 'falhou rc=%s' % falhas[lang]}")
    print("\nSe a cota acabou, rode este comando de novo amanha.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
