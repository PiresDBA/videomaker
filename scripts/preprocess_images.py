# -*- coding: utf-8 -*-
"""
Corta/redimensiona as imagens geradas (assets/images/gemini/scenes)
para 1920x1080 e copia para a pasta do HyperFrames (assets/images).

Uso:
  python scripts/preprocess_images.py
  python scripts/preprocess_images.py --only s4_barking.jpg,s8_jealous.jpg
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--proj", default=None, help="diretorio do projeto (senao vem de config.json)")
    ap.add_argument("--hf-dir", default=None,
                    help="workspace HyperFrames (senao: <raiz>/hyperframes-workspace)")
    ap.add_argument("--scenes", default=None, help="caminho do scenes.json")
    args = ap.parse_args()

    cfg = load_json(HERE / "config.json")
    proj = (Path(args.proj) if args.proj else (HERE / cfg.get("project_dir", ".."))).resolve()
    hf_dir = Path(args.hf_dir) if args.hf_dir else (proj.parent.parent / "hyperframes-workspace")
    ff = str(Path(cfg["ffmpeg_dir"]) / "ffmpeg.exe")
    w, h = cfg["video"]["width"], cfg["video"]["height"]

    src_dir = proj / "assets" / "images" / "gemini" / "scenes"
    dst_dir = hf_dir / "assets" / "images"
    dst_dir.mkdir(parents=True, exist_ok=True)

    scenes = load_json(Path(args.scenes) if args.scenes else HERE / "scenes.json")
    names = []
    for sid, cfg_s in scenes.items():
        if sid.startswith("_"):
            continue
        for n in cfg_s.get("images", []):
            if n not in names:
                names.append(n)

    only = {x.strip() for x in args.only.split(",") if x.strip()}
    if only:
        names = [n for n in names if n in only]

    for name in names:
        src = src_dir / name
        if not src.exists():
            print("FALTA:", src)
            continue
        dst = dst_dir / name
        subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
                        "-vf", "scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d" % (w, h, w, h),
                        "-q:v", "2", str(dst)], check=True)
        print("%-24s -> %s" % (name, dst.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
