# -*- coding: utf-8 -*-
r"""dublar_intro_v3.py - dublagem FINAL e sincronizada do intro.

Tempos EXATOS da voz original (whisper word-timestamps):
  beat 1: 0.80-2.94  "Hello there. Welcome to our home."
  beat 2: 3.56-5.62  "We are so glad you came to visit us."
  beat 3: 5.86-7.50  "Come on in and make yourself comfortable."

So PT e ES (o original ja e em ingles).

Tecnica:
 - TTS de cada frase traduzida
 - atempo agressivo (ate 3x) para caber EXATAMENTE no beat
 - adelay para posicionar no inicio REAL do beat (0.80, 3.56, 5.86)
 - atrim no fim do beat para nao "encalar" passando do tempo
 - amix das 3 frases
 - Audio ORIGINAL descartado (sem voz inglesa duplicada)
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
TMP = Path(r"C:\videomaker\_dublagem_tmp3")
TMP.mkdir(exist_ok=True)

# tempos REAIS (inicio e fim) da fala nos labios
BEATS = [(0.80, 2.94), (3.56, 5.62), (5.86, 7.50)]
# traducoes CURTAS (para caber rapido, igual o original)
FRASES = {
    "pt": ["Olá! Bem-vindos à nossa casa.",
           "Que alegria vocês estarem aqui.",
           "Entrem, fiquem à vontade!"],
    "es": ["¡Hola! Bienvenidos a nuestra casa.",
           "Qué alegría que estén aquí.",
           "¡Pasen, pónganse cómodos!"],
}
VOZES = {"pt": "pt-BR-ThalitaNeural", "es": "es-ES-ElviraNeural"}


def duracao(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


async def gerar_frase(texto, voz, out):
    await edge_tts.Communicate(texto, voz, rate="+12%").save(str(out))


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
            tempo = max(0.5, min(3.2, d / alvo))  # comprime agressivamente
            subprocess.run([FF, "-y", "-v", "error", "-i", str(raw),
                            "-af", f"atempo={tempo:.3f}", "-ar", "44100", "-ac", "1",
                            str(fit)], check=True)
            fits.append(fit)
            delay = int(t0 * 1000)
            # adelay posiciona a frase no tempo exato do labio; apad estende
            # ate 8s (senao amix duration=longest corta as frases com delay
            # maior e achata tudo para 0/3/6s).
            filtros.append(
                f"[{i}:a]adelay={delay}|{delay},apad=pad_dur=8.0,"
                f"atrim=0:8.0[f{i}]"
            )
            print(f"  beat {i}: {t0:.2f}-{t1:.2f} (alvo {alvo:.2f}s) | tts {d:.2f}s -> {tempo:.2f}x", flush=True)
        mix = "".join(f"[f{i}]" for i in range(len(fits)))
        filtro = ";".join(filtros) + ";" + mix + f"amix=inputs={len(fits)}:duration=longest:dropout_transition=0[voz]"
        cmd = [FF, "-y", "-v", "error"]
        for f in fits:
            cmd += ["-i", str(f)]
        voz = TMP / f"voz_{lang}.wav"
        cmd += ["-filter_complex", filtro, "-map", "[voz]", "-ar", "44100", "-ac", "2", str(voz)]
        subprocess.run(cmd, check=True)
        out = SCENES / f"intro_8s_{lang}.mp4"
        subprocess.run([FF, "-y", "-v", "error", "-i", str(SRC), "-i", str(voz),
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                        "-b:a", "192k", "-shortest", str(out)], check=True)
        print(f"  SALVO: {out.name} ({out.stat().st_size} bytes)", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
