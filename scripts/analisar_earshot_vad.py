# -*- coding: utf-8 -*-
"""analisar_earshot_vad.py - Detecta segmentos de VOZ num video usando EARSHOT.

O earshot 1.2.2 instalado NAO tem `segments()` nem `SegmenterOptions`.
A API real e:
    earshot.Detector().predict_i16(frame) -> float [0,1]
onde `frame` tem EXATAMENTE 256 amostras int16 a 16000 Hz (16 ms).
Scores > 0.5 indicam voz.

Este script:
  1. extrai o audio com ffmpeg -> WAV mono 16 kHz int16;
  2. le com wave/numpy;
  3. percorre frame a frame, agrupa frames consecutivos com voz em segmentos
     (com histerese e merge de pausas curtas);
  4. imprime e salva relatorio_earshot.txt.
"""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
import earshot

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

VIDEO_PATH = Path(
    r"C:\videomaker\projects\bulldogue-ingles-frida-e-dachshund-marrom-luna-fic\output\bulldogue-ingles-frida-e-dachshund-marrom-luna-fic.mp4"
)
RELATORIO = Path(r"C:\videomaker\relatorio_earshot.txt")
SR = 16000
FRAME = 256
THRESHOLD = 0.5
MERGE_GAP = 0.30       # pausas < 300ms sao coladas no mesmo segmento
MIN_DUR = 0.10         # descarta rajadas < 100ms


def find_ffmpeg() -> str:
    """Localiza o ffmpeg (PATH ou instalacao winget conhecida)."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    known = (r"C:\Users\Pires\AppData\Local\Microsoft\WinGet\Packages"
             r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
             r"\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe")
    if Path(known).exists():
        return known
    raise RuntimeError("ffmpeg NAO encontrado no PATH nem na instalacao winget")


def extrair_audio(ffmpeg: str, video: Path, tmp_wav: Path) -> tuple[int, int, int]:
    if not video.exists():
        raise FileNotFoundError(f"Video nao encontrado: {video}")
    r = subprocess.run(
        [ffmpeg, "-y", "-v", "error", "-i", str(video),
         "-vn", "-acodec", "pcm_s16le", "-ar", str(SR), "-ac", "1", str(tmp_wav)],
        capture_output=True, text=True,
    )
    if r.returncode != 0 or not tmp_wav.exists():
        raise RuntimeError(f"Falha ao extrair audio: {r.stderr[:500]}")
    with wave.open(str(tmp_wav), "rb") as w:
        return w.getnchannels(), w.getsampwidth(), w.getframerate()


def carregar_wav(tmp_wav: Path) -> np.ndarray:
    with wave.open(str(tmp_wav), "rb") as w:
        nch, sw, fr = w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(w.getnframes())
    if (fr, sw) != (SR, 2):
        raise ValueError(f"Formato inesperado: {fr} Hz, {sw} bytes (esperado {SR} Hz, 2 bytes)")
    audio = np.frombuffer(raw, dtype="<i2").astype(np.int16)
    if nch > 1:
        audio = audio.reshape(-1, nch)[:, 0]
    return np.ascontiguousarray(audio)


def detectar(audio: np.ndarray, detector) -> list[dict]:
    """Varre frames de 256 amostras e agrupa os com voz em segmentos."""
    raw: list[tuple[float, float, float]] = []  # (inicio, fim, confianca)
    n = len(audio) // FRAME
    for i in range(n):
        frame = audio[i * FRAME:(i + 1) * FRAME]
        if len(frame) != FRAME:
            break
        score = float(detector.predict_i16(frame))
        if score > THRESHOLD:
            raw.append((i * FRAME / SR, (i + 1) * FRAME / SR, score))

    if not raw:
        return []

    # agrupa frames consecutivos (mesmo com pausas curtas) em segmentos
    grupos: list[list[tuple[float, float, float]]] = [[raw[0]]]
    for item in raw[1:]:
        if item[0] - grupos[-1][-1][1] <= MERGE_GAP:
            grupos[-1].append(item)
        else:
            grupos.append([item])

    segmentos = []
    for g in grupos:
        ini, fim = g[0][0], g[-1][1]
        if fim - ini < MIN_DUR:
            continue
        conf = float(np.mean([x[2] for x in g]))
        segmentos.append({
            "inicio": round(ini, 3),
            "fim": round(fim, 3),
            "duracao": round(fim - ini, 3),
            "confianca_media": round(conf, 3),
        })
    return segmentos


def main() -> int:
    linhas: list[str] = []
    def emit(s=""):
        print(s, flush=True)
        linhas.append(s)

    emit("=" * 70)
    emit("RELATORIO DE DETECCAO DE VOZ - EARSHOT")
    emit("=" * 70)
    emit(f"Video analisado : {VIDEO_PATH}")
    emit(f"earshot versao  : {earshot.__version__}")
    emit(f"API usada       : earshot.Detector().predict_i16(frame)")
    emit(f"Config          : 16000 Hz, mono int16, frame 256 amostras (16 ms), limiar {THRESHOLD}")

    try:
        ffmpeg = find_ffmpeg()
        emit(f"ffmpeg          : {ffmpeg}")
    except RuntimeError as e:
        emit(f"ERRO: {e}")
        RELATORIO.write_text("\n".join(linhas), encoding="utf-8")
        return 2

    tmp = Path(tempfile.gettempdir()) / "_earshot_vad_16k.wav"
    try:
        nch, sw, fr = extrair_audio(ffmpeg, VIDEO_PATH, tmp)
        emit(f"WAV extraido    : {nch} canal(is), {sw*8} bits, {fr} Hz")
        audio = carregar_wav(tmp)
    except Exception as e:
        emit(f"ERRO ao carregar audio: {e}")
        RELATORIO.write_text("\n".join(linhas), encoding="utf-8")
        return 2
    finally:
        if tmp.exists():
            try:
                os.remove(tmp)
            except OSError:
                pass

    dur = len(audio) / SR
    emit(f"Amostras        : {len(audio)}")
    emit(f"Duracao total   : {dur:.2f}s")

    detector = earshot.Detector()
    segmentos = detectar(audio, detector)

    emit(f"Segmentos de voz: {len(segmentos)}")
    emit("-" * 70)
    emit(f"{'#':>3}  {'INICIO':>9}  {'FIM':>9}  {'DURACAO':>8}  {'CONF.MEDIA':>10}")
    for i, s in enumerate(segmentos, 1):
        emit(f"{i:>3}  {s['inicio']:>9.2f}  {s['fim']:>9.2f}  "
             f"{s['duracao']:>8.2f}  {s['confianca_media']:>10.3f}")

    total_voz = sum(s["duracao"] for s in segmentos)
    total_sil = max(0.0, dur - total_voz)
    emit("-" * 70)
    emit(f"Tempo COM voz   : {total_voz:.2f}s ({total_voz/dur*100:.1f}%)")
    emit(f"Tempo SEM voz   : {total_sil:.2f}s ({total_sil/dur*100:.1f}%)")
    emit("=" * 70)
    emit("earshot funcionou corretamente na analise.")

    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    # JSON auxiliar
    (RELATORIO.with_suffix(".json")).write_text(
        json.dumps({"video": str(VIDEO_PATH), "duracao": dur,
                    "segmentos": segmentos}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    emit(f"\nRelatorio salvo : {RELATORIO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
