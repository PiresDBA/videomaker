# -*- coding: utf-8 -*-
"""
Confere o MP4 final: duracao, resolucao, fps, codecs e loudness.

Uso:
  python scripts/verify_output.py
  python scripts/verify_output.py --file output/cachorro-salsicha.mp4
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    cfg = load_json(HERE / "config.json")
    proj = (HERE / cfg.get("project_dir", "..")).resolve()
    ff = Path(cfg["ffmpeg_dir"])
    ffprobe = str(ff / "ffprobe.exe")

    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=None)
    ap.add_argument("--proj", default=None, help="diretorio do projeto (senao vem de config.json)")
    args = ap.parse_args()
    proj = (Path(args.proj) if args.proj else (HERE / cfg.get("project_dir", ".."))).resolve()
    path = Path(args.file) if args.file else (proj / "output" / (proj.name + ".mp4"))
    if not path.exists():
        print("NAO ENCONTRADO:", path)
        return 2

    r = subprocess.run([ffprobe, "-v", "error", "-show_entries",
                        "format=duration,size:stream=codec_name,codec_type,width,height,r_frame_rate",
                        "-of", "json", str(path)], capture_output=True, text=True)
    info = json.loads(r.stdout)
    fmt = info.get("format", {})
    streams = info.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), {})
    a = next((s for s in streams if s.get("codec_type") == "audio"), {})
    dur = float(fmt.get("duration", 0))

    print("arquivo :", path)
    print("duracao : %.2f s" % dur)
    print("tamanho : %.1f MB" % (int(fmt.get("size", 0)) / 1048576))
    print("video   : %s %sx%s @ %s fps" % (v.get("codec_name"), v.get("width"),
                                           v.get("height"), v.get("r_frame_rate")))
    print("audio   : %s" % a.get("codec_name"))

    expected = None
    try:
        expected = float(load_json(proj / "artifacts" / "timeline.json")["total"])
        print("timeline: %.2f s (delta %.2f s)" % (expected, dur - expected))
    except Exception:
        pass

    r2 = subprocess.run([str(ff / "ffmpeg.exe"), "-hide_banner", "-i", str(path), "-af",
                         "loudnorm=print_format=summary", "-f", "null", "-"],
                        capture_output=True, text=True)
    for line in r2.stderr.splitlines():
        if "Input Integrated" in line or "Input True Peak" in line:
            print(line.strip())

    ok = (v.get("width") == 1920 and v.get("height") == 1080
          and (expected is None or abs(dur - expected) < 2.0))
    print("STATUS  :", "OK" if ok else "VERIFICAR")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
