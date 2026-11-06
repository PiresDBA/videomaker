# -*- coding: utf-8 -*-
"""
Gera a narracao (Edge-TTS) secao por secao a partir de artifacts/script.json.

Voz, velocidade e tom ficam em scripts/config.json:
  voice        -> pt-BR-ThalitaNeural (jovem, sorridente, empolgada)
  voice_rate   -> velocidade padrao (+10% = mais animada)
  voice_pitch  -> tom (+6Hz = mais jovem/brilhante)
  rate_by_pace -> ajuste fino por ritmo de cada secao
  rate_overrides -> forca um rate para uma secao especifica

Uso:
  python scripts/gen_narration.py
  python scripts/gen_narration.py --only s1,s12
  python scripts/gen_narration.py --voice pt-BR-JulioNeural --rate +14%
  python scripts/gen_narration.py --preview "Teste de voz empolgada."
"""
import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path

import edge_tts

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def ffprobe_duration(path, ffprobe):
    r = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True)
    try:
        return round(float(r.stdout.strip()), 3)
    except Exception:
        return None


async def synthesize(text, voice, rate, pitch, volume, out, tries=4):
    last = None
    for i in range(tries):
        try:
            comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume)
            await comm.save(str(out))
            return
        except Exception as e:
            last = e
            print("  retry %d/%d (%s)" % (i + 1, tries, str(e)[:80]))
            await asyncio.sleep(2 + i * 2)
    raise last


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="ids separados por virgula (ex: s1,s2)")
    ap.add_argument("--voice", default=None)
    ap.add_argument("--rate", default=None)
    ap.add_argument("--pitch", default=None)
    ap.add_argument("--preview", default=None, help="gera apenas uma frase de teste")
    args = ap.parse_args()

    cfg = load_json(HERE / "config.json")
    proj = (HERE / cfg.get("project_dir", "..")).resolve()
    ffprobe = str(Path(cfg["ffmpeg_dir"]) / "ffprobe.exe")

    voice = args.voice or cfg["voice"]
    pitch = args.pitch or cfg.get("voice_pitch", "+0Hz")
    volume = cfg.get("voice_volume", "+0%")

    if args.preview:
        out = proj / "assets" / "audio" / "preview.mp3"
        out.parent.mkdir(parents=True, exist_ok=True)
        await synthesize(args.preview, voice, args.rate or cfg["voice_rate"], pitch, volume, out)
        print("preview:", out, ffprobe_duration(out, ffprobe), "s")
        return

    script = load_json(proj / "artifacts" / "script.json")
    out_dir = proj / "assets" / "audio" / "narration"
    out_dir.mkdir(parents=True, exist_ok=True)

    only = {x.strip() for x in args.only.split(",") if x.strip()}
    rate_by_pace = cfg.get("rate_by_pace", {})
    overrides = cfg.get("rate_overrides", {})

    results = []
    for s in script["sections"]:
        sid = s["id"]
        if only and sid not in only:
            continue
        text = s.get("delivery_cues", {}).get("provider_text") or s["text"]
        pace = s.get("delivery_cues", {}).get("pace", "conversational")
        rate = args.rate or overrides.get(sid) or rate_by_pace.get(pace, cfg["voice_rate"])
        out = out_dir / ("%s.mp3" % sid)
        await synthesize(text, voice, rate, pitch, volume, out)
        dur = ffprobe_duration(out, ffprobe)
        results.append({"id": sid, "path": str(out), "duration": dur,
                        "rate": rate, "voice": voice, "pitch": pitch})
        print("%-4s %7.2fs  rate %s" % (sid, dur or 0, rate))

    timing_path = proj / "artifacts" / "narration_timing.json"
    if only:
        old = {x["id"]: x for x in load_json(timing_path)}
        for r in results:
            old[r["id"]] = r
        order = [s["id"] for s in script["sections"]]
        results = [old[k] for k in order if k in old]

    with open(timing_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    total = sum((r["duration"] or 0) for r in results)
    print("TOTAL %.1fs  (voz %s)" % (total, voice))
    target = cfg.get("target_duration_s", 590)
    tol = cfg.get("duration_tolerance_pct", 5)
    lo, hi = target * (1 - tol / 100), target * (1 + tol / 100)
    if not (lo <= total <= hi):
        print("AVISO: total fora da meta %.0f-%.0f s. Ajuste rate_by_pace no config." % (lo, hi))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
