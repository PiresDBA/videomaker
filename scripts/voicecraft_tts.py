# -*- coding: utf-8 -*-
r"""voicecraft_tts.py - adaptador do Videomaker para a API VoiceCraft (porta 8090).

PRIMEIRA opção de narração (voz com emoção). Uso:
  python voicecraft_tts.py --text "..." --out voz.mp3 [--lang pt-BR] [--profile infantil]

Fallback automatico: se a API nao estiver no ar, chama gen_narration_edge.py.
"""
import argparse, json, subprocess, sys, urllib.request, time
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URL = "http://127.0.0.1:8090/api/tts"


def api_up():
    try:
        urllib.request.urlopen("http://127.0.0.1:8090/health", timeout=3).read()
        return True
    except Exception:
        return False


def synthesize(text, out, lang="pt-BR", profile="infantil", provider="auto"):
    body = json.dumps({"text": text, "provider": provider, "profile": profile,
                       "language": lang}).encode("utf-8")
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = r.read()
        prov = r.headers.get("X-TTS-Provider", "?")
        voice = r.headers.get("X-TTS-Voice", "?")
    Path(out).write_bytes(data)
    return prov, voice, len(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--lang", default="pt-BR")
    ap.add_argument("--profile", default="infantil")
    ap.add_argument("--provider", default="auto")
    a = ap.parse_args()
    if not api_up():
        print("VoiceCraft API fora do ar - fallback Edge", flush=True)
        return 2
    for tentativa in range(3):
        try:
            prov, voice, n = synthesize(a.text, a.out, a.lang, a.profile, a.provider)
            print(f"OK provider={prov} voice={voice} bytes={n}", flush=True)
            return 0
        except Exception as e:
            print(f"tentativa {tentativa+1} falhou: {str(e)[:120]}", flush=True)
            time.sleep(3)
    return 1


if __name__ == "__main__":
    sys.exit(main())
