# -*- coding: utf-8 -*-
r"""dublar_intro.py - cria 3 versões do intro_8s.mp4 dubladas em PT/EN/ES.

Usa as mesmas 3 frases com timestamps da transcricao (intro_transcricao.json):
  [1.10-3.60] [3.60-5.86] [5.86-8.04]
Gera TTS (Edge-TTS) para cada frase em cada idioma, ajusta a duracao para
bater com o tempo original (atempo), monta a trilha completa e substitui o
audio do MP4 (video intacto - os labios permanecem).

Saida: assets/images/gemini/scenes/intro_8s_{pt,en,es}.mp4
"""
from __future__ import annotations
import asyncio, json, subprocess, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import edge_tts

FFDIR = Path(r"C:\videomaker\ffmpeg\bin")
FF = str(FFDIR / "ffmpeg.exe")
FFPROBE = str(FFDIR / "ffprobe.exe")
SCENES = Path(r"C:\videomaker\projects\a-caminha-nova-que-ninguem-quer-usar\assets\images\gemini\scenes")
SRC = SCENES / "intro_8s.mp4"
TMP = Path(r"C:\videomaker\_dublagem_tmp")
TMP.mkdir(exist_ok=True)

# Timestamps dos 3 beats (da transcricao)
BEATS = [(1.10, 3.60), (3.60, 5.86), (5.86, 8.04)]
# Frases traduzidas (mantidas curtas para caber no tempo dos labios)
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
RATE = {"pt": "+8%", "en": "+8%", "es": "+8%"}


def duracao(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


async def gerar_frase(texto, voz, rate, out):
    comm = edge_tts.Communicate(texto, voz, rate=rate)
    await comm.save(str(out))


async def main():
    for lang, frases in FRASES.items():
        print(f"\n=== {lang.upper()} ===", flush=True)
        trilhas = []
        for i, (frase, (t0, t1)) in enumerate(zip(frases, BEATS)):
            alvo = t1 - t0
            raw = TMP / f"{lang}_{i}_raw.mp3"
            fit = TMP / f"{lang}_{i}.wav"
            await gerar_frase(frase, VOZES[lang], RATE[lang], raw)
            d = duracao(raw)
            # ajusta velocidade para caber no tempo do beat
            tempo = max(0.7, min(1.4, d / alvo))
            subprocess.run([FF, "-y", "-v", "error", "-i", str(raw),
                            "-af", f"atempo={tempo:.3f}", "-ar", "44100", "-ac", "2",
                            str(fit)], check=True)
            print(f"  beat {i}: {t0:.2f}-{t1:.2f} (alvo {alvo:.2f}s) | tts {d:.2f}s -> {tempo:.2f}x", flush=True)
            # cria segmento com silencio ate t0 + frase
            seg = TMP / f"{lang}_{i}_seg.wav"
            sil = TMP / f"sil_{i}.wav"
            subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                            "anullsrc=r=44100:cl=stereo", "-t", f"{t0:.3f}", str(sil)], check=True)
            subprocess.run([FF, "-y", "-v", "error", "-i", str(sil), "-i", str(fit),
                            "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1", str(seg)], check=True)
            trilhas.append(seg)
        # concatena as 3 trilhas + silencio final ate 8s
        lista = TMP / f"lista_{lang}.txt"
        linhas = [f"file '{p.as_posix()}'" for p in trilhas]
        sil_fim = TMP / "sil_fim.wav"
        subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                        "anullsrc=r=44100:cl=stereo", "-t", "0.3", str(sil_fim)], check=True)
        linhas.append(f"file '{sil_fim.as_posix()}'")
        lista.write_text("\n".join(linhas) + "\n", encoding="utf-8")
        voz_final = TMP / f"voz_{lang}.wav"
        subprocess.run([FF, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i",
                        str(lista), "-ar", "44100", "-ac", "2", str(voz_final)], check=True)
        # mixa com a musica original do intro (volume baixo) + voz
        # (o audio original tem musica; abaixamos para a voz se destacar)
        out = SCENES / f"intro_8s_{lang}.mp4"
        filtro = ("[1:a]volume=0.25[bgm];[0:a][bgm]amix=inputs=2:duration=first:"
                  "dropout_transition=0:weights=1 0.25[mix];[mix]loudnorm=I=-14[out]")
        subprocess.run([FF, "-y", "-v", "error", "-i", str(voz_final), "-i", str(SRC),
                        "-filter_complex", filtro, "-map", "1:v", "-map", "[out]",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                        str(out)], check=True)
        print(f"  SALVO: {out.name} ({out.stat().st_size} bytes)", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
