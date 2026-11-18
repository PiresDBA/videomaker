# -*- coding: utf-8 -*-
"""testar_voicecraft.py - testa a API VoiceCraft com perfil infantil."""
import urllib.request, json, sys, pathlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URL = "http://127.0.0.1:8090/api/tts"
texto = "Oi, pessoal! Bem-vindos a mais uma aventura da Frida e da Luna!"

for provider in ["auto", "gemini"]:
    print(f"\n=== provider={provider} profile=infantil ===", flush=True)
    body = json.dumps({"text": texto, "provider": provider, "profile": "infantil",
                       "language": "pt-BR"}).encode("utf-8")
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
            print("  status:", r.status, "bytes:", len(data),
                  "provider:", r.headers.get("X-TTS-Provider"),
                  "voice:", r.headers.get("X-TTS-Voice"))
            out = pathlib.Path(rf"C:\videomaker\teste_voz_{provider}.mp3")
            out.write_bytes(data)
            print("  salvo:", out)
    except Exception as e:
        print("  ERRO:", type(e).__name__, str(e)[:250])
