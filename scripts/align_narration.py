# -*- coding: utf-8 -*-
"""
Alinha a narracao gerada em blocos (narration_chunks/c1..c3.wav) com as secoes
do roteiro e grava um arquivo por secao em assets/audio/narration/<id>.wav.

Como funciona:
  1. transcreve cada bloco com faster-whisper (timestamps por palavra);
  2. localiza as primeiras palavras de cada secao no texto transcrito;
  3. corta o audio no meio do silencio antes dessa palavra.

Uso:
  python scripts/align_narration.py
  python scripts/align_narration.py --chunk c1 --debug
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


def load_audio(path, sr=16000, ffmpeg=r"C:\videomaker\ffmpeg\bin\ffmpeg.exe"):
    raw = subprocess.run(
        [ffmpeg, "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1",
         "-ar", str(sr), "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32), sr


def transcribe_words(audio, sr):
    from faster_whisper import WhisperModel
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = model.transcribe(audio, language="pt", word_timestamps=True,
                               vad_filter=True, beam_size=5)
    words = []
    for s in segs:
        for w in (s.words or []):
            n = norm(w.word)
            if n:
                words.append((n, float(w.start), float(w.end)))
    return words


def find_section(words, target, start_idx):
    """Procura a melhor posicao para a sequencia `target` a partir de start_idx."""
    best, best_score = None, -1
    n = len(target)
    for i in range(start_idx, max(start_idx, len(words) - n + 1)):
        score = 0
        for j in range(n):
            if words[i + j][0] == target[j]:
                score += 2
            elif target[j] in words[i + j][0] or words[i + j][0] in target[j]:
                score += 1
            else:
                break
        if score > best_score:
            best, best_score = i, score
        if best_score >= 2 * n:
            break
    return best, best_score


def cut(src, dst, start, end, ffmpeg=r"C:\videomaker\ffmpeg\bin\ffmpeg.exe"):
    subprocess.run(
        [ffmpeg, "-y", "-v", "error", "-i", str(src), "-ss", "%.3f" % max(0, start),
         "-to", "%.3f" % end, "-ac", "1", "-ar", "24000",
         "-c:a", "pcm_s16le", str(dst)], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--pad", type=float, default=0.18)
    args = ap.parse_args()

    cfg = load_json(HERE / "config.json")
    ffmpeg = str(Path(cfg["ffmpeg_dir"]) / "ffmpeg.exe")
    script = load_json(PROJECT / "artifacts" / "script.json")
    by_id = {s["id"]: s for s in script["sections"]}
    chunks = load_json(PROJECT / "assets" / "audio" / "narration_chunks" / "chunks.json")
    # Filter chunk ids to only include those that exist in the script
    chunks = [{"chunk": ch["chunk"], "ids": [i for i in ch["ids"] if i in by_id]}
              for ch in chunks]

    out_dir = PROJECT / "assets" / "audio" / "narration"
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for ch in chunks:
        ids = ch["ids"]
        src = PROJECT / "assets" / "audio" / "narration_chunks" / (ch["chunk"] + ".wav")
        audio, sr = load_audio(src, ffmpeg=ffmpeg)
        words = transcribe_words(audio, sr)
        total = len(audio) / sr

        starts = []
        idx = 0
        for sid in ids:
            target = [norm(w) for w in by_id[sid]["text"].split()[:7]]
            pos, score = find_section(words, target, idx)
            if pos is None:
                print("AVISO: nao achei inicio de", sid)
                pos = idx
            starts.append((sid, words[pos][1], score))
            idx = pos + 1
            if args.debug:
                heard = " ".join(w[0] for w in words[pos:pos + 7])
                print("  %-4s t=%7.2f score=%d  ouvi: %s" % (sid, words[pos][1], score, heard))

        for i, (sid, t0, _) in enumerate(starts):
            t1 = starts[i + 1][1] if i + 1 < len(starts) else total
            dst = out_dir / ("%s.wav" % sid)
            cut(src, dst, t0 - args.pad, t1, ffmpeg=ffmpeg)
            d = subprocess.run([str(Path(cfg["ffmpeg_dir"]) / "ffprobe.exe"), "-v", "error",
                                "-show_entries", "format=duration",
                                "-of", "default=noprint_wrappers=1:nokey=1", str(dst)],
                               capture_output=True, text=True).stdout.strip()
            results.append({"id": sid, "path": str(dst), "duration": round(float(d), 3)})
            print("%-4s %7.2fs" % (sid, float(d)))

    order = [s["id"] for s in script["sections"]]
    results.sort(key=lambda r: order.index(r["id"]))
    with open(PROJECT / "artifacts" / "narration_timing.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("TOTAL %.1fs" % sum(r["duration"] for r in results))


if __name__ == "__main__":
    sys.exit(main())
