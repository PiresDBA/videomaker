# -*- coding: utf-8 -*-
r"""dublar_intro_v2.py - CORRIGE a dublagem do intro (v2).

Problemas da v1:
 - misturava o audio ORIGINAL (com voz em ingles) -> voz dupla
 - concatenava silencios somando os tempos -> frases fora do lugar e espaços

v2:
 - DESCARTA o audio original por completo
 - cada frase TTS e ajustada com atempo para durar EXATAMENTE o beat
 - cada frase e posicionada no tempo exato com adelay (sobreposicao correta)
 - as 3 frases sao mixadas(num=3) numa trilha limpa
 - a trilha substitui o audio do MP4 (video/labios intactos)
"""
from __future__ import annotations
import asyncio, subprocess, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import edge_tts

FFDIR = Path(r"C:\videomaker\ffmpeg\bin")
FF = str(FFDIR / "ffmpeg.exe")
FFPROBE = str(FFDIR / "ffprobe.exe")
SCENES = Path(r"C:\videomaker\projects\a-caminha-nova-que-ninguem-quer-usar\assets\images\gemini\scenes")
SRC = SCENES / "intro_8s.mp4"
TMP = Path(r"C:\videomaker\_dublagem_tmp2")
TMP.mkdir(exist_ok=True)

BEATS = [(1.10, 3.60), (3.60, 5.86), (5.86, 8.04)]
FRASES = {
    "pt": ["Olá! Bem-vindos à nossa casa.",
           "Que alegria vocês estarem aqui com a gente.",
           "Entrem, fiquem à vontade!"],
    "en": ["Hello there, welcome to our home.",
           "We are so glad you came to visit us.",
           "Come on in and make yourself comfortable."],
    "es": ["¡Hola! Bienvenidos a nuestra casa.",
           "Qué alegría que estén aquí con nosotros.",
           "¡Pasen, pónganse cómodos!"],
}
VOZES = {"pt": "pt-BR-ThalitaNeural", "en": "en-US-AriaNeural", "es": "es-ES-ElviraNeural"}


def duracao(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


async def gerar_frase(texto, voz, out):
    comm = edge_tts.Communicate(texto, voz, rate="+6%")
    await comm.save(str(out))


async def main():
    for lang, frases in FRASES.items():
        print(f"\n=== {lang.upper()} ===", flush=True)
        fits, filtros = [], []
        for i, (frase, (t0, t1)) in enumerate(zip(frases, BEATS)):
            alvo = t1 - t0
            raw = TMP / f"{lang}_{i}_raw.mp3"
            fit = TMP / f"{lang}_{i}_fit.wav"
            await gerar_frase(frase, VOZES[lang], raw)
            d = duracao(raw)
            tempo = max(0.55, min(2.0, d / alvo))
            subprocess.run([FF, "-y", "-v", "error", "-i", str(raw),
                            "-af", f"atempo={tempo:.3f}", "-ar", "44100", "-ac", "1",
                            str(fit)], check=True)
            fits.append(fit)
            delay = int(t0 * 1000)
            filtros.append(f"[{i}:a]adelay={delay}|{delay},atrim=0:{t1:.3f}[f{i}]")
            print(f"  beat {i}: {t0:.2f}-{t1:.2f} | tts {d:.2f}s -> {tempo:.2f}x @ {t0}s", flush=True)
        # mixa as 3 frases na linha do tempo
        mix = ""
        for i in range(len(fits)):
            mix += f"[f{i}]"
        mix += f"amix=inputs={len(fits)}:duration=longest:dropout_transition=0[voz]"
        filtro = ";".join(filtros) + ";" + mix
        cmd = [FF, "-y", "-v", "error"]
        for f in fits:
            cmd += ["-i", str(f)]
        voz_final = TMP / f"voz_{lang}.wav"
        cmd += ["-filter_complex", filtro, "-map", "[voz]", "-ar", "44100", "-ac", "2",
                str(voz_final)]
        subprocess.run(cmd, check=True)
        # substitui o audio do MP4 (video intacto, SEM musica/voz original)
        out = SCENES / f"intro_8s_{lang}.mp4"
        subprocess.run([FF, "-y", "-v", "error", "-i", str(SRC), "-i", str(voz_final),
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                        "-b:a", "192k", "-shortest", str(out)], check=True)
        print(f"  SALVO: {out.name} ({out.stat().st_size} bytes)", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
