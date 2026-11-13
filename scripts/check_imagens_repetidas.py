# -*- coding: utf-8 -*-
"""
Trava anti-imagem-repetida (MANUAL_GRAFOS.md 58.6 / CONTRATO.md 5.8).

Compara as imagens de cena de um projeto duas a duas (48x48, luminancia) e
falha quando duas sao praticamente iguais. E o bug que fez o Chihuahua repetir
a mesma foto de ~1:22 ao fim e o Restaurante repetir a mesma figura o video
inteiro - o video NAO pode ser renderizado nem publicado assim.

Uso:
  python scripts/check_imagens_repetidas.py                 # todos os projetos
  python scripts/check_imagens_repetidas.py --slug <slug>   # um projeto
  python scripts/check_imagens_repetidas.py --slug <slug> --tol 3.0 --max 5
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

EXTENSOES = ("*.jpg", "*.jpeg", "*.png")
# Abaixo disso as imagens sao consideradas a mesma figura (0-255).
TOL_PADRAO = 2.0


def _assinatura(caminho: Path):
    from PIL import Image
    img = Image.open(caminho).convert("L").resize((48, 48))
    return img.tobytes()


def _distancia(a, b) -> float:
    total = 0
    for x, y in zip(a, b):
        d = x - y
        total += d if d >= 0 else -d
    return total / float(len(a))


def conferir_projeto(pasta: Path, tol: float, max_pares: int):
    try:
        from PIL import Image  # noqa: F401
    except Exception:
        print("AVISO: Pillow nao instalado; checagem de imagem repetida pulada.")
        return []

    arquivos = []
    for ext in EXTENSOES:
        arquivos.extend(sorted(pasta.glob(ext)))
    arquivos = [f for f in arquivos if not f.name.startswith("_")]
    if len(arquivos) < 2:
        return []

    assinaturas = []
    for f in arquivos:
        try:
            assinaturas.append((f, _assinatura(f)))
        except Exception:
            continue

    repetidas = []
    for i in range(len(assinaturas)):
        for j in range(i + 1, len(assinaturas)):
            fa, sa = assinaturas[i]
            fb, sb = assinaturas[j]
            if _distancia(sa, sb) < tol:
                repetidas.append((fa.name, fb.name))
                if len(repetidas) >= max_pares:
                    return repetidas
    return repetidas


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Falha quando duas imagens de cena sao a mesma figura")
    ap.add_argument("--slug", default="", help="confere so este projeto")
    ap.add_argument("--projects-dir", default=str(ROOT / "projects"))
    ap.add_argument("--tol", type=float, default=TOL_PADRAO,
                    help=f"distancia media maxima (0-255) para considerar igual "
                         f"(padrao {TOL_PADRAO})")
    ap.add_argument("--max", type=int, default=8, help="maximo de pares listados")
    args = ap.parse_args()

    base = Path(args.projects_dir)
    if args.slug:
        projetos = [base / args.slug]
    else:
        projetos = sorted(p for p in base.iterdir() if p.is_dir())

    problemas = []
    total_imagens = 0
    for proj in projetos:
        pasta = proj / "assets" / "images" / "gemini" / "scenes"
        if not pasta.is_dir():
            continue
        n = len([f for f in pasta.iterdir() if f.suffix.lower() in (".jpg", ".jpeg", ".png")])
        total_imagens += n
        repetidas = conferir_projeto(pasta, args.tol, args.max)
        if repetidas:
            problemas.append((proj.name, repetidas))

    if problemas:
        print("=" * 70)
        print("TRACADO: imagem repetida (o video NAO pode ser renderizado assim)")
        print("=" * 70)
        for nome, pares in problemas:
            print(f"\n[{nome}] imagens praticamente iguais:")
            for a, b in pares:
                print(f"  - {a}  ==  {b}")
        print()
        print("O que fazer (MANUAL_GRAFOS.md 58.6):")
        print("  1. Apagar as imagens duplicadas da pasta de cenas.")
        print("  2. Regerar (gerar_capitulo_trilinguo.py): o flow_fetch agora")
        print("     descarta imagem igual a referencia e reenvia o prompt.")
        print("  3. Conferir 3-4 .jpg antes de renderizar.")
        print("  4. Se o video ja subiu assim: apagar no YouTube e reenviar.")
        return 1

    print(f"[OK] nenhuma imagem repetida ({total_imagens} imagem(ns) conferida(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
