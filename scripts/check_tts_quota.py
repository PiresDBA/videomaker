# -*- coding: utf-8 -*-
"""
Verifica a cota diária do Gemini TTS para cada GOOGLE_TTS_API_KEY disponível
e aponta qual chave ainda tem cota sobrando.

Leitura das chaves (nenhuma é gravada no repositorio):
  - Variaveis de ambiente: GOOGLE_TTS_API_KEY_1, _2, _3 ...
  - Ou variavel unica: GOOGLE_TTS_API_KEY (a que ja esta em uso)
  - Ou arquivo .env (local, ja gitignorado) lido via scripts/env_keys.py

Uso:
  python scripts/check_tts_quota.py
  python scripts/check_tts_quota.py --model gemini-3.8-flash-lite-tts --texto "teste de cota"
  set GOOGLE_TTS_API_KEY_1=...
  set GOOGLE_TTS_API_KEY_2=...
  set GOOGLE_TTS_API_KEY_3=...
  python scripts/check_tts_quota.py
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


def collect_keys():
    """Reunir candidatas sem expor valores no log."""
    keys = []
    seen = set()

    def add(key):
        if not key or key in seen:
            return
        seen.add(key)
        keys.append(key)

    # Variavel unica ja em uso (a "atual")
    add(os.environ.get("GOOGLE_TTS_API_KEY", ""))
    if load_env_key:
        try:
            add(load_env_key("GOOGLE_TTS_API_KEY") or "")
        except Exception:
            pass

    # Variaveis numeradas para rotacao (ambiente e/ou .env)
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


def test_key(api_key, model, texto, voice="Leda"):
    """
    Tenta gerar um trecho de audio curto. Retorna:
      ("ok", tamanho_bytes)        -> cota disponível
      ("quota", mensagem)          -> 429 (cota esgotada)
      ("invalida", mensagem)       -> 401/403 (chave invalida)
      ("erro", mensagem)           -> outro erro
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
        data = json.load(urllib.request.urlopen(req, timeout=30))
        cand = data["candidates"][0]
        part = cand["content"]["parts"][0]
        inline = part.get("inlineData") or part.get("inline_data")
        if not inline or "data" not in inline:
            return ("erro", "resposta sem audio (finish=%s)" % cand.get("finishReason"))
        audio = base64.b64decode(inline["data"])
        return ("ok", len(audio))
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "ignore")[:200]
        if e.code == 429:
            return ("quota", msg)
        if e.code in (400, 401, 403):
            return ("invalida", msg)
        return ("erro", "HTTP %d %s" % (e.code, msg))
    except Exception as e:
        return ("erro", str(e)[:200])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemini-3.8-flash-lite-tts",
                    help="modelo usado no teste de cota")
    ap.add_argument("--texto", default="teste de cota",
                    help="texto curto enviado no teste")
    ap.add_argument("--apenas-disponivel", action="store_true",
                    help="imprime so a primeira chave com cota disponivel")
    args = ap.parse_args()

    keys = collect_keys()
    if not keys:
        print("Nenhuma GOOGLE_TTS_API_KEY encontrada.")
        print("Defina: set GOOGLE_TTS_API_KEY_1=XXXX (e _2, _3) ou GOOGLE_TTS_API_KEY")
        return 1

    print("Testando cota do Gemini TTS (%d chave(s), modelo %s)\n" % (len(keys), args.model))

    disponivel = None
    for idx, key in enumerate(keys, 1):
        status, info = test_key(key, args.model, args.texto)
        if status == "ok":
            print("[%d/%d] %s -> DISPONIVEL (audio %d bytes)" % (idx, len(keys), mask(key), info))
            disponivel = key
            if args.apenas_disponivel:
                break
        elif status == "quota":
            print("[%d/%d] %s -> COTA ESGOTADA (429)" % (idx, len(keys), mask(key)))
        elif status == "invalida":
            print("[%d/%d] %s -> CHAVE INVALIDA (401/403): %s" % (idx, len(keys), mask(key), info))
        else:
            print("[%d/%d] %s -> ERRO: %s" % (idx, len(keys), mask(key), info))

    print()
    if disponivel:
        print("CHAVE COM COTA: %s" % mask(disponivel))
        print("Use-a como GOOGLE_TTS_API_KEY (ou GOOGLE_TTS_API_KEY_1) para gerar narracoes.")
        return 0
    print("Nenhuma chave com cota disponível no momento.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
