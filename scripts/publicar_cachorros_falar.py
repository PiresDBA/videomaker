# -*- coding: utf-8 -*-
"""publicar_cachorros_falar.py - Publica PT/EN/ES do projeto
'e-se-os-cachorros-pudessem-falar-por-um-dia' nos canais respectivos.

Por padrao sobe como PRIVATE (conferencia). Use --public para tornar publico.
Use --only pt|en|es para publicar um idioma por vez (ordem pedida: PT, EN, ES).
"""
import argparse, subprocess, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
PY = sys.executable
UPLOAD = HERE / "youtube_upload.py"
OUT = Path(r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia\output")
SLUG = "e-se-os-cachorros-pudessem-falar-por-um-dia"

CFG = {
    "pt": {
        "title": "E se os cachorros pudessem falar por um dia? | Frida e Luna",
        "desc": ("E se os cachorros pudessem falar por um dia? A Frida e a Luna "
                 "descobrem que podem conversar com todo mundo na pracinha! "
                 "Uma aventura divertida para crianças com ossinhos voadores, "
                 "borboletas e uma lição sobre amizade. "
                 "Gostou? Deixe seu like e se inscreva no canal!"),
        "tags": "frida,luna,cachorro,animacao,infantil,engracado,cachorros falando,desenho",
        "lang": "pt-BR", "audio": "pt-BR",
    },
    "en": {
        "title": "What If Dogs Could Talk for a Day? | Frida and Luna",
        "desc": ("What if dogs could talk for a day? Frida and Luna discover they "
                 "can talk to everyone at the park! A fun adventure for kids with "
                 "flying bones, butterflies, and a lesson about friendship. "
                 "Like and subscribe!"),
        "tags": "frida,luna,dog,animation,kids,funny,talking dogs,cartoon",
        "lang": "en-US", "audio": "en-US",
    },
    "es": {
        "title": "¿Y si los perros pudieran hablar por un día? | Frida y Luna",
        "desc": ("¿Y si los perros pudieran hablar por un día? ¡Frida y Luna "
                 "descubren que pueden hablar con todos en la plaza! Una aventura "
                 "divertida para niños con huesitos voladores, mariposas y una "
                 "lección sobre la amistad. ¡Dale like y suscríbete!"),
        "tags": "frida,luna,perro,animacion,infantil,gracioso,perros hablando,dibujo",
        "lang": "es-ES", "audio": "es-ES",
    },
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--public", action="store_true", help="torna publico (padrao: private)")
    ap.add_argument("--only", default="", help="so um idioma (pt/en/es)")
    args = ap.parse_args()
    privacy = "public" if args.public else "private"
    ordem = [args.only] if args.only else ["pt", "en", "es"]
    for lang in ordem:
        c = CFG[lang]
        video = OUT / f"{SLUG}_{lang}.mp4"
        if not video.exists():
            print(f"FALTA video {lang}: {video}")
            continue
        cmd = [PY, str(UPLOAD),
               "--video", str(video),
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
