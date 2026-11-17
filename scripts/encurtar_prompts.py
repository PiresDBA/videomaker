# -*- coding: utf-8 -*-
r"""encurtar_prompts.py - converte image_prompts.json longo/PT em prompts curtos/EN.

Motivo (2026-11-17): o filtro do Google Flow rejeita prompts longos com muito
texto em portugues ("Falha -Esta geracao talvez viole nossas politicas").
Prompts CURTOS em ingles funcionam na primeira tentativa e mantem os personagens.

Le:  <proj>/artifacts/image_prompts.json  (prompt longo atual)
Grava: <proj>/artifacts/image_prompts_short.json  (nome -> prompt curto EN)

O prompt curto contem:
  - estilo (Pixar 3D, 16:9)
  - identidade FIXA de Frida e Luna (pelo nome +racas/cores)
  - a CENA (primeira linha do prompt original, em PT -> mantida curta)
  - proibicoes basicas (sem humanos, gatos, texto)
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent

IDENTIDADE = (
    "Pixar-style 3D cartoon, 16:9. Use the SAME two dogs in every image: "
    "FRIDA = a big fawn English bulldog with a pearl necklace; "
    "LUNA = a long low chocolate-brown dachshund (sausage dog) with a gold collar. "
)

REGRAS = (
    " No humans, no cats, no other dog breeds. No text, no words. "
    "The red dog bed with golden hearts looks identical in every image."
)


def extrair_cena(prompt: str) -> str:
    """Pega so a descricao da CENA (primeira linha, apos 'CENA ...:')."""
    first = (prompt or "").splitlines()[0] if prompt else ""
    if first.startswith("CENA"):
        first = first.split(":", 1)[1].strip() if ":" in first else first
    # remove risadas e excesso
    first = re.sub(r"\bHahaha+\b[!.]*", "", first, flags=re.I)
    first = re.sub(r"\s{2,}", " ", first).strip(" .,")
    return first[:220] or "the dogs in the living room"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proj", required=True)
    a = ap.parse_args()
    p = Path(a.proj)
    src = p / "artifacts" / "image_prompts.json"
    dst = p / "artifacts" / "image_prompts_short.json"
    d = json.loads(src.read_text(encoding="utf-8"))
    out = {}
    for k, v in d.items():
        if k.startswith("_"):
            continue
        cena = extrair_cena(v)
        out[k] = IDENTIDADE + "Scene: " + cena + "." + REGRAS
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("escrito:", dst, "(", len(out), "prompts, ~",
          sum(len(x) for x in out.values()) // len(out), "chars cada )")


if __name__ == "__main__":
    main()
