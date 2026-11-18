# -*- coding: utf-8 -*-
"""analisar_earshot.py - Deteccao de segmentos de voz (VAD) com earshot 1.2.2.

A binding Python do earshot 1.2.2 expoe apenas Detector (predict_i16 /
predict_f32 / reset), NAO expoe earshot.segments() nem SegmenterOptions.
Por isso replicamos a logica do segmentador Rust (src/segments.rs) com os
parametros default:
    smoothing_factor = 0.4
    attack_threshold = 0.6
    decay_threshold  = 0.5
    preroll_frames   = 5
    min_duration     = 6   (frames => 96 ms)
    start_delay      = 2
    end_delay        = 4
Cada frame = 256 amostras @ 16 kHz (16 ms), mono PCM int16.
"""
from __future__ import annotations
import os
import sys
import wave
import shutil
import tempfile
import subprocess
from pathlib import Path

import numpy as np
import earshot

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------- parametros
VIDEO_PATH = Path(
    r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia"
    r"\output\e-se-os-cachorros-pudessem-falar-por-um-dia_pt.mp4"
)
RELATORIO = Path(r"C:\videomaker\relatorio_earshot.txt")

SAMPLE_RATE = 16000
FRAME_SIZE = 256  # 16 ms @ 16 kHz
SMOOTHING = 0.4
ATTACK = 0.6
DECAY = 0.5
PREROLL = 5
MIN_DURATION = 6
START_DELAY = 2
END_DELAY = 4


def encontrar_ffmpeg() -> str:
    """Localiza o ffmpeg no PATH ou em caminhos conhecidos."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    candidatos = [
        r"C:\Users\Pires\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe",
        r"C:\OpenMontage\ffmpeg\bin\ffmpeg.exe",
        r"C:\videomaker\ffmpeg\bin\ffmpeg.exe",
    ]
    for c in candidatos:
        if Path(c).is_file():
            return c
    raise RuntimeError("ffmpeg NAO encontrado no PATH nem nos caminhos conhecidos.")


def extrair_audio_wav(video: Path, wav: Path) -> None:
    """Converte o audio do video para WAV mono 16 kHz PCM int16."""
    ffmpeg = encontrar_ffmpeg()
    cmd = [ffmpeg, "-y", "-v", "error", "-i", str(video),
           "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE),
           "-acodec", "pcm_s16le", str(wav)]
    subprocess.run(cmd, check=True)


def carregar_wav(wav: Path) -> tuple[np.ndarray, int, int, int]:
    """Le o WAV e garante formato mono/int16/16 kHz. Retorna (audio, sr, canais, width)."""
    with wave.open(str(wav), "rb") as w:
        canais = w.getnchannels()
        width = w.getsampwidth()
        sr = w.getframerate()
        nframes = w.getnframes()
        raw = w.readframes(nframes)
    if width != 2:
        raise RuntimeError(f"WAV com sampwidth={width} bytes; esperado 2 (int16).")
    audio = np.frombuffer(raw, dtype="<i2")  # little-endian int16
    if canais > 1:
        audio = audio.reshape(-1, canais)[:, 0]  # canal esquerdo
    if sr != SAMPLE_RATE:
        raise RuntimeError(f"Sample rate {sr} != {SAMPLE_RATE}.")
    return np.ascontiguousarray(audio), sr, canais, width


def detectar_segmentos(audio: np.ndarray) -> list[dict]:
    """Roda o earshot frame-a-frame e aplica a maquina de estados do
    segmentador Rust. Retorna lista de segmentos com confianca media."""
    total_frames = len(audio) // FRAME_SIZE
    detector = earshot.Detector()

    smoothed = 0.0
    n_frames = 0
    state = "silence"          # silence | pending | voice
    voice_frames = 0
    seg_start = 0
    silence_frames = 0
    segmentos: list[dict] = []

    # acumuladores de confianca por segmento (media do score bruto)
    conf_sum = 0.0
    conf_count = 0

    def fechar(start_f: int, end_f: int) -> dict:
        return {
            "inicio": start_f * FRAME_SIZE / SAMPLE_RATE,
            "fim": end_f * FRAME_SIZE / SAMPLE_RATE,
            "duracao": (end_f - start_f) * FRAME_SIZE / SAMPLE_RATE,
            "confianca": (conf_sum / conf_count) if conf_count else 0.0,
        }

    for fi in range(total_frames):
        frame = audio[fi * FRAME_SIZE:(fi + 1) * FRAME_SIZE]
        if len(frame) != FRAME_SIZE:
            break
        raw = float(detector.predict_i16(frame))
        smoothed = SMOOTHING * smoothed + (1.0 - SMOOTHING) * raw

        is_voice = (smoothed >= ATTACK) if state in ("silence", "pending") \
                   else (smoothed >= DECAY)

        if state == "silence":
            if is_voice:
                state = "pending"
                voice_frames = 1
        elif state == "pending":
            if is_voice:
                voice_frames += 1
                conf_sum += raw
                conf_count += 1
                if voice_frames >= START_DELAY:
                    seg_start = max(0, n_frames + voice_frames - PREROLL)
                    state = "voice"
                    silence_frames = 0
            else:
                state = "silence"
                conf_sum = 0.0
                conf_count = 0
        else:  # voice
            if is_voice:
                silence_frames = 0
                conf_sum += raw
                conf_count += 1
            else:
                silence_frames += 1

            if silence_frames >= END_DELAY:
                if n_frames - seg_start >= MIN_DURATION:
                    segmentos.append(fechar(seg_start, n_frames))
                state = "silence"
                conf_sum = 0.0
                conf_count = 0

        n_frames += 1

    # segmento ainda aberto no fim do audio
    if state == "voice" and n_frames - seg_start >= MIN_DURATION:
        segmentos.append(fechar(seg_start, n_frames))

    return segmentos


def main() -> None:
    linhas: list[str] = []
    wav_tmp = None
    try:
        if not VIDEO_PATH.is_file():
            raise FileNotFoundError(f"Video nao encontrado: {VIDEO_PATH}")

        print("Extraindo audio para WAV 16 kHz mono int16...")
        fd, wav_tmp = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        extrair_audio_wav(VIDEO_PATH, Path(wav_tmp))

        print("Carregando WAV...")
        audio, sr, canais, width = carregar_wav(Path(wav_tmp))
        duracao = len(audio) / sr
        print(f"Audio: {sr} Hz, {canais} canal(is), {width*8}-bit, "
              f"{len(audio)} amostras, {duracao:.2f}s")

        print("Detectando voz com earshot (frame-a-frame, 256 amostras)...")
        segmentos = detectar_segmentos(audio)

        tempo_voz = sum(s["duracao"] for s in segmentos)
        # evita sobrepor segmentos (a maquina nao deve gerar sobreposicao)
        tempo_silencio = max(0.0, duracao - tempo_voz)
        pct_voz = (tempo_voz / duracao * 100.0) if duracao else 0.0

        linhas.append("=" * 78)
        linhas.append("RELATORIO DE DETECCAO DE VOZ - EARSHOT 1.2.2")
        linhas.append("=" * 78)
        linhas.append(f"Video analisado      : {VIDEO_PATH}")
        linhas.append(f"Duracao total audio  : {duracao:.2f}s")
        linhas.append(f"Formato              : {sr} Hz, mono, int16, {FRAME_SIZE} amostras/frame")
        linhas.append(f"Parametros           : smoothing=0.4 attack=0.6 decay=0.5 "
                      f"min_dur=6f end_delay=4f")
        linhas.append(f"Segmentos de voz     : {len(segmentos)}")
        linhas.append(f"Tempo com voz        : {tempo_voz:.2f}s ({pct_voz:.1f}%)")
        linhas.append(f"Tempo sem voz        : {tempo_silencio:.2f}s ({100-pct_voz:.1f}%)")
        linhas.append("-" * 78)
        linhas.append(f"{'#':>4}  {'INICIO':>9}  {'FIM':>9}  {'DURACAO':>9}  {'CONF.':>7}")
        linhas.append("-" * 78)
        for i, s in enumerate(segmentos, 1):
            linhas.append(f"{i:>4}  {s['inicio']:>9.2f}  {s['fim']:>9.2f}  "
                          f"{s['duracao']:>9.2f}  {s['confianca']:>7.3f}")
        linhas.append("=" * 78)
        linhas.append(f"earshot versao: {getattr(earshot, '__version__', '1.2.2')}")

        relatorio = "\n".join(linhas)
        RELATORIO.write_text(relatorio, encoding="utf-8")
        print(relatorio)
        print(f"\nRelatorio salvo em: {RELATORIO}")

    except FileNotFoundError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        raise
    except subprocess.CalledProcessError as e:
        print(f"ERRO ao extrair audio com ffmpeg (codigo {e.returncode}).", file=sys.stderr)
        raise
    except wave.Error as e:
        print(f"ERRO: arquivo WAV corrompido ou invalido: {e}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"ERRO inesperado: {type(e).__name__}: {e}", file=sys.stderr)
        raise
    finally:
        if wav_tmp:
            try:
                os.remove(wav_tmp)
            except OSError:
                pass


if __name__ == "__main__":
    main()
