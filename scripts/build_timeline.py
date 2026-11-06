# -*- coding: utf-8 -*-
"""
Monta a linha do tempo real da narracao:
  1. normaliza cada MP3 para -16 LUFS
  2. concatena com pausas (config.gap_seconds)
  3. grava assets/audio/narration_full.wav
  4. grava artifacts/timeline.json (start/end por secao)

Uso:
  python scripts/build_timeline.py
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def probe_duration(ffprobe, path):
    out = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                         capture_output=True, text=True).stdout.strip()
    return float(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proj", default=None, help="diretorio do projeto (senao vem de config.json)")
    args = ap.parse_args()

    cfg = load_json(HERE / "config.json")
    proj = (Path(args.proj) if args.proj else (HERE / cfg.get("project_dir", ".."))).resolve()
    ff = str(Path(cfg["ffmpeg_dir"]) / "ffmpeg.exe")
    ffprobe = str(Path(cfg["ffmpeg_dir"]) / "ffprobe.exe")

    aud = proj / "assets" / "audio"
    timing = load_json(proj / "artifacts" / "narration_timing.json")
    gap = float(cfg.get("gap_seconds", 0.6))
    tempo = float(cfg.get("narration_tempo", 1.0))
    loud = cfg.get("loudness", {})
    nar_i = loud.get("narration_i", -16)
    tp = loud.get("true_peak", -1.5)
    lra = loud.get("lra", 11)

    silence = aud / "silence.wav"
    subprocess.run([ff, "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                    "-t", str(gap), str(silence)], check=True, capture_output=True)

    norm_dir = aud / "narration_norm"
    norm_dir.mkdir(parents=True, exist_ok=True)

    lines, timeline = [], []
    cursor = 0.0
    for i, item in enumerate(timing):
        src = Path(item["path"])
        dst = norm_dir / ("%s.wav" % item["id"])
        chain = []
        if abs(tempo - 1.0) > 1e-3:
            chain.append("atempo=%.4f" % tempo)
        chain.append("loudnorm=I=%s:TP=%s:LRA=%s" % (nar_i, tp, lra))
        subprocess.run([ff, "-y", "-i", str(src), "-ar", "44100", "-ac", "2",
                        "-af", ",".join(chain), str(dst)],
                       check=True, capture_output=True)
        dur = probe_duration(ffprobe, dst)
        timeline.append({"id": item["id"], "start": round(cursor, 3),
                         "end": round(cursor + dur, 3), "duration": round(dur, 3)})
        lines.append("file '%s'" % str(dst).replace("\\", "/"))
        cursor += dur
        if i < len(timing) - 1:
            lines.append("file '%s'" % str(silence).replace("\\", "/"))
            cursor += gap

    listfile = aud / "concat_narration.txt"
    listfile.write_text("\n".join(lines) + "\n", encoding="utf-8")

    nar_full = aud / "narration_full.wav"
    subprocess.run([ff, "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
                    "-ar", "44100", "-ac", "2", str(nar_full)],
                   check=True, capture_output=True)

    with open(proj / "artifacts" / "timeline.json", "w", encoding="utf-8") as f:
        json.dump({"timeline": timeline, "total": round(cursor, 3), "gap": gap},
                  f, ensure_ascii=False, indent=2)

    print("narration_full: %.3fs" % cursor)
    for t in timeline:
        print("  %-4s %8.3f -> %8.3f" % (t["id"], t["start"], t["end"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
