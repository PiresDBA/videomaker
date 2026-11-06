# -*- coding: utf-8 -*-
"""
Publicação em lote simplificada - 7 vídeos no YouTube.
Sem descrição complexa (evita erro de caracteres especiais).
Apenas título, tags simples, thumbnail individual, público infantil.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROJECTS = ROOT / "projects"

VIDEOS = [
    {
        "slug": "frida-e-luna-descobrem-o-espelho",
        "video": "output/frida-e-luna-descobrem-o-espelho.mp4",
        "thumb": "assets/images/gemini/scenes/apresenta_o_scene.jpg",
        "title": "Frida e Luna Descobrem o Espelho - Desenho Animado Infantil",
    },
    {
        "slug": "luna-e-frida-descobrem-o-espelho-da-casa",
        "video": "output/luna-e-frida-descobrem-o-espelho-da-casa.mp4",
        "thumb": "assets/images/gemini/scenes/at_a_pr_xima_scene.jpg",
        "title": "Luna e Frida Descobrem o Espelho da Casa - Desenho Infantil",
    },
    {
        "slug": "por-que-o-cachorro-gira-antes-de-dei-98ff",
        "video": "output/por-que-o-cachorro-gira-antes-de-dei-98ff.mp4",
        "thumb": "assets/images/gemini/scenes/alerta_de_insetos_scene.jpg",
        "title": "Por Que o Cachorro Gira Antes de Deitar? - Desenho Infantil",
    },
    {
        "slug": "teste-10s-dentes-cachorro",
        "video": "output/teste-10s-dentes-cachorro.mp4",
        "thumb": "assets/images/gemini/scenes/escovacao_scene.jpg",
        "title": "Limpeza dos Dentes do Cachorro - Desenho Infantil",
    },
    {
        "slug": "video-educativo-sobre-banho-em-cachorro",
        "video": "output/video-educativo-sobre-banho-em-cachorro.mp4",
        "thumb": "assets/images/gemini/scenes/a_chacoalhada_nuclear_scene.jpg",
        "title": "O Banho do Cachorro - Desenho Animado Educativo",
    },
    {
        "slug": "video-engracado-sobre-buldogue-ingles-00",
        "video": "output/video-engracado-sobre-buldogue-ingles-00.mp4",
        "thumb": "assets/images/gemini/scenes/alimenta_o_e_gula_scene.jpg",
        "title": "O Buldogue Ingles - Desenho Animado para Criancas",
    },
    {
        "slug": "video-engracado-sobre-buldogue-ingles-divertido",
        "video": "output/video-engracado-sobre-buldogue-ingles-divertido.mp4",
        "thumb": "assets/images/gemini/scenes/alimenta_o_e_gula_scene.jpg",
        "title": "O Buldogue Ingles Mais Preguiçoso - Desenho Infantil",
    },
]

TAGS = "frida,luna,desenho animado,desenho infantil,cachorro,cachorrinha,buldogue,salsicha,animacao,infantil,criancas,familia,cartoon dog,kids animation,family animation,bulldog cartoon,dog cartoon"

def main():
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    published = 0
    failed = 0

    for v in VIDEOS:
        video_path = PROJECTS / v["slug"] / v["video"]
        thumb_path = PROJECTS / v["slug"] / v["thumb"]
        title = v["title"]

        if not video_path.exists():
            print(f"❌ VÍDEO NÃO ENCONTRADO: {video_path}")
            failed += 1
            continue

        thumb_str = str(thumb_path) if thumb_path.exists() else ""

        print(f"\n{'='*60}")
        print(f"📹 Publicando: {v['slug']}")
        print(f"   Título: {title}")
        print(f"   Thumbnail: {thumb_path.name if thumb_path.exists() else 'NENHUMA'}")
        print(f"{'='*60}")

        cmd = [
            sys.executable, str(HERE / "youtube_upload.py"),
            "--video", str(video_path),
            "--title", title,
            "--tags", TAGS,
            "--category", "24",
            "--privacy", "unlisted",
            "--made-for-kids",
            "--client-secret", str(HERE / "client_secret.json"),
            "--token", str(HERE / "youtube_token.json"),
        ]
        if thumb_str:
            cmd += ["--thumbnail", thumb_str]

        print(f"\n⏳ Enviando para o YouTube...")
        r = subprocess.run(cmd, cwd=str(HERE))
        if r.returncode == 0:
            print(f"✅ PUBLICADO: {v['slug']}")
            published += 1
        else:
            print(f"❌ FALHA: {v['slug']}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"📊 RESUMO: {published} publicado(s), {failed} falha(s)")
    print(f"{'='*60}")
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
