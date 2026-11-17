# -*- coding: utf-8 -*-
"""Teste rapido (sem Chrome) das variacoes de painel - MANUAL_GRAFOS.md §60.

  python scripts/test_paineis.py
"""
from io import BytesIO
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image

import flow_agent_batch as fab


def img_bytes(w, h, color="orange"):
    buf = BytesIO()
    Image.new("RGB", (w, h), color).save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print("  ok:", msg)


def main():
    print("dividir_colagem:")
    # colagem larga (3 colunas) -> 3 paineis
    largos = fab.dividir_colagem(img_bytes(1800, 600), 3, "lado_a_lado")
    check(len(largos) == 3, "colagem larga -> 3 paineis")
    check(all(Image.open(BytesIO(b)).size[1] == 600
              and 585 <= Image.open(BytesIO(b)).size[0] <= 600 for b in largos),
          "paineis largos ~600x600 (margem das linhas divisoriais)")

    # colagem alta (3 linhas) -> 3 paineis
    altos = fab.dividir_colagem(img_bytes(600, 1800), 3, "empilhado")
    check(len(altos) == 3, "colagem alta -> 3 paineis")
    check(all(Image.open(BytesIO(b)).size[0] == 600
              and 585 <= Image.open(BytesIO(b)).size[1] <= 600 for b in altos),
          "paineis altos ~600x600 (margem das linhas divisoriais)")

    # colagem 16:9 com paineis internos -> preservada inteira (efeito quadrinho)
    inteira = fab.dividir_colagem(img_bytes(1280, 720), 3, "lado_a_lado")
    check(len(inteira) == 1, "colagem 16:9 preservada inteira")
    check(Image.open(BytesIO(inteira[0])).size == (1280, 720),
          "dimensoes da colagem 16:9 mantidas")

    print("montar_prompt_lote:")
    itens = [("cena_a", "CENA 1"), ("cena_b", "CENA 2"), ("cena_c", "CENA 3")]
    p_emp = fab.montar_prompt_lote(itens, "", colagem=True,
                                   orientacao="empilhado", n_paineis=3)
    check("EMPILHADOS" in p_emp and "de cima para baixo" in p_emp,
          "prompt empilhado descreve ordem de cima para baixo")

    p_lado = fab.montar_prompt_lote(itens, "", colagem=True,
                                    orientacao="lado_a_lado", n_paineis=3)
    check("LADO A LADO" in p_lado and "da esquerda" in p_lado,
          "prompt lado a lado descreve ordem da esquerda para a direita")

    p4 = fab.montar_prompt_lote(itens + [("cena_d", "CENA 4")], "", colagem=True,
                                orientacao="empilhado", n_paineis=4)
    check("4 paineis" in p4 or "4 paineis HORIZONTAIS" in p4,
          "prompt aceita 4 paineis")

    p_sep = fab.montar_prompt_lote(itens, "", colagem=False)
    check("SEPARADAS" in p_sep, "prompt sem colagem pede imagens separadas")

    todos = " ".join((p_emp, p_lado, p4, p_sep)).lower()
    check("siga a imagem de referencia anexada para tudo" not in todos,
          "nenhum prompt manda copiar a referencia")
    print("\n[OK] variacoes de painel validadas")


if __name__ == "__main__":
    main()
