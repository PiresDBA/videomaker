# -*- coding: utf-8 -*-
"""
Publicação em lote de 7 vídeos no YouTube.
Conteúdo infantil (made for kids), português do Brasil, categoria Entretenimento.
Cada vídeo recebe sua própria thumbnail (imagem do próprio projeto).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROJECTS = ROOT / "projects"

# Lista de vídeos para publicar com seus respectivos thumbnails
VIDEOS = [
    {
        "slug": "frida-e-luna-descobrem-o-espelho",
        "video": "output/frida-e-luna-descobrem-o-espelho.mp4",
        "thumb": "assets/images/gemini/scenes/apresenta_o_scene.jpg",
        "title": "Frida e Luna Descobrem o Espelho - Desenho Animado para Crianças",
        "prompt": "Frida, Luna e o Espelho Mágico",
    },
    {
        "slug": "luna-e-frida-descobrem-o-espelho-da-casa",
        "video": "output/luna-e-frida-descobrem-o-espelho-da-casa.mp4",
        "thumb": "assets/images/gemini/scenes/at_a_pr_xima_scene.jpg",
        "title": "Luna e Frida Descobrem o Espelho da Casa - Desenho Animado para Crianças",
        "prompt": "O Mistério do Espelho Mágico da Luna e da Frida",
    },
    {
        "slug": "por-que-o-cachorro-gira-antes-de-dei-98ff",
        "video": "output/por-que-o-cachorro-gira-antes-de-dei-98ff.mp4",
        "thumb": "assets/images/gemini/scenes/alerta_de_insetos_scene.jpg",
        "title": "Por Que o Cachorro Gira Antes de Deitar? - Desenho Animado Infantil",
        "prompt": "Por que o cachorro gira antes de deitar?",
    },
    {
        "slug": "teste-10s-dentes-cachorro",
        "video": "output/teste-10s-dentes-cachorro.mp4",
        "thumb": "assets/images/gemini/scenes/escovacao_scene.jpg",
        "title": "Limpeza dos Dentes do Cachorro - Desenho Infantil Educativo",
        "prompt": "Limpeza dos dentes do cachorro",
    },
    {
        "slug": "video-educativo-sobre-banho-em-cachorro",
        "video": "output/video-educativo-sobre-banho-em-cachorro.mp4",
        "thumb": "assets/images/gemini/scenes/a_chacoalhada_nuclear_scene.jpg",
        "title": "O Banho do Cachorro - Desenho Animado Educativo para Crianças",
        "prompt": "A Incrível Odisseia do Banho Canino",
    },
    {
        "slug": "video-engracado-sobre-buldogue-ingles-00",
        "video": "output/video-engracado-sobre-buldogue-ingles-00.mp4",
        "thumb": "assets/images/gemini/scenes/alimenta_o_e_gula_scene.jpg",
        "title": "O Guia Definitivo do Buldogue Inglês - Desenho Animado para Crianças",
        "prompt": "O Guia Definitivo do Buldogue Inglês: Apanhados, Roncos e Muita Fofura",
    },
    {
        "slug": "video-engracado-sobre-buldogue-ingles-divertido",
        "video": "output/video-engracado-sobre-buldogue-ingles-divertido.mp4",
        "thumb": "assets/images/gemini/scenes/alimenta_o_e_gula_scene.jpg",
        "title": "O Buldogue Inglês Mais Preguiçoso - Desenho Animado para Crianças",
        "prompt": "O Buldogue Inglês: O Cão Mais Preguiçoso, Roncador e Divertido",
    },
]

def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def build_description(title, prompt):
    """Constrói descrição completa em português do Brasil para público infantil."""
    desc = f"""🐶 {title}

🎬 SINOPSE
{prompt if prompt else "Uma aventura divertida e cheia de surpresas para toda a família!"}

✨ PERSONAGENS PRINCIPAIS
• Luna: salsicha marrom-chocolate, ~11 anos, briguenta, ciumenta, chefona da casa, sempre lidera as aventuras
• Frida: buldogue inglesa fawn (amarela), ~30 kg, tranquila, preguiçosa, gulosa, obedece a Luna em tudo

👨‍👩‍👧‍👦 PARA TODA FAMÍLIA
Conteúdo 100% seguro, educativo e divertido. Perfeito para crianças e adultos assistirem juntos. Sem violência, sem conteúdos inadequados.

🌍 IDIOMAS / LANGUAGES
Narração em português do Brasil. Ative as legendas automáticas do YouTube para assistir em seu idioma:
• English: Enable auto-captions
• Español: Active los subtítulos automáticos
• Français: Activez les sous-titres automatiques
• Deutsch: Automatische Untertitel aktivieren
• Italiano: Attiva i sottotitoli automatici
• 日本語: 自動字幕を有効にする

🔔 INSCREVA-SE
Inscreva-se no canal para não perder nenhuma aventura da Frida e da Luna!

📱 SIGA NOSSAS REDES SOCIAIS
Acompanhe mais conteúdos da Frida e da Luna.

#FridaELuna #DesenhoAnimado #DesenhoInfantil #Cachorro #Cachorrinha #Buldogue #Salsicha #Dachshund #Animação #AventuraInfantil #Família #Crianças #ConteúdoInfantil #CanalInfantil #DesenhoAnimadoParaCrianças #HistóriaInfantil #CartoonDog #KidsAnimation #FamilyAnimation #BulldogCartoon #DogCartoon #DesenhoParaCrianças #VídeoInfantil #ConteúdoParaCrianças"""
    return desc

def build_tags():
    """Constrói tags em português para o YouTube (apenas caracteres simples, sem acentos)."""
    tags = [
        "frida e luna", "desenho animado", "desenho animado para criancas",
        "desenho infantil", "cachorro", "cachorrinha", "buldogue", "salsicha",
        "dachshund", "animacao", "animacao infantil", "aventura infantil",
        "familia", "criancas", "conteudo infantil", "canal infantil",
        "video para criancas", "desenho do cachorro", "historia infantil",
        "desenho animado portugues", "desenho animado brasil", "cartoon dog",
        "cartoon for kids", "kids animation", "family animation",
        "bulldog cartoon", "dog cartoon", "historia para criancas",
        "desenho animado cachorro", "desenho para criancas", "video para criancas"
    ]
    return ",".join(tags)

def main():
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    if not PROJECTS.exists():
        print(f"ERRO: pasta de projetos não encontrada: {PROJECTS}")
        return 1

    published = 0
    failed = 0

    for v in VIDEOS:
        video_path = PROJECTS / v["slug"] / v["video"]
        thumb_path = PROJECTS / v["slug"] / v["thumb"]
        title = v["title"]
        description = build_description(title, v["prompt"])
        tags = build_tags()

        if not video_path.exists():
            print(f"❌ VÍDEO NÃO ENCONTRADO: {video_path}")
            failed += 1
            continue

        thumb_str = str(thumb_path) if thumb_path.exists() else ""
        if not thumb_path.exists():
            print(f"⚠️  THUMBNAIL NÃO ENCONTRADA: {thumb_path} (sem thumbnail)")

        print(f"\n{'='*60}")
        print(f"📹 Publicando: {v['slug']}")
        print(f"   Título: {title}")
        print(f"   Thumbnail: {thumb_path.name if thumb_path.exists() else 'NENHUMA'}")
        print(f"{'='*60}")

        cmd = [
            sys.executable, str(HERE / "youtube_upload.py"),
            "--video", str(video_path),
            "--title", title,
            "--description", description,
            "--tags", tags,
            "--category", "24",
            "--privacy", "unlisted",
            "--made-for-kids",
            "--client-secret", str(HERE / "client_secret.json"),
            "--token", str(HERE / "youtube_token.json"),
        ]
        if thumb_str:
            cmd += ["--thumbnail", thumb_str]

        print(f"\n⏳ Enviando para o YouTube...")
        import subprocess
        r = subprocess.run(cmd, cwd=str(HERE))
        if r.returncode == 0:
            print(f"✅ PUBLICADO COM SUCESSO: {v['slug']}")
            published += 1
        else:
            print(f"❌ FALHA: {v['slug']} (código {r.returncode})")
            failed += 1

    print(f"\n{'='*60}")
    print(f"📊 RESUMO: {published} publicado(s), {failed} falha(s), {len(VIDEOS)} total")
    print(f"{'='*60}")
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
