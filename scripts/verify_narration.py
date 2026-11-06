# -*- coding: utf-8 -*-
"""
Confere se a narracao de cada secao contem o texto do roteiro.

Transcreve cada arquivo de assets/audio/narration/ com faster-whisper e compara
com artifacts/script.json: palavras ouvidas x esperadas, inicio e fim.

Uso:
  python scripts/verify_narration.py
  python scripts/verify_narration.py --ids s4,s12
  python scripts/verify_narration.py --verbose
"""
import argparse
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def norm(w):
    w = unicodedata.normalize("NFD", w.lower())
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", w)


def load_audio(path, ffmpeg, sr=16000):
    raw = subprocess.run([ffmpeg, "-v", "error", "-i", str(path), "-f", "f32le",
                          "-ac", "1", "-ar", str(sr), "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def coverage(expected, heard):
    """Semelhanca entre o texto esperado e o transcrito (0..1) + trechos faltando.

    Usa difflib porque o Whisper escreve numeros de outro jeito ("24" em vez de
    "vinte e quatro") e isso nao significa audio faltando.
    """
    import difflib
    exp = [norm(w) for w in expected if norm(w)]
    h = [norm(w) for w in heard if norm(w)]
    sm = difflib.SequenceMatcher(a=exp, b=h, autojunk=False)
    missing = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace") and (i2 - i1) >= 2:
            missing.append(" ".join(exp[i1:i2]))
    return sm.ratio(), missing, len(exp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default=None, help="ex.: s4,s12")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--model", default="small")
    args = ap.parse_args()

    cfg = load_json(HERE / "config.json")
    ffmpeg = str(Path(cfg["ffmpeg_dir"]) / "ffmpeg.exe")
    script = load_json(PROJECT / "artifacts" / "script.json")
    timing = load_json(PROJECT / "artifacts" / "narration_timing.json")
    by_id = {s["id"]: s["text"] for s in script["sections"]}
    only = set(args.ids.split(",")) if args.ids else None

    from faster_whisper import WhisperModel
    model = WhisperModel(args.model, device="cpu", compute_type="int8")

    worst = 1.0
    for item in timing:
        sid = item["id"]
        if only and sid not in only:
            continue
        audio = load_audio(item["path"], ffmpeg)
        segs, _ = model.transcribe(audio, language="pt", vad_filter=True, word_timestamps=True)
        heard = [w.word for s in segs for w in (s.words or [])]
        exp_words = by_id[sid].split()
        cov, missing, total = coverage(exp_words, heard)
        worst = min(worst, cov)
        flag = "ok " if cov >= 0.90 else "VER"
        print("%s %-4s %6.2fs  similaridade %5.1f%% (esperado %d palavras)"
              % (flag, sid, item["duration"], cov * 100, total))
        if args.verbose:
            print("    inicio esperado:", " ".join(exp_words[:6]))
            print("    inicio ouvido  :", " ".join(heard[:6]))
            print("    fim esperado   :", " ".join(exp_words[-6:]))
            print("    fim ouvido     :", " ".join(heard[-6:]))
            if missing:
                print("    trechos possivelmente faltando:")
                for m in missing[:5]:
                    print("      -", m)

    print("\ncobertura minima: %.1f%%  ->  %s"
          % (worst * 100, "OK" if worst >= 0.85 else "REVISAR"))
    return 0 if worst >= 0.85 else 1


if __name__ == "__main__":
    sys.exit(main())
