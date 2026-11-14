# -*- coding: utf-8 -*-
"""
Gera scripts/scenes/sN.html para cada secao do roteiro.

Comportamento padrao: NENHUM texto sobre a imagem (apenas naracao), exceto a
secao de APRESENTACAO do canal (s0), que ganha um overlay infantil com o nome
da historia animado (bounce/pop via GSAP -> build_composition.py).

Os chips de palavras-chave ficam DESATIVADOS por padrao (poluiam a tela).
Use --chips apenas se quiser reativar (chips normalmente em secoes normais,
a s0 continua com o overlay de titulo).

Uso:
  python scripts/generate_scene_htmls.py --script artifacts/script.json \
      --scenes scripts/scenes.json --out-dir scripts/scenes
"""
import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def clean(t):
    t = t.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", t).strip()


def first_sentence(t):
    parts = re.split(r"(?<=[.!?])\s+", clean(t))
    return parts[0] if parts else clean(t)[:90]


def chips_from(text, n=4):
    words = re.findall(r"[A-Za-z\u00c0-\u00ff]+", text)
    seen, out = set(), []
    for w in words:
        wl = w.lower()
        if len(wl) < 4 or wl in seen:
            continue
        seen.add(wl)
        out.append(w.upper())
        if len(out) >= n:
            break
    return out


def esc(t):
    return (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def is_intro_section(s):
    """True apenas para a secao de apresentacao do canal (s0)."""
    sid = (s.get("id", "") or "").lower()
    return sid == "s0"


# Linha de abertura do overlay s0, no idioma do video (regra: os textos de
# tela seguem o idioma do video; o padrao pt preserva o comportamento antigo).
INTRO_BODY = {
    "pt": "Uma aventura nova com a Frida e a Luna!",
    "en": "A brand-new adventure with Frida and Luna!",
    "es": "Una nueva aventura con Frida y Luna!",
}

# Badge do canal no idioma do video. "Frida e Luna" e PT: em EN/ES precisa
# virar "Frida and Luna"/"Frida y Luna" (regra: nenhum texto PT no video).
CHANNEL_BADGE = {
    "pt": "Frida e Luna",
    "en": "Frida and Luna",
    "es": "Frida y Luna",
}


def render_intro_overlay(s, story_title="", lang="pt"):
    """Abertura infantil: badge do canal + titulo da historia animado.
    O texto do overlay NAO e narracao — e apenas o titulo curto na tela
    enquanto o narrador cumprimenta a audiencia."""
    title = s.get("overlay_title") or story_title or ""
    t = esc(title)
    return (
        '<div class="block tc" style="top:30%;max-width:1400px">'
        '<div class="badge" data-anim="pop" data-delay="0.2">'
        + CHANNEL_BADGE.get((lang or "pt").lower(), CHANNEL_BADGE["pt"])
        + "</div>"
        '<h2 class="h-xl" data-anim="bounce" data-delay="0.8" style="margin-top:18px">'
        + t
        + "</h2>"
        '<div class="body" data-anim="pop" data-delay="1.6" style="margin-top:16px">'
        + INTRO_BODY.get((lang or "pt").lower(), INTRO_BODY["pt"])
        + "</div>"
        "</div>"
    )


def render_section(s, with_chips=False, story_title="", lang="pt"):
    """Retorna HTML vazio (nenhum texto na tela), EXCETO a secao de
    apresentacao (s0), que ganha o titulo da historia animado."""
    if is_intro_section(s):
        return render_intro_overlay(s, story_title, lang)
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default=str(PROJECT / "artifacts" / "script.json"))
    ap.add_argument("--scenes", default=str(HERE / "scenes.json"))
    ap.add_argument("--out-dir", default=str(HERE / "scenes"))
    ap.add_argument("--lang", default="pt",
                    help="idioma dos textos de tela (pt,en,es); padrao pt")
    ap.add_argument("--chips", action="store_true",
                    help="inclui os 4 chips de palavras-chave no canto direito (desativado por padrao)")
    args = ap.parse_args()

    script = load_json(args.script)
    sections = script.get("sections", [])
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    for i, s in enumerate(sections):
        sid = s.get("id", "s%d" % i)
        html = render_section(s, with_chips=args.chips, story_title=script.get("title", ""),
                              lang=getattr(args, "lang", "pt"))
        (out / ("%s.html" % sid)).write_text(html, encoding="utf-8")
        print("wrote", out / ("%s.html" % sid))

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
