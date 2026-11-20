# -*- coding: utf-8 -*-
r"""gen_narration_voicecraft.py - narração por secao via API VoiceCraft (8090).

Primeira opção de voz (com emoção). Gera narration/<lang>/<id>.mp3 e
artifacts/narration_timing_<lang>.json no MESMO formato do gen_narration_edge,
para o build_timeline/mix continuarem funcionando.

Uso: python gen_narration_voicecraft.py --proj <dir> --lang pt \
         --script <script.json> [--voice ...] [--workers 4]
"""
from __future__ import annotations
import argparse, json, subprocess, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from voz_nativa import voz_para, validar_voz, registrar_voz  # regra 2026-11-20

URL = "http://127.0.0.1:8090/api/tts"
LANG_CODE = {"pt": "pt-BR", "en": "en-US", "es": "es-ES"}


def api_up():
    try:
        urllib.request.urlopen("http://127.0.0.1:8090/health", timeout=3).read()
        return True
    except Exception:
        return False


def limpar(texto):
    import re
    texto = re.sub(r"Hahaha+[!.]*", "", texto, flags=re.I)
    texto = re.sub(r"\s{2,}", " ", texto)
    return texto.strip()


def synthesize(text, out, lang_code, profile="infantil", provider="nvidia", voice=None):
    body = {"text": text, "provider": provider, "profile": profile,
            "language": lang_code}
    if voice:
        body["voice"] = voice
    req = urllib.request.Request(URL, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = r.read()
    Path(out).write_bytes(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proj", required=True)
    ap.add_argument("--lang", default="pt")
    ap.add_argument("--script", default=None)
    ap.add_argument("--voice", default="")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    proj = Path(a.proj)
    artifacts = proj / "artifacts"
    script_path = Path(a.script) if a.script else artifacts / "script.json"
    scr = json.load(open(script_path, encoding="utf-8"))
    out = proj / "assets" / "audio" / "narration" / a.lang
    out.mkdir(parents=True, exist_ok=True)
    code = LANG_CODE.get(a.lang, "pt-BR")

    # REGRA 2026-11-20: voz nativa do pais + infantil + emoção máxima.
    # O provider 'auto' (Gemini) usava a MESMA locutora para pt/en/es e gerava
    # sotaque brasileiro no inglês/espanhol. Aqui fixamos a voz pelo idioma.
    cfg = voz_para(a.lang)
    provider, voice, profile = cfg["provider"], cfg["voice"], cfg["profile"]
    validar_voz(a.lang, provider, voice)   # trava antes de sintetizar
    registrar_voz(proj, a.lang, provider, voice)
    print(f"VOZ NATIVA[{a.lang}]: {provider} / {voice} / perfil={profile} "
          f"({cfg['narrador']})", flush=True)

    tarefas = [(s["id"], limpar(s.get("text", ""))) for s in scr["sections"]
               if s.get("text", "").strip()]

    ffprobe = r"C:\videomaker\ffmpeg\bin\ffprobe.exe"

    def gen_one(item):
        sid, texto = item
        dst = out / f"{sid}.mp3"
        for attempt in range(3):
            try:
                synthesize(texto, str(dst), code, profile=profile,
                           provider=provider, voice=voice)
                break
            except Exception as e:
                print(f"{sid}: erro {str(e)[:70]} (tentativa {attempt+1}/3)", flush=True)
                time.sleep(4)
        if dst.exists() and dst.stat().st_size > 1000:
            r = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration",
                                "-of", "default=noprint_wrappers=1:nokey=1", str(dst)],
                               capture_output=True, text=True)
            dur = float(r.stdout.strip()) if r.stdout.strip() else 0.0
            print(f"{sid:9s} {dur:7.2f}s [{code}]", flush=True)
            return {"id": sid, "path": str(dst), "duration": round(dur, 3)}
        print(f"{sid}: FALHA")
        return None

    results = []
    with ThreadPoolExecutor(max_workers=max(1, a.workers)) as ex:
        for r in ex.map(gen_one, tarefas):
            if r:
                results.append(r)
    ordem = [t[0] for t in tarefas]
    results.sort(key=lambda t: ordem.index(t["id"]))
    tp = artifacts / f"narration_timing_{a.lang}.json"
    json.dump(results, open(tp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"TOTAL {sum(t['duration'] for t in results):.1f}s [{a.lang}] -> {tp}")
    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main())
