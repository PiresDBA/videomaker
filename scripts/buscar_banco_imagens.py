#!/usr/bin/env python3
"""
buscar_banco_imagens.py - Busca no banco de imagens locais (indice_midia.db)
uma imagem adequada para uma cena específica.

Uso:
  python buscar_banco_imagens.py --descricao "cachorro bulldog dormindo no sofa"
  python buscar_banco_imagens.py --descricao "luna dachshund brincando" --limite 5

Retorna o caminho da melhor imagem encontrada ou vazio se nada adequado.
"""
import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

BANCO_IMAGENS = Path(r"C:\videomaker\banco de imagens")
DB_PATH = BANCO_IMAGENS / "indice_midia.db"


def normalizar_texto(t: str) -> str:
    """Remove acentos e caracteres especiais para comparação."""
    import unicodedata
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", t).strip().lower()


def extrair_palavras_chave(texto: str) -> list:
    """Extrai palavras importantes de uma descrição de cena."""
    texto = normalizar_texto(texto)
    # Remove palavras comuns (stop words simples em português)
    stop = {"o", "a", "os", "as", "um", "uma", "de", "do", "da", "dos", "das",
            "e", "em", "no", "na", "nos", "nas", "por", "para", "com", "sem",
            "sobre", "entre", "que", "quem", "qual", "se", "nao", "nao", "eh",
            "ser", "estar", "tem", "tem", "vai", "foi", "era", "sera", "ja",
            "ja", "sao", "são", "esta", "esta", "estao", "estão", "mais", "menos",
            "muito", "bem", "mal", "sim", "nao", "nao"}
    palavras = re.findall(r"\w+", texto)
    return [p for p in palavras if p not in stop and len(p) > 2]


def buscar_imagem_no_banco(descricao_cena: str, limite: int = 5) -> str | None:
    """
    Busca no banco SQLite (indice_midia.db) uma imagem adequada para a cena.
    Retorna o caminho do arquivo JPG ou None se não encontrar nada adequado.
    """
    if not DB_PATH.exists():
        return None

    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row

    palavras = extrair_palavras_chave(descricao_cena)
    if not palavras:
        db.close()
        return None

    # Monta consulta FTS com AND entre as palavras principais (mais restritivo primeiro)
    # Se não encontrar, relaxa para OR
    termos_quoted = [f'"{t}"' for t in palavras]
    consulta_and = " AND ".join(termos_quoted)
    consulta_or = " OR ".join(termos_quoted)

    resultados = []

    # Tenta AND primeiro (mais preciso)
    try:
        rows = db.execute(
            "SELECT caminho, descricao, palavras_chave, bm25(busca) AS r "
            "FROM busca WHERE busca MATCH ? ORDER BY r LIMIT ?",
            (consulta_and, limite * 2)
        ).fetchall()
        for r in rows:
            resultados.append({
                "caminho": r["caminho"],
                "descricao": r["descricao"] or "",
                "palavras_chave": r["palavras_chave"] or "",
                "score": r["r"],
                "match_tipo": "AND"
            })
    except Exception:
        pass

    # Se não encontrou com AND, tenta OR
    if not resultados:
        try:
            rows = db.execute(
                "SELECT caminho, descricao, palavras_chave, bm25(busca) AS r "
                "FROM busca WHERE busca MATCH ? ORDER BY r LIMIT ?",
                (consulta_or, limite * 2)
            ).fetchall()
            for r in rows:
                resultados.append({
                    "caminho": r["caminho"],
                    "descricao": r["descricao"] or "",
                    "palavras_chave": r["palavras_chave"] or "",
                    "score": r["r"],
                    "match_tipo": "OR"
                })
        except Exception:
            pass

    db.close()

    if not resultados:
        return None

    # Filtra: o arquivo deve existir fisicamente
    validos = []
    for r in resultados:
        if Path(r["caminho"]).exists():
            validos.append(r)

    if not validos:
        return None

    # Ordena por score (bm25 menor é melhor)
    validos.sort(key=lambda x: x["score"])

    # Retorna o melhor
    melhor = validos[0]
    return melhor["caminho"]


def listar_imagens_disponiveis(descricao_cena: str, limite: int = 10) -> list:
    """
    Retorna lista de imagens candidatas do banco, ordenadas por relevância.
    """
    if not DB_PATH.exists():
        return []

    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row

    palavras = extrair_palavras_chave(descricao_cena)
    if not palavras:
        db.close()
        return []

    consulta_or = " OR ".join([f'"{t}"' for t in palavras])

    try:
        rows = db.execute(
            "SELECT caminho, descricao, palavras_chave, bm25(busca) AS r "
            "FROM busca WHERE busca MATCH ? ORDER BY r LIMIT ?",
            (consulta_or, limite * 3)
        ).fetchall()
    except Exception:
        db.close()
        return []

    resultados = []
    for r in rows:
        caminho = r["caminho"]
        if Path(caminho).exists():
            resultados.append({
                "caminho": caminho,
                "descricao": r["descricao"] or "",
                "palavras_chave": r["palavras_chave"] or "",
                "score": r["r"],
            })

    db.close()
    resultados.sort(key=lambda x: x["score"])
    return resultados[:limite]


def main():
    ap = argparse.ArgumentParser(description="Busca imagem no banco local por descrição de cena")
    ap.add_argument("--descricao", required=True, help="Descrição da cena para buscar imagem")
    ap.add_argument("--limite", type=int, default=5, help="Número de resultados a retornar")
    ap.add_argument("--listar", action="store_true", help="Lista todos os candidatos em vez de só o melhor")
    args = ap.parse_args()

    if args.listar:
        candidatos = listar_imagens_disponiveis(args.descricao, args.limite)
        if not candidatos:
            print("Nenhuma imagem encontrada no banco local.")
            return 0
        print(f"=== {len(candidatos)} imagem(ns) candidata(s) para: '{args.descricao}' ===")
        for i, c in enumerate(candidatos, 1):
            print(f"{i}. {Path(c['caminho']).name}")
            print(f"   Caminho: {c['caminho']}")
            print(f"   Descricao: {c['descricao'][:150]}")
            print(f"   Palavras-chave: {c['palavras_chave'][:100]}")
            print()
    else:
        resultado = buscar_imagem_no_banco(args.descricao, args.limite)
        if resultado:
            print(resultado)
            return 0
        else:
            print("Nenhuma imagem adequada encontrada no banco local.")
            return 1


if __name__ == "__main__":
    sys.exit(main())
