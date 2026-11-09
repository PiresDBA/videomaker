# -*- coding: utf-8 -*-
"""
Gera a narracao com Gemini TTS (Google AI Studio) em blocos de secoes.

- Le o texto de artifacts/script.json
- Aplica as piadas/risadas e exclamacoes definidas em config.json -> "tts"
- Divide as secoes em blocos de "tts.chunk_size" e faz 1 requisicao por bloco
- Grava assets/audio/narration_chunks/cN.wav + cN.txt + chunks.json

A chave da API vem da variavel de ambiente indicada em config.tts.key_env
(padrao GOOGLE_TTS_API_KEY no .env da raiz do Videomaker).

Uso:
  python scripts/gen_narration_gemini.py
  python scripts/gen_narration_gemini.py --voice Achernar --model gemini-3.8-flash-tts
  python scripts/gen_narration_gemini.py --only c2 --force

Depois rode: python scripts/align_narration.py
"""
import argparse
import base64
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from env_keys import load_env_key

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def section_text(sec, tts):
    t = sec["text"].strip()
    pair = tts.get("laughs", {}).get(sec["id"])
    if pair and pair[0] in t:
        t = t.replace(pair[0], pair[1], 1)
    for a, b in tts.get("exclamations", []):
        if a in t:
            t = t.replace(a, b, 1)
    return t


def build_chunks(sections, size):
    return [sections[i:i + size] for i in range(0, len(sections), size)]


def synthesize(key, model, voice, text, timeout=900):
    url = ("https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s"
           % (model, key))
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--chunk-size", type=int, default=None)
    ap.add_argument("--only", default=None, help="gera apenas este bloco (c1, c2, ...)")
    ap.add_argument("--force", action="store_true", help="regenera mesmo se o wav ja existe")
    args = ap.parse_args()

    cfg = load_json(HERE / "config.json")
    tts = cfg.get("tts", {})
    model = args.model or tts.get("model", "gemini-3.8-flash-tts")
    voice = args.voice or tts.get("voice", "Leda")
    size = args.chunk_size or int(tts.get("chunk_size", 4))
    key_env = tts.get("key_env", "GOOGLE_TTS_API_KEY")

    key = load_env_key(key_env) or load_env_key("GOOGLE_API_KEY")
    if not key:
        raise SystemExit("chave nao encontrada: defina %s no .env" % key_env)

    script = load_json(PROJECT / "artifacts" / "script.json")
    out = PROJECT / "assets" / "audio" / "narration_chunks"
    out.mkdir(parents=True, exist_ok=True)

    groups = build_chunks(script["sections"], size)
    if tts.get("chunks"):
        by_id = {s["id"]: s for s in script["sections"]}
        groups = [[by_id[sid] for sid in grp] for grp in tts["chunks"]]
    meta = []
    for n, secs in enumerate(groups, start=1):
        name = "c%d" % n
        meta.append({"chunk": name, "ids": [s["id"] for s in secs]})
        wav = out / ("%s.wav" % name)
        text = "\n\n".join(section_text(s, tts) for s in secs)
        (out / ("%s.txt" % name)).write_text(text, encoding="utf-8")
        if args.only and args.only != name:
            continue
        if wav.exists() and wav.stat().st_size > 1000 and not args.force:
            print("%s: ja existe, pulando" % name)
            continue
        for attempt in range(3):
            try:
                raw, finish = synthesize(key, model, voice, text)
                wav.write_bytes(raw)
                print("%s: OK %.2f MB (%s) voz=%s modelo=%s"
                      % (name, len(raw) / 1e6, finish, voice, model))
                break
            except urllib.error.HTTPError as e:
                print("%s: HTTP %s %s" % (name, e.code, e.read().decode()[:160].replace("\n", " ")))
                break
            except Exception as e:
                print("%s: erro %s (tentativa %d)" % (name, str(e)[:80], attempt + 1))
                time.sleep(10)
        time.sleep(4)

    (out / "chunks.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("blocos:", ", ".join(m["chunk"] for m in meta))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
