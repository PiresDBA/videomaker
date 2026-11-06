# -*- coding: utf-8 -*-
"""
Monta uma folha de contato (grade de quadros) para revisar o video sem IA.

Extrai quadros do MP4 nos tempos pedidos (ou usa PNGs de uma pasta) e junta
tudo em uma imagem unica, com o tempo marcado em cada quadro.

Uso:
  python scripts/make_contact_sheet.py --at 5,60,120,250,340,470,570
  python scripts/make_contact_sheet.py --dir C:\\Temp\\snaps --out revisao.jpg
  python scripts/make_contact_sheet.py --video output/cachorro-salsicha.mp4 --at 10,300 --cols 2
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
FONT = Path(r"C:\Windows\Fonts\arial.ttf")


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    cfg = load_json(HERE / "config.json")
    ff = Path(cfg["ffmpeg_dir"])
    ffmpeg = str(ff / "ffmpeg.exe")

    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=str(PROJECT / "output" / "cachorro-salsicha.mp4"))
    ap.add_argument("--at", default="5,60,120,250,340,470,570", help="tempos em segundos, separados por virgula")
    ap.add_argument("--dir", default=None, help="usa PNGs desta pasta em vez do video")
    ap.add_argument("--out", default=str(PROJECT / "artifacts" / "contact_sheet.jpg"))
    ap.add_argument("--cols", type=int, default=0, help="colunas (0 = automatico)")
    ap.add_argument("--width", type=int, default=640, help="largura de cada quadro")
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="sheet_"))
    frames = []

    if args.dir:
        for p in sorted(Path(args.dir).glob("*.png")):
            frames.append((p.stem, p))
    else:
        video = Path(args.video)
        if not video.exists():
            print("video nao encontrado:", video)
            return 2
        for t in args.at.split(","):
            t = t.strip()
            dst = tmp / ("f_%s.png" % t.replace(".", "_"))
            subprocess.run([ffmpeg, "-y", "-v", "error", "-ss", t, "-i", str(video),
                            "-frames:v", "1", "-vf", "scale=%d:-2" % args.width, str(dst)],
                           check=True)
            frames.append(("%ss" % t, dst))

    if not frames:
        print("nenhum quadro encontrado")
        return 2

    n = len(frames)
    cols = args.cols or (1 if n == 1 else 2 if n <= 4 else 3 if n <= 9 else 4)
    rows = (n + cols - 1) // cols

    probe = subprocess.run([str(ff / "ffprobe.exe"), "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=height", "-of",
                            "default=noprint_wrappers=1:nokey=1", str(frames[0][1])],
                           capture_output=True, text=True).stdout.strip()
    cell_h = int(probe) if probe.isdigit() else 360

    inputs, filters, labels = [], [], []
    for i, (label, path) in enumerate(frames):
        inputs += ["-i", str(path)]
        chain = "scale=%d:%d" % (args.width, cell_h)
        if FONT.exists():
            chain += (",drawtext=fontfile='%s':text='%s':x=10:y=10:fontsize=24:"
                      "fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=6"
                      % (str(FONT).replace(":", "\\:"), label))
        filters.append("[%d:v]%s,format=rgba[v%d]" % (i, chain, i))
        labels.append("[v%d]" % i)

    for i in range(n, rows * cols):
        filters.append("color=c=black:s=%dx%d:d=1,format=rgba[pad%d]"
                       % (args.width, cell_h, i))
        labels.append("[pad%d]" % i)

    layout = []
    for i in range(rows * cols):
        r, c = divmod(i, cols)
        layout.append("%d_%d" % (c * args.width, r * cell_h))

    fc = ";".join(filters) + ";" + "".join(labels) + \
         "xstack=inputs=%d:layout=%s[out]" % (rows * cols, "|".join(layout))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([ffmpeg, "-y", "-v", "error"] + inputs + ["-filter_complex", fc,
                    "-map", "[out]", "-frames:v", "1", "-q:v", "3", str(out)], check=True)
    print("quadros:", ", ".join(l for l, _ in frames))
    print("folha  :", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
