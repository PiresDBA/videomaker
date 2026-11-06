# -*- coding: utf-8 -*-
"""Testa vozes Edge-TTS: Brenda e Giovanna sem estilo (default) e Thalita com excited."""
import asyncio
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
OUT = PROJECT / "assets" / "audio" / "preview"
OUT.mkdir(parents=True, exist_ok=True)

CASES = [
    ("pt-BR-BrendaNeural", None, "+6%"),
    ("pt-BR-BrendaNeural", "excited", "+6%"),
    ("pt-BR-GiovannaNeural", None, "+6%"),
    ("pt-BR-ThalitaNeural", "excited", "+6%"),
    ("pt-BR-ThalitaNeural", "cheerful", "+12%"),
]
SAMPLE = ("Olha o formato desse cachorro! Parece um peluche que ganhou vida. "
          "E aí, você acredita que ele adora brincar com o dono? Hahaha!")

async def gen(voice, style, rate, out):
    import edge_tts
    if style:
        ssml = ('<speak version="1.0" xml:lang="pt-BR">'
                '<mstts:expressions style="%s">%s</mstts:expressions></speak>' % (style, SAMPLE))
    else:
        ssml = '<speak version="1.0" xml:lang="pt-BR">%s</speak>' % SAMPLE
    comm = edge_tts.Communicate(ssml, voice, rate=rate, pitch="+8Hz")
    await comm.save(str(out))

async def main():
    for voice, style, rate in CASES:
        tag = style or "default"
        out = OUT / ("preview_%s_%s.mp3" % (voice.replace("pt-BR-", ""), tag))
        try:
            await gen(voice, style, rate, out)
            print("ok", voice, tag, out.name, out.stat().st_size)
        except Exception as e:
            print("ERR", voice, tag, str(e)[:120])

asyncio.run(main())