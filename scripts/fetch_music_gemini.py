# -*- coding: utf-8 -*-
"""
Gera a trilha sonora instrumental no Gemini web e extrai o audio.

Saida:
  assets/audio/gemini/bgm_gemini.mp4  (video com audio)
  assets/audio/gemini/bgm_gemini.wav  (audio puro, 48k stereo)

Uso:
  python scripts/fetch_music_gemini.py
  python scripts/fetch_music_gemini.py --prompt "outra descricao musical"
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
    ap.add_argument("--prompt", default=None)
    ap.add_argument("--wait", type=int, default=600)
    ap.add_argument("--proj", default=None, help="diretorio do projeto (senao vem de config.json)")
    args = ap.parse_args()

    cfg = load_json(HERE / "config.json")
    proj = (Path(args.proj) if args.proj else (HERE / cfg.get("project_dir", ".."))).resolve()
    ff = str(Path(cfg["ffmpeg_dir"]) / "ffmpeg.exe")
    skill = Path(cfg["gemini_skill"])
    music = cfg["music"]

    out_dir = proj / "assets" / "audio" / "gemini"
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, str(skill),
           "--project-dir", str(proj),
           "--kind", "audio",
           "--name", "bgm_gemini",
           "--prompt", args.prompt or music["gemini_prompt"],
           "--out-dir", str(out_dir),
           "--wait", str(args.wait),
           "--pause", "6"]
    print(" ".join(cmd))
    rc = subprocess.run(cmd).returncode
    if rc != 0:
        print("gemini_fetch falhou (codigo %s)" % rc)
        return rc

    mp4 = out_dir / "bgm_gemini.mp4"
    wav = out_dir / "bgm_gemini.wav"
    if mp4.exists() and mp4.stat().st_size > 100000:
        subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error", "-i", str(mp4),
                        "-vn", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", str(wav)],
                       check=True)
        print("audio extraido:", wav)
    if not (wav.exists() and wav.stat().st_size > 100000):
        print("FALHA: trilha nao foi gerada corretamente (sem %s)" % wav.name)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
