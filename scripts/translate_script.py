# -*- coding: utf-8 -*-
"""
Traduz as secoes do script.json para outros idiomas usando o Gemini WEB
(kind=text, Chrome CDP) — mesma infraestrutura da fase script.

Uso:
  python scripts/translate_script.py --script artifacts/script.json --lang en,es --out-dir artifacts
  python scripts/translate_script.py --script projects/<slug>/artifacts/script.json --lang en --out-dir projects/<slug>/artifacts

Saida:
  artifacts/script_en.json
  artifacts/script_es.json

Estrutura preservada: somente o campo "text" de cada secao e o "title" sao traduzidos.
IDs, labels e delivery_cues ficam inalterados.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GEMINI_FETCH = HERE / "gemini_fetch.py"

LANG_NAMES = {
    "pt": "portugues do Brasil",
    "en": "ingles",
    "es": "espanhol",
}

# Risadas escritas ("Hahaha!", "ha ha ha", "HAHAH", "rsrsrs", "kkkkk") 
# sao removidas antes de traduzir para evitar que o Gemini as traduza
# ou que o Edge-TTS as leia de forma mecanica.
LAUGH_RE = re.compile(r"(?i)\b(?:ha[\s\-!]*|he[\s\-!]*|hi[\s\-!]*|ho[\s\-!]*|rs[\s\-!]*|kk[\s\-!]*){2,}[!\.,]?\s*")


def remover_risadas(text: str) -> str:
    """Remove risadas escritas do texto para evitar leitura mecanica pelo Edge-TTS."""
    return LAUGH_RE.sub(" ", text).strip()

# Secoes do contrato que devem soar naturais em cada idioma (nao traduzidas palavra a palavra,
# mas adaptadas para nao soar robota). Se o Gemini nao retornar traducao boa, usamos esses fallback.
CONTRACT_FALLBACKS = {
    "en": {
        "s_intro": "Did you know dogs can have amazing adventures too?",
        "s0": "Hi friends! Welcome to our channel! Today we are going to talk about {topic}.",
        "s_final": "And that's the end of our story today! This is the end of our adventure!",
        "s_outro": "Thank you for watching! A big kiss on your heart and stay with us! Follow our next videos! Leave your like, subscribe to the channel and tell your little friends!",
    },
    "es": {
        "s_intro": "¿Sabías que los perros también pueden vivir aventuras increíbles?",
        "s0": "¡Hola, amigos! Bienvenidos a nuestro canal. Hoy vamos a hablar de {topic}.",
        "s_final": "¡Y así termina nuestra historia de hoy! Este es el final de nuestra aventura.",
        "s_outro": "¡Gracias por ver! Un gran beso en tu corazón y quédate con nosotros. ¡Acompáñenos en nuestros próximos videos! Deja tu like, suscríbete al canal y cuéntaselo a tus amiguitos.",
    },
}


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_json(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def translate_text(text, target_lang, topic, out_dir, name, wait_s=120):
    """Traduz um unico texto via Gemini WEB (kind=text)."""
    # Remove risadas escritas antes de traduzir (evita leitura mecanica)
    text = remover_risadas(text)
    prompt = (
        f"Traduza o seguinte texto para o {LANG_NAMES[target_lang]} "
        f"(Brasil/natural, tom infantil e divertido). "
        f"Contexto: video infantil sobre '{topic}' com os cachorros Frida e Luna. "
        f"Mantenha nomes proprios (Frida, Luna, Luninha, Fridoca) e apelidos inalterados. "
        f"Nao adicione explicacoes, nao coloque aspas, nao diga 'aqui esta a traducao'. "
        f"Responda apenas com o texto traduzido, nada mais.\n\n"
        f"TEXTO: {text}"
    )
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cmd = [
            sys.executable, str(GEMINI_FETCH),
            "--kind", "text",
            "--prompt", prompt,
            "--name", name,
            "--out-dir", str(td),
            "--wait", str(wait_s),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            return None
        # gemini_fetch grava .md no out_dir
        md_files = list(td.glob("*.md"))
        if not md_files:
            return None
        trad = md_files[0].read_text(encoding="utf-8").strip()
        # Limpa possiveis aspas ou marcadores ao redor
        trad = trad.strip().strip('"').strip("'").strip()
        return trad if trad else None


def translate_script(script_path, languages, out_dir, topic, wait_s=120):
    script = load_json(script_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sections = script.get("sections", [])
    title = script.get("title", "") or ""

    for lang in languages:
        if lang == "pt":
            continue
        print(f"== Traduzindo roteiro para {lang.upper()}...", flush=True)
        translated = {
            "title": translate_text(title, lang, topic, out_dir, f"title_{lang}", wait_s)
            or title,
            "sections": [],
        }
        for s in sections:
            sid = s.get("id", "")
            texto = s.get("text", "").strip()
            if not texto:
                translated["sections"].append({**s, "text": ""})
                continue
            # Secoes do contrato: tenta traduzir; se falhar, usa fallback adaptado.
            trad = translate_text(texto, lang, topic, out_dir, f"{sid}_{lang}", wait_s)
            if not trad:
                fb = CONTRACT_FALLBACKS.get(lang, {}).get(sid, "")
                if fb:
                    trad = fb.format(topic=topic)
                else:
                    trad = texto  # fallback ultimo recurso: mantem o original
            translated["sections"].append({
                **s,
                "text": trad,
            })
            time.sleep(2)  # respeita o Gemini Web (conta gratuita)
        out_path = out_dir / f"script_{lang}.json"
        save_json(out_path, translated)
        print(f"   salvo: {out_path} ({len(translated['sections'])} secoes)", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", required=True, help="caminho do artifacts/script.json")
    ap.add_argument("--lang", required=True, help="idiomas separados por virgula (ex: en,es)")
    ap.add_argument("--out-dir", default=None, help="pasta de saida (padrao: mesma do script)")
    ap.add_argument("--topic", default=None, help="topico/assunto do video (para contexto da traducao)")
    ap.add_argument("--wait", type=int, default=120, help="espera por resposta do Gemini Web (s)")
    args = ap.parse_args()

    script_path = Path(args.script)
    out_dir = Path(args.out_dir) if args.out_dir else script_path.parent
    languages = [l.strip().lower() for l in args.lang.split(",") if l.strip()]
    topic = args.topic or script_path.parent.name

    translate_script(script_path, languages, out_dir, topic, args.wait)
    return 0


if __name__ == "__main__":
    sys.exit(main())
