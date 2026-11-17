# -*- coding: utf-8 -*-
"""Baixa todos os videos da galeria do Flow que ainda nao estao salvos."""
import asyncio, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import flow_fetch as ff
from playwright.async_api import async_playwright

DIR = Path(r"C:\videomaker\projects\a-caminha-nova-que-ninguem-quer-usar\assets\images\gemini\scenes")

async def main():
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp("http://127.0.0.1:18800")
        pg = [x for x in b.contexts[0].pages if "flow.google.com" in x.url][0]
        await pg.wait_for_timeout(1500)
        vids = await pg.locator("video").evaluate_all("els=>els.map(e=>({src:(e.currentSrc||e.src||''),dur:e.duration,ready:e.readyState}))")
        print("videos na galeria:", len(vids), flush=True)
        for i, v in enumerate(vids):
            print(i, "dur", round(v["dur"], 3), "ready", v["ready"], flush=True)
        # salvos: pega os que nao tem arquivo ainda (por ordem: 1=outro, 2=subscribe)
        nomes = ["resgatado_1.mp4", "resgatado_2.mp4", "resgatado_3.mp4", "resgatado_4.mp4"]
        for i, v in enumerate(vids):
            if not v["src"] or v["ready"] < 2:
                continue
            data, ct = await ff.fetch_url(pg, v["src"])
            if data and len(data) > 5000:
                p_out = DIR / nomes[i] if i < len(nomes) else DIR / f"resgatado_{i}.mp4"
                p_out.write_bytes(data)
                print("SALVO:", p_out.name, p_out.stat().st_size, flush=True)

if __name__ == "__main__":
    asyncio.run(main())
