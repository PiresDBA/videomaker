# -*- coding: utf-8 -*-
"""
Descobre e testa as vozes disponíveis do Gemini TTS com sua(s) chave(s).

Gera um audio curto para cada voz que funcionar, em
assets/audio/voice_test/<voz>.wav, para voce ouvir e escolher.

Le as chaves de GOOGLE_TTS_API_KEY / GOOGLE_TTS_API_KEY_1..N (ambiente ou .env,
gitignorado). Nao grava chaves em lugar nenhum.

Uso:
  python scripts/check_tts_voices.py
  python scripts/check_tts_voices.py --model gemini-3.8-flash-lite-tts --texto "Ola, eu sou a voz X"
  python scripts/check_tts_voices.py --vozes Achernar,Leda,Kore,Zephyr,Puck
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

try:
    from env_keys import load_env_key
except Exception:
    load_env_key = None

API = "https://generativelanguage.googleapis.com/v1beta"

# Vozes conhecidas/candidatas do Gemini TTS (prebuiltVoiceConfig)
DEFAULT_VOZES = [
    "Achernar", "Leda", "Kore", "Zephyr", "Puck", "Aoede", "Fenrir", "Orus",
    "Charon", "Nemausa", "Enceladus", "Callisto", "Io", "Europa",
    "Ganymede", "Triton", "Umbriel", "Titania", "Oberon",
]


def collect_keys():
    keys, seen = [], set()

    def add(key):
        if not key or key in seen:
            return
        seen.add(key)
        keys.append(key)

    add(os.environ.get("GOOGLE_TTS_API_KEY", ""))
    if load_env_key:
        try:
            add(load_env_key("GOOGLE_TTS_API_KEY") or "")
        except Exception:
            pass

    i = 1
    while True:
        val = os.environ.get("GOOGLE_TTS_API_KEY_%d" % i, "")
        if not val and load_env_key:
            try:
                val = load_env_key("GOOGLE_TTS_API_KEY_%d" % i) or ""
            except Exception:
                val = ""
        if not val:
            break
        add(val)
        i += 1
    return keys


def mask(key):
    if not key:
        return "(vazia)"
    return key[:4] + "..." + key[-4:] if len(key) > 8 else key[:2] + "..."


def test_voice(api_key, model, voice, texto, timeout=30):
    """
    Tenta gerar audio com a voz.
    Retorna (ok, audio_bytes ou None, erro ou "").
    """
    url = "%s/models/%s:generateContent?key=%s" % (API, model, api_key)
    body = {
        "contents": [{"parts": [{"text": texto}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {
                "prebuiltVoiceConfig": {"voiceName": voice}}}},
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        data = json.load(urllib.request.urlopen(req, timeout=timeout))
        cand = data["candidates"][0]
        part = cand["content"]["parts"][0]
        inline = part.get("inlineData") or part.get("inline_data")
        if not inline or "data" not in inline:
            return False, None, "sem audio (finish=%s)" % cand.get("finishReason")
        return True, base64.b64decode(inline["data"]), ""
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "ignore")[:160]
        return False, None, "HTTP %d %s" % (e.code, msg)
    except Exception as e:
        return False, None, str(e)[:160]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemini-3.8-flash-lite-tts",
                    help="modelo TTS a ser testado")
    ap.add_argument("--texto", default="Ola, eu sou a voz %s. Este e um teste de ouvido.",
                    help="texto curto lido por cada voz (use %s para o nome da voz)")
    ap.add_argument("--vozes", default=",".join(DEFAULT_VOZES),
                    help="lista de vozes separadas por virgula")
    ap.add_argument("--saida", default=None,
                    help="pasta para salvar os WAVs (padrao: assets/audio/voice_test do projeto atual ou temp)")
    ap.add_argument("--apenas-funcionando", action="store_true",
                    help="mostra so as vozes que geraram audio")
    args = ap.parse_args()

    keys = collect_keys()
    if not keys:
        print("Nenhuma GOOGLE_TTS_API_KEY encontrada.")
        print("Defina: set GOOGLE_TTS_API_KEY_1=XXXX (e _2, _3)")
        return 1

    # Escolhe a primeira chave que nao deu quota esgotada em teste rapido.
    chave_usada = keys[0]

    vozes = [v.strip() for v in args.vozes.split(",") if v.strip()]
    texto = args.texto

    if args.saida:
        out_dir = Path(args.saida)
    else:
        # tenta usar o projeto mais recente, senao temp
        proj = Path("projects")
        mais_recente = None
        if proj.exists():
            dirs = [d for d in proj.iterdir() if d.is_dir() and (d / "artifacts" / "script.json").exists()]
            if dirs:
                mais_recente = max(dirs, key=lambda d: d.stat().st_mtime)
        if mais_recente:
            out_dir = mais_recente / "assets" / "audio" / "voice_test"
        else:
            out_dir = Path("C:/Users/Pires/AppData/Local/Temp/opencode/voice_test")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Escolhe a primeira chave disponível; rotaciona se uma der quota esgotada.
    chave_usada = keys[0]

    print("Testando %d voz(es) com o modelo %s (chaves: %s)\n"
          % (len(vozes), args.model, ", ".join(mask(k) for k in keys)))

    funcionando = []
    for voz in vozes:
        t = texto % voz
        ok, audio, err = False, None, ""
        for chave in keys:
            ok, audio, err = test_voice(chave, args.model, voz, t)
            if ok:
                chave_usada = chave
                break
        status = "OK" if ok else "FALHA"
        print("[%s] %-12s (chave %s) %s %s" % (status, voz,
                                              mask(chave_usada),
                                              ("%d bytes" % len(audio)) if ok else "",
                                              "" if ok else err))
        if ok:
            funcionando.append(voz)
            (out_dir / (voz + ".wav")).write_bytes(audio)

    print()
    if funcionando:
        print("VOZES DISPONIVEIS (%d): %s" % (len(funcionando), ", ".join(funcionando)))
        print("Arquivos de teste gravados em: %s" % out_dir)
        print("Ouça cada %s<voz>.wav para escolher." % (out_dir,))
        return 0
    print("Nenhuma voz funcionou com esta chave/modelo.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
