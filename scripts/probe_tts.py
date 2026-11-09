# -*- coding: utf-8 -*-
"""
Diagnostico do Gemini TTS: testa a chave, lista modelos de voz e cota,
e gera uma previa de voz em WAV.

Usa a chave de config.json -> tts.key_env (padrao GOOGLE_TTS_API_KEY no .env
da raiz do Videomaker).

Uso:
  python scripts/probe_tts.py --list
  python scripts/probe_tts.py --test
  python scripts/probe_tts.py --voice Achernar --text "Teste de voz." --out preview/Achernar.wav
"""
import argparse
import base64
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

from env_keys import load_env_key

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
API = "https://generativelanguage.googleapis.com/v1beta"

TTS_MODELS = [
    "gemini-3.8-flash-tts",
    "gemini-3.8-flash-lite-tts",
    "gemini-3.1-flash-tts-preview",
    "gemini-2.5-flash-preview-tts",
    "gemini-2.5-pro-preview-tts",
]

VOICES = ["Leda", "Kore", "Despina", "Erinome", "Laomedeia", "Achernar",
          "Zephyr", "Autonoe", "Puck", "Charon", "Fenrir", "Aoede"]


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def call(key, model, voice, text, timeout=180):
    url = "%s/models/%s:generateContent?key=%s" % (API, model, key)
    body = {"contents": [{"parts": [{"text": text}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {
                                     "prebuiltVoiceConfig": {"voiceName": voice}}}}}
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req, timeout=timeout))
    cand = data["candidates"][0]
    return base64.b64decode(cand["content"]["parts"][0]["inlineData"]["data"]), cand.get("finishReason")


def main():
    cfg = load_json(HERE / "config.json")
    tts = cfg.get("tts", {})
    key_env = tts.get("key_env", "GOOGLE_TTS_API_KEY")
    key = load_env_key(key_env) or load_env_key("GOOGLE_API_KEY")

    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="lista modelos e vozes conhecidos")
    ap.add_argument("--test", action="store_true", help="faz uma requisicao curta em cada modelo")
    ap.add_argument("--model", default=tts.get("model", "gemini-3.8-flash-tts"))
    ap.add_argument("--voice", default=tts.get("voice", "Leda"))
    ap.add_argument("--text", default="Ola! Esta e uma previa da voz.")
    ap.add_argument("--out", default=None, help="caminho do WAV de saida")
    args = ap.parse_args()

    if args.list:
        print("modelos TTS conhecidos:")
        for m in TTS_MODELS:
            print("  -", m)
        print("vozes predefinidas testadas:")
        print("  ", ", ".join(VOICES))
        print("modelo atual:", tts.get("model"), "| voz atual:", tts.get("voice"))
        return 0

    if not key:
        print("ERRO: chave nao encontrada (%s no .env)" % key_env)
        return 2

    if args.test:
        for model in TTS_MODELS:
            try:
                raw, finish = call(key, model, args.voice, "Ola.")
                print("%-34s OK   %6d bytes  finish=%s" % (model, len(raw), finish))
            except urllib.error.HTTPError as e:
                msg = e.read().decode("utf-8", "ignore")
                if e.code == 429:
                    print("%-34s 429  cota esgotada/indisponivel" % model)
                else:
                    print("%-34s %s  %s" % (model, e.code, msg[:100].replace("\n", " ")))
            except Exception as e:
                print("%-34s ERRO %s" % (model, str(e)[:80]))
        return 0

    raw, finish = call(key, args.model, args.voice, args.text)
    out = Path(args.out) if args.out else (PROJECT / "assets" / "audio" / "preview" / ("%s.wav" % args.voice))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw)
    print("ok: %s (%d bytes, finish=%s, modelo=%s, voz=%s)"
          % (out, len(raw), finish, args.model, args.voice))
    return 0


if __name__ == "__main__":
    sys.exit(main())
