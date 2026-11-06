# -*- coding: utf-8 -*-
"""
Atualiza metadados dos 2 videos no YouTube com descricoes completas, tags e miniaturas.
Execute: & .\.venv\Scripts\python.exe scripts/youtube_update_full.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))
from youtube_update import get_service, update_video

HERE = Path(__file__).resolve().parent  # C:\videomaker\scripts
PROJECT_ROOT = HERE.parent  # C:\videomaker

DESC1 = """🐶 Frida e Luna Descobrem o Espelho - Desenho Animado para Crianças

🎬 SINOPSE
Frida, a buldogue inglesa preguiçosa e gulosa, e Luna, a salsicha curiosa e chefona, vivem uma grande aventura quando descobrem um espelho mágico na sala de casa. O que elas veem no reflexo vai surpreender você!

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

#FridaELuna #DesenhoAnimado #DesenhoInfantil #Cachorro #Cachorrinha #Buldogue #Salsicha #Dachshund #Animação #EspelhoMagico #AventuraInfantil #Família #Crianças #ConteúdoInfantil #CanalInfantil #DesenhoAnimadoParaCrianças #HistóriaInfantil #CartoonDog #KidsAnimation #FamilyAnimation #BulldogCartoon #DogCartoon"""

TAGS1 = "frida e luna,desenho animado,desenho infantil,cachorro,cachorrinha,buldogue,salsicha,animacao,espelho magico,aventura infantil,familia,criancas,conteudo infantil,canal infantil,cartoon dog,kids animation,family animation,bulldog cartoon,dog cartoon,perro dibujito,dibujo animado niños,historia para niños,animacion infantil"

DESC2 = """🐶 Luna e Frida Descobrem o Espelho da Casa - Desenho Animado para Crianças

🎬 SINOPSE
Luna, a salsicha curiosa e chefona, e Frida, a buldogue inglesa preguiçosa e gulosa, descobrem um espelho antigo na casa. Quando olham no reflexo, veem algo inesperado e embarcam em uma aventura mágica cheia de surpresas!

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

#LunaEFrida #DesenhoAnimado #DesenhoInfantil #Cachorro #Cachorrinha #Buldogue #Salsicha #Dachshund #Animação #EspelhoDaCasa #AventuraMagica #Família #Crianças #ConteúdoInfantil #CanalInfantil #DesenhoAnimadoParaCrianças #HistóriaInfantil #CartoonDog #KidsAnimation #FamilyAnimation #BulldogCartoon #DogCartoon"""

TAGS2 = "luna e frida,desenho animado,desenho infantil,cachorro,cachorrinha,buldogue,salsicha,animacao,espelho da casa,aventura magica,familia,criancas,conteudo infantil,canal infantil,cartoon dog,kids animation,family animation,bulldog cartoon,dog cartoon,perro dibujito,dibujo animado niños,historia para niños,animacion infantil"

if __name__ == "__main__":
    service = get_service(HERE / "client_secret.json", HERE / "youtube_token.json")

    print("=== Atualizando video 1: Frida e Luna Descobrem o Espelho ===")
    update_video(service, "3vqti6cJ3EE",
                 "Frida e Luna Descobrem o Espelho - Desenho Animado para Crianças",
                 DESC1, TAGS1.split(","), "24",
                 HERE.parent / "thumbnails" / "frida-luna-clean.jpg")

    print("\n=== Atualizando video 2: Luna e Frida Descobrem o Espelho da Casa ===")
    update_video(service, "GXeRo92lOW8",
                 "Luna e Frida Descobrem o Espelho da Casa - Desenho Animado para Crianças",
                 DESC2, TAGS2.split(","), "24",
                 HERE.parent / "thumbnails" / "luna-frida-clean.jpg")

    print("\nConcluido! Ambos os videos atualizados.")
