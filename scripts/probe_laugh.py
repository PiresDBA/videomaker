# -*- coding: utf-8 -*-
"""Testa como o Edge-TTS (Thalita excited) renderiza 'Hahaha!' e frases com risada."""
import asyncio
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
OUT = PROJECT / "assets" / "audio" / "preview"
OUT.mkdir(parents=True, exist_ok=True)

CASES = [
    ("normal", "Olha o formato desse cachorro, ele e um peluche com vida."),
    ("hahaha", "Olha o formato desse cachorro, ele e um peluche com vida. Hahaha!"),
    ("risada_ssml", '<speak version="1.0" xml:lang="pt-BR">'
                     '<mstts:expressions style="excited">'
                     'Olha o formato desse cachorro, ele e um peluche com vida. '
                     'Hahaha! '
                     'Que thing incrivel, nao e?'
                     '</mstts:expressions></speak>'),
    ("break", '<speak version="1.0" xml:lang="pt-BR">'
              '<mstts:expressions style="excited">'
              'Olha o formato desse cachorro, ele e um peluche com vida.'
              '<break time="400ms"/>Hahaha!'
              '<break time="300ms"/>Que coisa incrivel, nao e?'
              '</mstts:expressions></speak>'),
]

async def gen(text, voice, rate, pitch, out):
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await comm.save(str(out))

async def main():
    for tag, text in CASES:
        out = OUT / ("laugh_%s.mp3" % tag)
        try:
            await gen(text, "pt-BR-ThalitaNeural", "+4%", "+8Hz", out)
            print("ok", tag, out.name, out.stat().st_size)
        except Exception as e:
            print("ERR", tag, str(e)[:120])

asyncio.run(main())