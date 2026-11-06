# -*- coding: utf-8 -*-
"""
Publicacao em lote de todos os vídeos MP4 finais no YouTube.
Conteúdo infantil (made for kids), português do Brasil, categoria Entretenimento.

Uso:
  python scripts/youtube_batch_publish.py
"""
import json
import sys
from pathlib import Path

# Força UTF-8 no stdout para evitar erro de codificação no Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROJECTS = ROOT / "projects"
THUMBNAILS = ROOT / "thumbnails"


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def get_final_videos(project_dir):
    """Retorna a lista de vídeos finais (MP4) na pasta output do projeto."""
    output_dir = project_dir / "output"
    if not output_dir.exists():
        return []
    videos = []
    for f in sorted(output_dir.iterdir()):
        if f.suffix.lower() != ".mp4":
            continue
        name_lower = f.name.lower()
        # Pular BGM e versões alternativas (sem chips, renders antigos, etc.)
        if "bgm" in name_lower:
            continue
        if "sem-chips" in name_lower or "old-v2" in name_lower:
            continue
        if "renders" in str(f):
            continue
        videos.append(f)
    return videos


def get_title_and_prompt(project_dir):
    """Lê o título e prompt do script.json do projeto."""
    script_file = project_dir / "artifacts" / "script.json"
    title = project_dir.name.replace("-", " ").title()
    prompt = ""
    if script_file.exists():
        try:
            s = load_json(script_file)
            title = s.get("title", title)
            prompt = s.get("prompt", "")
        except Exception:
            pass
    return title, prompt


def find_thumbnail(project_dir):
    """Encontra uma thumbnail para o projeto."""
    # Primeiro tenta thumbnails geradas especificamente
    slug = project_dir.name
    for thumb_name in [f"{slug}-clean.jpg", f"{slug}-thumb.jpg"]:
        t = THUMBNAILS / thumb_name
        if t.exists():
            return str(t)
    # Senão tenta qualquer thumbnail disponível
    if THUMBNAILS.exists():
        for t in THUMBNAILS.iterdir():
            if t.suffix.lower() in (".jpg", ".jpeg", ".png"):
                return str(t)
    # Senão tenta a primeira imagem de cena do projeto
    images_dir = project_dir / "assets" / "images" / "gemini" / "scenes"
    if images_dir.exists():
        for img in images_dir.iterdir():
            if img.suffix.lower() in (".jpg", ".jpeg", ".png"):
                return str(img)
    return None


def build_description(title, prompt):
    """Constrói uma descrição completa em português do Brasil para público infantil."""
    desc = f"""🐶 {title} - Desenho Animado para Crianças

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


def build_tags(title):
    """Constrói tags em português para o YouTube (max 30 chars cada, sem especiais)."""
    base_tags = [
        "frida e luna", "desenho animado", "desenho infantil",
        "cachorro", "cachorrinha", "buldogue", "salsicha",
        "animacao", "aventura infantil", "familia", "criancas",
        "conteudo infantil", "canal infantil", "video para criancas",
        "desenho do cachorro", "historia infantil", "cartoon dog",
        "kids animation", "family animation", "bulldog cartoon",
        "dog cartoon", "desenho para criancas"
    ]
    return ",".join(base_tags)


def main():
    if not PROJECTS.exists():
        print(f"ERRO: pasta de projetos não encontrada: {PROJECTS}")
        return 1

    projects = [p for p in PROJECTS.iterdir() if p.is_dir()]
    print(f"Encontrados {len(projects)} projeto(s) em {PROJECTS}\n")

    published = 0
    skipped = 0

    for pdir in sorted(projects):
        videos = get_final_videos(pdir)
        if not videos:
            print(f"⏭️  {pdir.name}: sem vídeos finais em output/")
            skipped += 1
            continue

        title, prompt = get_title_and_prompt(pdir)
        description = build_description(title, prompt)
        tags = build_tags(title)
        thumbnail = find_thumbnail(pdir)

        for video in videos:
            print(f"\n{'='*60}")
            print(f"📹 Publicando: {video.name}")
            print(f"   Projeto: {pdir.name}")
            print(f"   Título: {title}")
            print(f"   Thumbnail: {thumbnail or '(não encontrada)'}")
            print(f"{'='*60}")

            cmd = [
                sys.executable, str(HERE / "youtube_upload.py"),
                "--video", str(video),
                "--title", title,
                "--description", description,
                "--tags", tags,
                "--category", "24",
                "--privacy", "unlisted",
                "--made-for-kids",
                "--client-secret", str(HERE / "client_secret.json"),
                "--token", str(HERE / "youtube_token.json"),
            ]
            if thumbnail:
                cmd += ["--thumbnail", thumbnail]

            print(f"\n⏳ Enviando para o YouTube...")
            result = __import__("subprocess").run(cmd, cwd=str(HERE))
            if result.returncode == 0:
                print(f"✅ PUBLICADO COM SUCESSO: {video.name}")
                published += 1
            else:
                print(f"❌ FALHA ao publicar: {video.name} (código {result.returncode})")

    print(f"\n{'='*60}")
    print(f"📊 RESUMO: {published} vídeo(s) publicado(s), {skipped} projeto(s) sem vídeo")
    print(f"{'='*60}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
