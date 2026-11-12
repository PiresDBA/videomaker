# -*- coding: utf-8 -*-
"""Sobe os vídeos de cada idioma para o canal do idioma, repetindo enquanto
houber envios (respeita a cota diária da YouTube Data API).

É o "programa que faz loop e sobe tudo". Rode quantas vezes quiser; ele para
sozinho quando não houver mais nada para publicar nos canais selecionados.

Uso:
  python scripts/loop_upload_idiomas.py           # EN e ES (até a cota)
  python scripts/loop_upload_idiomas.py --langs pt,en,es
  python scripts/loop_upload_idiomas.py --limite 3  # no máximo 3 uploads por canal por ciclo

Cota: ~6 uploads por canal por dia (videos.insert = 1600 de 10.000 unidades).
Quando a cota acaba, o upload_por_idioma pára sozinho. Rode este script de novo
amanhã para continuar de onde parou.
"""
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def ciclo(lang, extra):
    """Roda upload_por_idioma.py --all para um idioma. Retorna 0 se enviou algo,
    1 se não enviou nada (terminou) ou se houve erro."""
    cmd = [sys.executable, str(HERE / "upload_por_idioma.py"), lang, "--all"] + extra
    print("\n" + "#" * 70)
    print("# CANAL", lang.upper())
    print("#" * 70, flush=True)
    r = subprocess.run(cmd)
    return r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", default="en,es",
                    help="idiomas a subir, separados por vírgula (padrão: en,es)")
    ap.add_argument("--limite", type=int, default=0,
                    help="máximo de uploads por ciclo (0 = ignora, sobe tudo até a cota)")
    a = ap.parse_args()

    langs = [x.strip() for x in a.langs.split(",") if x.strip()]
    extra = []
    if a.limite > 0:
        extra = ["--limit", str(a.limite)]

    print("Canal(s):", ", ".join(l.upper() for l in langs))
    print("Cota estimada: ~6 uploads/canal/dia. Se acabar, rode de novo amanhã.\n")

    for lang in langs:
        rc = ciclo(lang, extra)
        if rc != 0:
            print(f"\n{lang.upper()}: parou (rc={rc}). Provavelmente cota esgotada.")

    print("\n" + "=" * 70)
    print("LOOP CONCLUÍDO. Relatórios acima.")
    print("Se ainda houver pendentes, rode este script de novo (amanhã, se a cota acabou).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
