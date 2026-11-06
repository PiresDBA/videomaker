"""Trilha procedural alegre (offline, custo zero) - fallback da trilha do Gemini.

Gera assets/audio/music/bgm_procedural.wav com arranjo de ukulele/marimba/pizzicato.
A duracao vem de artifacts/timeline.json (ou --duration).

Uso:
  python scripts/gen_music_procedural.py
  python scripts/gen_music_procedural.py --duration 600
"""
import argparse
import json
import math
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent

SR = 44100
BPM = 120.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT
TOTAL = 592.0
np.random.seed(1234)

# Note frequencies
def f(name):
    names = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6,
             'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
    if len(name) == 2:
        n, octv = name[0], int(name[1])
    else:
        n, octv = name[:2], int(name[2])
    midi = 12 * (octv + 1) + names[n]
    return 440.0 * 2 ** ((midi - 69) / 12.0)


def env_ad(n, attack, decay, curve=4.0):
    a = max(1, int(attack * SR))
    e = np.ones(n)
    e[:a] = np.linspace(0, 1, a)
    d = np.exp(-curve * np.linspace(0, 1, n))
    return e * d


def marimba(freq, dur, amp=0.3):
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = (np.sin(2 * np.pi * freq * t) * 1.0 +
           0.5 * np.sin(2 * np.pi * freq * 3.93 * t) +
           0.25 * np.sin(2 * np.pi * freq * 9.2 * t))
    return amp * sig * env_ad(n, 0.002, dur, 5.0)


def pluck(freq, dur, amp=0.25, bright=0.5):
    """Karplus-Strong plucked string."""
    n = int(dur * SR)
    period = max(2, int(SR / freq))
    buf = (np.random.rand(period) * 2 - 1) * bright
    out = np.zeros(n)
    idx = 0
    for i in range(n):
        out[i] = buf[idx]
        nxt = buf[idx] * 0.996 + buf[(idx + 1) % period] * 0.0
        buf[idx] = 0.5 * (buf[idx] + buf[(idx - 1) % period]) * 0.996
        idx = (idx + 1) % period
    e = np.exp(-3.0 * np.linspace(0, 1, n))
    return amp * out * e


def bass(freq, dur, amp=0.35):
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * 2 * freq * t)
    e = np.exp(-2.2 * np.linspace(0, 1, n))
    a = max(1, int(0.006 * SR))
    e[:a] *= np.linspace(0, 1, a)
    return amp * sig * e


def shaker(dur=0.06, amp=0.08):
    n = int(dur * SR)
    noise = np.random.randn(n)
    # crude high-pass
    noise = np.diff(np.concatenate([[0], noise]))
    e = np.exp(-30 * np.linspace(0, 1, n))
    return amp * noise * e


def woodblock(freq=900, dur=0.08, amp=0.12):
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * freq * t) * np.exp(-25 * t)
    return amp * sig


def add(buf, start, sig):
    s = int(start * SR)
    e = min(len(buf), s + len(sig))
    if s < len(buf):
        buf[s:e] += sig[:e - s]


# Chord voicings (root, third, fifth) around C4
CH = {
    'C':  ['C4', 'E4', 'G4'],
    'G':  ['G3', 'B3', 'D4'],
    'Am': ['A3', 'C4', 'E4'],
    'F':  ['F3', 'A3', 'C4'],
    'Dm': ['D3', 'F3', 'A3'],
    'Em': ['E3', 'G3', 'B3'],
}
ROOT = {'C': 'C2', 'G': 'G1', 'Am': 'A1', 'F': 'F1', 'Dm': 'D2', 'Em': 'E2'}

# 8-bar progression per section (each bar 2s at 120bpm)
PROG_MAIN = ['C', 'G', 'Am', 'F', 'C', 'G', 'F', 'C']
PROG_B = ['F', 'G', 'Em', 'Am', 'F', 'G', 'C', 'C']
PROG_TENDER = ['C', 'Am', 'F', 'G', 'C', 'Am', 'F', 'C']

# Melody motifs in scale degrees (C major), -1 = rest
MOTIF_A = [4, 6, 7, 6, 4, 2, 4, -1, 7, 6, 4, 2, 4, 6, 7, -1]
MOTIF_B = [7, 7, 6, 4, 2, 4, 6, 7, 4, 4, 2, 2, 4, -1, -1, -1]
SCALE = ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5']


def section(kind):
    """Render an 8-bar (~16s) section as stereo float array."""
    n = int(8 * BAR * SR)
    L = np.zeros(n)
    R = np.zeros(n)

    if kind in ('main', 'finale'):
        prog, motif, mel_amp = PROG_MAIN, MOTIF_A, 0.26
        dens = 1.0
    elif kind == 'b':
        prog, motif, mel_amp = PROG_B, MOTIF_B, 0.24
        dens = 0.9
    else:
        prog, motif, mel_amp = PROG_TENDER, MOTIF_A, 0.20
        dens = 0.6

    for bar, chord in enumerate(prog):
        t0 = bar * BAR
        # bass on 1 and 3
        add(L, t0, bass(f(ROOT[chord]), BEAT * 1.4, 0.30))
        add(R, t0, bass(f(ROOT[chord]), BEAT * 1.4, 0.30))
        add(L, t0 + 2 * BEAT, bass(f(ROOT[chord]), BEAT * 1.2, 0.24))
        add(R, t0 + 2 * BEAT, bass(f(ROOT[chord]), BEAT * 1.2, 0.24))
        # ukulele strum arpeggio on each beat
        notes = CH[chord]
        for b in range(4):
            for k, nt in enumerate(notes):
                off = t0 + b * BEAT + k * 0.02
                s = pluck(f(nt), BEAT * 0.9, 0.10 * dens, 0.5)
                add(L, off, s * 0.9)
                add(R, off + 0.006, s)
        # shaker on 2 and 4
        add(L, t0 + BEAT, shaker(amp=0.05 * dens))
        add(R, t0 + 3 * BEAT, shaker(amp=0.05 * dens))
        # woodblock accent on 1
        add(L, t0, woodblock(amp=0.06 * dens))
        add(R, t0, woodblock(amp=0.06 * dens))

    # melody: 16 eighth notes over 8 bars (one per beat/2)
    step = BAR / 4.0  # two notes per bar? -> 16 notes over 8 bars = 2 per bar
    step = 8 * BAR / len(motif)
    for i, deg in enumerate(motif):
        if deg < 0:
            continue
        note_name = SCALE[min(deg, len(SCALE) - 1)]
        off = i * step
        amp = mel_amp * (1.0 if kind != 'tender' else 0.8)
        s = marimba(f(note_name), step * 1.6, amp)
        add(L, off, s * 0.95)
        add(R, off + 0.004, s)

    return np.stack([L, R], axis=1)


def main():
    global TOTAL
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--proj", default=None, help="diretorio do projeto (senao vem de config.json)")
    args = ap.parse_args()

    cfg = json.load(open(HERE / "config.json", encoding="utf-8"))
    proj = (Path(args.proj) if args.proj else (HERE / cfg.get("project_dir", ".."))).resolve()
    if args.duration:
        TOTAL = args.duration
    else:
        try:
            tl = json.load(open(proj / "artifacts" / "timeline.json", encoding="utf-8"))
            TOTAL = float(tl["total"]) + 2.0
        except Exception:
            TOTAL = 592.0

    # Arrangement plan: list of (kind, repeats)
    plan = [
        ('tender', 1),          # 0-16   intro
        ('main', 3),            # 16-64
        ('b', 2),               # 64-96
        ('main', 3),            # 96-144
        ('b', 2),               # 144-176
        ('main', 3),            # 176-224
        ('b', 2),               # 224-256
        ('main', 3),            # 256-304
        ('b', 2),               # 304-336
        ('main', 3),            # 336-384
        ('b', 2),               # 384-416
        ('main', 3),            # 416-464
        ('b', 2),               # 464-496
        ('main', 3),            # 496-544
        ('tender', 2),          # 544-576  ending
        ('finale', 1),          # 576-592
    ]

    total_samples = int(TOTAL * SR)
    out = np.zeros((total_samples, 2), dtype=np.float32)

    pos = 0
    for kind, reps in plan:
        seg = section(kind)
        for _ in range(reps):
            end = min(total_samples, pos + len(seg))
            if pos >= total_samples:
                break
            out[pos:end] += seg[:end - pos]
            pos = end

    # gentle fades
    fade = int(1.5 * SR)
    out[:fade] *= np.linspace(0, 1, fade)[:, None]
    out[-fade:] *= np.linspace(1, 0, fade)[:, None]

    # normalize to -3 dBFS peak then soft limit
    peak = np.max(np.abs(out))
    if peak > 0:
        out = out / peak * 0.7
    out = np.tanh(out * 1.2) * 0.85

    pcm = (out * 32767).astype(np.int16)
    out_dir = proj / "assets" / "audio" / "music"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = str(out_dir / "bgm_procedural.wav")
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print('wrote', path, 'seconds', len(pcm) / SR)


if __name__ == '__main__':
    main()
