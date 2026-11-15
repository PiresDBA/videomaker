#!/usr/bin/env python3
"""Atualiza selfDeclaredMadeForKids=False em todos os vídeos de um canal."""
import json
import sys
from pathlib import Path

# Adiciona scripts/ ao caminho para importar get_service
sys.path.insert(0, str(Path(__file__).resolve().parent))
from youtube_metadados import get_service


def listar_todos_videos(svc):
    """Lista todos os vídeos do canal (com paginação)."""
    videos = []
    request = svc.search().list(
        part="id",
        forMine=True,
        type="video",
        maxResults=50,
    )
    while request:
        response = request.execute()
        for item in response.get("items", []):
            videos.append(item["id"]["videoId"])
        request = svc.search().list_next(request, response)
    return videos


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/atualizar_kids.py <pt|en|es>")
        return 1

    lang = sys.argv[1].lower()
    if lang not in ("pt", "en", "es"):
        print(f"Idioma invalido: {lang}. Use: pt, en, es")
        return 1

    print(f"Autenticando no canal {lang.upper()}...")
    svc = get_service(lang)

    print(f"Listando todos os vídeos do canal {lang.upper()}...")
    video_ids = listar_todos_videos(svc)
    print(f"Encontrados {len(video_ids)} vídeo(s).")

    atualizados = 0
    erros = 0
    for i, vid in enumerate(video_ids, 1):
        try:
            body = {
                "id": vid,
                "status": {"selfDeclaredMadeForKids": False},
            }
            svc.videos().update(part="status", body=body).execute()
            print(f"  [{i}/{len(video_ids)}] OK: {vid} -> madeForKids=False")
            atualizados += 1
        except Exception as e:
            print(f"  [{i}/{len(video_ids)}] ERRO: {vid} -> {e}")
            erros += 1

    print(f"\nResultado: {atualizados} atualizado(s), {erros} erro(s), {len(video_ids)} total.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
