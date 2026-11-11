# -*- coding: utf-8 -*-
"""
Monta o mix final: narracao + trilha (Gemini ou procedural), com ducking
lateral e normalizacao para -14 LUFS / -1.5 dBTP.

Entradas:
  assets/audio/narration_full.wav
  assets/audio/gemini/bgm_gemini.wav   (provider = gemini)
  assets/audio/music/bgm_procedural.wav (provider = procedural)

Saida:
  assets/audio/final_mix.m4a
  hyperframes-workspace/final_mix.m4a  (copia usada no render)

Uso:
  python scripts/mix_audio.py
  python scripts/mix_audio.py --provider procedural
  python scripts/mix_audio.py --gain 0.5
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from build_composition import INTRO_DUR

HERE = Path(__file__).resolve().parent


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default=None, choices=["gemini", "procedural"])
    ap.add_argument("--gain", type=float, default=None)
    ap.add_argument("--proj", default=None, help="diretorio do projeto (senao vem de config.json)")
    ap.add_argument("--lang", default="pt", help="idioma da narracao a mixar (pt,en,es). padrao: pt")
    ap.add_argument("--hf-dir", default=None,
                    help="pasta do workspace HyperFrames para copiar o mix (senao: padrao do projeto)")
    args = ap.parse_args()

    cfg = load_json(HERE / "config.json")
    proj = (Path(args.proj) if args.proj else (HERE / cfg.get("project_dir", ".."))).resolve()
    lang = args.lang.lower().strip()
    ff = str(Path(cfg["ffmpeg_dir"]) / "ffmpeg.exe")
    music = cfg["music"]
    loud = cfg["loudness"]

    provider = args.provider or music.get("provider", "gemini")
    gain = args.gain if args.gain is not None else music.get("gain", 0.42)
    xf = float(music.get("loop_crossfade_s", 4))

    aud = proj / "assets" / "audio"
    narration = aud / f"narration_full_{lang}.wav"
    if not narration.exists():
        print("FALTA narration_full.wav - rode scripts/build_timeline.py antes.")
        return 2

    if provider == "gemini":
        bgm_src = aud / "gemini" / "bgm_gemini.wav"
        if not bgm_src.exists():
            bgm_src = aud / "music" / "bgm_procedural.wav"
    else:
        bgm_src = aud / "music" / "bgm_procedural.wav"
        if not bgm_src.exists():
            bgm_src = aud / "gemini" / "bgm_gemini.wav"
    if not bgm_src.exists():
        print("FALTA trilha: nem bgm_procedural.wav nem bgm_gemini.wav encontrados")
        return 2

    total = float(load_json(proj / "artifacts" / "timeline.json")["total"])
    total_mix = INTRO_DUR + total
    lead_ms = int(round(INTRO_DUR * 1000))

    # loop com crossfade ate passar do total
    loop = aud / ("bgm_%s_loop.wav" % provider)
    chain = ""
    n = 2
    cmd = [ff, "-y", "-hide_banner", "-loglevel", "error"]
    while True:
        dur = float(subprocess.run(
            [str(Path(cfg["ffmpeg_dir"]) / "ffprobe.exe"), "-v", "error",
             "-show_entries", "format=duration", "-of",
             "default=noprint_wrappers=1:nokey=1", str(bgm_src)],
            capture_output=True, text=True).stdout.strip() or 0)
        need = int((total_mix / max(dur, 1)) + 2)
        if need <= n:
            break
        n = need

    for _ in range(n):
        cmd += ["-i", str(bgm_src)]

    if n == 1:
        chain = "[0:a]atrim=0:%.3f[out]" % total_mix
    else:
        prev = "0"
        for i in range(1, n):
            lab = "a%d" % i
            chain += "[%s][%d]acrossfade=d=%s:c1=tri:c2=tri[%s];" % (prev, i, xf, lab)
            prev = lab
        chain += "[%s]atrim=0:%.3f,asetpts=N/SR/TB[out]" % (prev, total_mix)

    subprocess.run(cmd + ["-filter_complex", chain, "-map", "[out]",
                          "-c:a", "pcm_s16le", str(loop)], check=True)

    out = aud / "final_mix.m4a"
    filt = (
        "[1:a]volume=%.3f,afade=t=in:st=0:d=2.5,afade=t=out:st=%.3f:d=3.7[bgm];"
        "[0:a]adelay=%d:all=1,apad=pad_dur=%.3f,asplit=2[voice][key];"
        "[bgm][key]sidechaincompress=threshold=%s:ratio=%s:attack=%s:release=%s[duck];"
        "[voice][duck]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[mix];"
        "[mix]loudnorm=I=%s:TP=%s:LRA=%s[out]"
        % (gain, total_mix - 3.756, lead_ms, INTRO_DUR,
           music.get("duck_threshold", 0.05), music.get("duck_ratio", 9),
           music.get("duck_attack_ms", 15), music.get("duck_release_ms", 350),
           loud.get("final_i", -14), loud.get("true_peak", -1.5), loud.get("lra", 11))
    )
    subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error",
                    "-i", str(narration), "-i", str(loop),
                    "-filter_complex", filt, "-map", "[out]", "-t", "%.3f" % total_mix,
                    "-c:a", "aac", "-b:a", "192k", str(out)], check=True)

    dst = Path(args.hf_dir) if args.hf_dir else proj
    dst.mkdir(parents=True, exist_ok=True)
    dst = dst / "final_mix.m4a"
    shutil.copyfile(out, dst)
    print("mix:", out, "->", dst)

    r = subprocess.run([ff, "-hide_banner", "-i", str(out), "-af",
                        "loudnorm=I=%s:TP=%s:print_format=summary" % (loud.get("final_i", -14), loud.get("true_peak", -1.5)),
                        "-f", "null", "-"], capture_output=True, text=True)
    for line in r.stderr.splitlines():
        if "Input Integrated" in line or "Input True Peak" in line:
            print(line.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
