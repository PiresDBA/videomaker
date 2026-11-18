# -*- coding: utf-8 -*-
"""publicar_3_idiomas.py - sobe PT/EN/ES para os respectivos canais.

Por padrao sobe como PRIVATE para conferencia. Depois de aprovado, rodar com
--public para tornar publicos (ou usar --publish-at para agendar).
"""
import argparse, subprocess, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
PY = sys.executable
UPLOAD = HERE / "youtube_upload.py"
OUT = Path(r"C:\videomaker\projects\a-caminha-nova-que-ninguem-quer-usar\output")
SLUG = "a-caminha-nova-que-ninguem-quer-usar"

CFG = {
    "pt": {
        "video": OUT / f"{SLUG}_pt.mp4",
        "title": "A Incrível Batalha da Caminha Nova que Ninguém Quer Usar!",
        "desc": ("A Frida e a Luna descobrem uma caminha nova e fofinha que ninguém "
                 "quer usar! Uma aventura engraçada para crianças com muita risada, "
                 "musiquinha e uma lição sobre não julgar o que é novo. "
                 "Gostou? Deixe seu like e se inscreva no canal!"),
        "tags": "frida,luna,cachorro,animacao,infantil,engracado,caminha,desenho",
        "lang": "pt-BR", "audio": "pt-BR",
    },
    "en": {
        "video": OUT / f"{SLUG}_en.mp4",
        "title": "The Ultimate Battle of the Brand New Dog Bed That Nobody Wants to Use!",
        "desc": ("Frida and Luna discover a brand new cozy dog bed that nobody wants "
                 "to use! A funny adventure for kids with lots of laughs, music, and a "
                 "lesson about not judging something new. Like and subscribe!"),
        "tags": "frida,luna,dog,animation,kids,funny,dogbed,cartoon",
        "lang": "en-US", "audio": "en-US",
    },
    "es": {
        "video": OUT / f"{SLUG}_es.mp4",
        "title": "¡La gran batalla de la camita nueva que nadie quiere usar!",
        "desc": ("¡Frida y Luna descubren una camita nueva y acogedora que nadie quiere "
                 "usar! Una aventura divertida para niños con muchas risas, música y "
                 "una lección sobre no juzgar lo nuevo. ¡Dale like y suscríbete!"),
        "tags": "frida,luna,perro,animacion,infantil,gracioso,camita,dibujo",
        "lang": "es-ES", "audio": "es-ES",
    },
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--public", action="store_true", help="torna publico (padrao: private)")
    ap.add_argument("--only", default="", help="so um idioma (pt/en/es)")
    args = ap.parse_args()
    privacy = "public" if args.public else "private"
    for lang, c in CFG.items():
        if args.only and lang != args.only:
            continue
        if not c["video"].exists():
            print(f"FALTA video {lang}: {c['video']}"); continue
        cmd = [PY, str(UPLOAD),
               "--video", str(c["video"]),
               "--title", c["title"],
               "--description", c["desc"],
               "--tags", c["tags"],
               "--privacy", privacy,
               "--default-language", c["lang"],
               "--default-audio-language", c["audio"],
               "--client-secret", str(HERE / f"client_secret_{lang}.json"),
               "--token", str(HERE / f"youtube_token_{lang}.json"),
               "--made-for-kids"]
        print(f"\n{'='*60}\nUPLOAD {lang.upper()} ({privacy})\n{'='*60}", flush=True)
        r = subprocess.run(cmd)
        print(f"=== {lang} rc={r.returncode} ===", flush=True)


if __name__ == "__main__":
    main()
