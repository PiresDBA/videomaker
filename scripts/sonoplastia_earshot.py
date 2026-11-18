# -*- coding: utf-8 -*-
"""sonoplastia_earshot.py - Sonoplastia com o BANCO DE 252 SONS do earshot
(Leonxlnx/earshot). Sons renderizados por ID (pure DSP, sem modelos) e mixados
nos tempos exatos da narração (regra de ouro §65: som = cena = fala).

Inclui:
  - Foley pontual casado com a palavra falada
  - CAMADA AMBIENTE de passarinhos na pracinha (baixo volume, varios pontos)
  - Borboleta (hover_tick/air = asa batendo + shimmer)
  - Shimmer de estrelinhas/poeirinha
  - Subscribe/campainha no final

Cache: cada ID e renderizado UMA vez (performance).
Saida: assets/audio/final_mix_sonoplastia_earshot.m4a
"""
from __future__ import annotations
import sys, subprocess, shutil
from pathlib import Path
import numpy as np
import soundfile as sf
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, r"C:\videomaker\earshot-sfx")
from earshot.forge import bank

FF = shutil.which("ffmpeg") or r"C:\Users\Pires\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
P = Path(r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia")
AUD = P / "assets/audio"
MIX_BASE = AUD / "final_mix.m4a"
OUT = AUD / "final_mix_sonoplastia_earshot.m4a"
SR = 44100

# (tempo video, id, ganho, motivo)
CUES = [
    # ABERTURA
    (0.30, "shimmer/m2", 0.45, "abertura: brilho"),
    # MINUTO 1 - manha na pracinha, passarinhos ambiente
    (30.90, "pro_pop/chirp", 0.22, "PASSARINHO ambiente 'manha cedinho na pracinha'"),
    (34.80, "whoosh_fast/whistle", 0.20, "PASSARINHO 'sol nascendo'"),
    (49.50, "hover_tick/air", 0.28, "BORBOLETAS 'correr atras de borboletas' - asinhas"),
    (52.00, "pro_shimmer/m1", 0.25, "borboletas - sparkle"),
    (55.40, "shimmer/m1", 0.45, "'algo magico... no ar'"),
    (61.77, "shimmer/m4", 0.70, "POEIRINHA DOURADA BRILHANTE - estrelinhas"),
    (63.17, "shimmer/m5", 0.55, "'brilhante, futuava por toda parte'"),
    (67.59, "pro_impact/air", 0.90, "ESPIRRO FORTE da Frida"),
    (71.00, "pro_pop/boop", 0.45, "'abriu a boca e disse bom dia'"),
    (76.30, "pro_tap/knock", 0.40, "'Luninha caiu de bumbum na grama'"),
    # MINUTO 1-2
    (93.30, "pro_pop/boop", 0.45, "'mexeu a boquinha e falou de novo'"),
    (98.60, "pro_pop/chirp", 0.30, "'começou a latir de alegria'"),
    (109.01, "typing_key/crisp", 0.45, "'biscoito favorito' - crocante"),
    (118.40, "swish/soft", 0.30, "VENTO 'vento soprava suavemente'"),
    (124.90, "pro_pop/chirp", 0.25, "PASSARINHO 'dia barulhento'"),
    (131.53, "whoosh_fast/whistle", 0.40, "PASSARINHOS nas arvores"),
    (137.80, "swish/flick", 0.30, "'ajeitou as dobrinhas do rostinho'"),
    # MINUTO 2-3
    (156.60, "pro_pop/boop", 0.35, "'ideia genial'"),
    (167.00, "tap/soft", 0.30, "PATA 'caminharam lado a lado'"),
    (179.10, "pro_pop/boop", 0.35, "'gato Pingo' apareceu"),
    (193.22, "pro_pop/bloop", 0.65, "BOLINHA 'correr atras de uma bolinha' - quique"),
    (203.39, "pro_pop/chirp", 0.45, "RISADINHA gostosa do gato"),
    # MINUTO 3-4 - passarinho minhoca, patos
    (218.70, "pro_pop/chirp", 0.35, "PASSARINHO 'minhoca mais saborosa'"),
    (238.70, "tap/soft", 0.30, "PATA 'correndo com patinhas firmes'"),
    (256.40, "swish/soft", 0.25, "sol subindo / grama"),
    # MINUTO 4-5 - carros, gargalhada, pombo, borboleta
    (271.10, "whoosh_big/gust", 0.45, "CARROS VERMELHOS passando"),
    (278.40, "whoosh_big/jet", 0.40, "CARROS - passada"),
    (286.70, "whoosh_fast/whistle", 0.35, "RISADA da Frida - assobio alegre"),
    (298.80, "pro_pop/chirp", 0.30, "POMBO rechonchudo"),
    (330.00, "hover_tick/air", 0.35, "BORBOLETA AZUL na margarida - asinhas"),
    (330.50, "pro_shimmer/m2", 0.30, "borboleta - sparkle azul"),
    (335.90, "hover_tick/high", 0.30, "'conversar com a borboleta' - asinhas"),
    (341.70, "shimmer/m3", 0.30, "'apenas dançavam no vento' - brilho"),
    (360.20, "pro_pop/chirp", 0.25, "PASSARINHO 'voz ecoava entre arvores'"),
    # MINUTO 6-7 - fonte, agua, formiga
    (392.40, "drip/drop", 0.35, "AGUA 'fonte de pedra' - pingo"),
    (427.80, "drip/bubble", 0.35, "AGUA caindo na pedra - musica gostosa"),
    (455.28, "shimmer/m4", 0.25, "olhinhos brilhantes"),
    (473.20, "tap/soft", 0.25, "FORMIGUINHA caminhando na grama"),
    # MINUTO 8-10 - comida, joaninhas, cantoria
    (533.21, "typing_key/light", 0.40, "BISCOITOS crocantes de mel"),
    (544.85, "pro_impact/rumble", 0.50, "BARRIGA roncando alto"),
    (557.90, "shimmer/m2", 0.30, "JOANINHAS vermelhinhas - brilho"),
    (565.60, "pro_shimmer/m3", 0.30, "'falar baixinho com visitantes pontilhadas'"),
    (603.30, "mallet/glock", 0.40, "CANTANDO musica engraçada - xilofone"),
    (611.20, "mallet/flourish", 0.45, "cantoria - flourish"),
    (619.17, "whoosh_fast/whistle", 0.50, "OSSINHOS VOADORES caindo do ceu - assobio"),
    (623.40, "pro_tap/knock", 0.35, "ossinhos caindo na grama - plop"),
    (630.01, "whoosh_fast/crisp", 0.40, "PASSEINHOS aplaudindo com piados"),
    (650.00, "swish/soft", 0.25, "descanso debaixo da arvore"),
    # MINUTO 10-13 - abraco, bocejo, estrelas
    (665.30, "mallet/pluck", 0.40, "ABRACO APERTADO - carinho"),
    (763.99, "swish/soft", 0.35, "BOCEJO enorme - sopro"),
    (769.80, "shimmer/m0", 0.55, "POEIRINHA MAGICA subindo ao ceu"),
    (787.60, "swish/flick", 0.30, "'magia sumindo'"),
    (806.27, "pro_pop/bloop", 0.45, "LATIDINHO mansinho da Frida"),
    (847.88, "shimmer/m5", 0.55, "ESTRELAS BRILHANTES no ceu"),
    (848.52, "shimmer/m2", 0.50, "ceu estrelado - sparkle"),
    (863.80, "mallet/pluck", 0.30, "'sonhar com novas brincadeiras'"),
    # MINUTO 14-15 - final
    (907.40, "shimmer/m1", 0.30, "'termina nossa aventura'"),
    (915.19, "mallet/flourish", 0.70, "CONFETE - fanfarra"),
    (929.90, "fit/bell/small_bell", 0.80, "INSCREVA-SE - campainha"),
    (930.40, "pro_notify/ding_2045", 0.60, "CTA like/subscribe"),
]


def render_cue(sid, cache):
    if sid in cache:
        return cache[sid]
    y, meta = bank.render(sid)
    if getattr(y, "ndim", 1) == 2:
        y = y.mean(axis=1)
    if meta.get("sr", SR) != SR:
        n = int(len(y) * SR / meta["sr"])
        y = np.interp(np.linspace(0, len(y), n), np.arange(len(y)), y)
    y = y.astype(np.float32)
    cache[sid] = y
    return y


def main():
    print(f"banco earshot: {bank.VERSION} ({len(bank.list())} sons), {len(CUES)} cues", flush=True)
    subprocess.run([FF, "-y", "-v", "error", "-i", str(MIX_BASE),
                    "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le",
                    str(AUD / "_base_tmp.wav")], check=True)
    base, _ = sf.read(AUD / "_base_tmp.wav", dtype="float32")
    print(f"mix base: {len(base)/SR:.2f}s", flush=True)

    out = base.copy()
    cache = {}
    for k, (t_cue, sid, gain, motivo) in enumerate(CUES):
        i0 = int(t_cue * SR)
        if i0 >= len(out):
            continue
        try:
            y = render_cue(sid, cache)
        except Exception as e:
            print(f"  ERRO {sid}: {e}", flush=True)
            continue
        n = min(len(y), len(out) - i0)
        out[i0:i0+n] += y[:n] * gain
        if (k+1) % 10 == 0 or k == 0:
            print(f"  {k+1}/{len(CUES)} cues processados", flush=True)

    peak = np.max(np.abs(out))
    if peak > 0.99:
        out = out / peak * 0.99
    tmp_wav = AUD / "_sono_final_tmp.wav"
    sf.write(tmp_wav, out.astype(np.float32), SR)
    subprocess.run([FF, "-y", "-v", "error", "-i", str(tmp_wav),
                    "-c:a", "aac", "-b:a", "192k", str(OUT)], check=True)
    tmp_wav.unlink(missing_ok=True)
    (AUD / "_base_tmp.wav").unlink(missing_ok=True)
    print(f"OK: {OUT} ({OUT.stat().st_size} bytes)", flush=True)


if __name__ == "__main__":
    main()
