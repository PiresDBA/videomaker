# -*- coding: utf-8 -*-
"""detecta_paineis.py - classifica cada imagem de cena em:
   1 painel (imagem unica) | 2 | 3 | 4 paineis (colagem).

Metodo: uma colagem tem linhas divisorias finas (retas, claras) em posicoes
tipicas (1/2; 1/3,2/3; 1/4,2/4,3/4). Mede o "salto" de cor ao longo da linha
e da continuidade vertical: linha divisoria real tem salto alto e constante
por quase toda a altura.
"""
from __future__ import annotations
import sys
from pathlib import Path
from io import BytesIO

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from PIL import Image
import numpy as np

SCENES = Path(r"C:\videomaker\projects\a-caminha-nova-que-ninguem-quer-usar\assets\images\gemini\scenes")


def _score_line(a, x, axis):
    """Quao 'linha divisoria' parece a coluna x (axis=1 vertical) ou linha y."""
    h, w = a.shape[:2]
    if axis == 1:  # linha vertical na coluna x
        if x < 8 or x > w - 8:
            return 0.0
        left = a[:, max(0, x - 3):x].mean(axis=1)
        right = a[:, x + 1:min(w, x + 4)].mean(axis=1)
    else:  # linha horizontal na linha y
        if x < 8 or x > h - 8:
            return 0.0
        left = a[max(0, x - 3):x, :].mean(axis=0)
        right = a[x + 1:min(h, x + 4), :].mean(axis=0)
    diff = np.abs(left - right).mean(axis=-1)
    # salto forte em >=60% do percurso = divisoria
    return float((diff > 28).mean())


def n_paineis(path: Path) -> int:
    im = Image.open(path).convert("RGB")
    im.thumbnail((640, 640))
    a = np.asarray(im).astype(float)
    h, w = a.shape[:2]
    # candidato vertical: halves/tercos/quarters
    vlines = {2: [w // 2], 3: [w // 3, 2 * w // 3], 4: [w // 4, w // 2, 3 * w // 4]}
    hlines = {2: [h // 2], 3: [h // 3, 2 * h // 3], 4: [h // 4, h // 2, 3 * h // 4]}
    best = 1
    for n, xs in vlines.items():
        if all(_score_line(a, x, 1) > 0.55 for x in xs):
            best = max(best, n)
    for n, ys in hlines.items():
        if all(_score_line(a, y, 0) > 0.55 for y in ys):
            best = max(best, n)
    return best


def main():
    out = {}
    for f in sorted(SCENES.glob("*.jpg")):
        try:
            out[f.name] = n_paineis(f)
        except Exception:
            out[f.name] = 1
    for k, v in out.items():
        print(v, k)
    import json
    (SCENES.parent / "paineis_manifest.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("gravado paineis_manifest.json")


if __name__ == "__main__":
    main()
