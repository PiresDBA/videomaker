# -*- coding: utf-8 -*-
"""Gera um video de 8s com logo do YouTube + joinha + SUBSCRIBE (modo Agente)."""
import asyncio
import sys
import time
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import flow_fetch as ff
from playwright.async_api import async_playwright

SAVE = Path(r"C:\videomaker\projects\a-caminha-nova-que-ninguem-quer-usar\assets\images\gemini\scenes\subscribe_8s.mp4")
PROMPT = (
    "Gere um vídeo animado de 8 segundos, 16:9, estilo desenho 3D para crianças. "
    "Numa sala aconchegante com uma caminha vermelha de corações dourados, os MESMOs dois cachorros: "
    "FRIDA = buldogue inglês fawn com colar de pérolas; LUNA = dachshund marrom com coleira dourada. "
    "Os dois sorriem e acenam. Do lado direito da tela aparece um botão vermelho de play do YouTube, "
    "uma mão azul de joinha (like) sobe animada com um pulinho, e a palavra SUBSCRIBE aparece "
    "em letras grandes e brancas. Cores vivas, luz dourada, final feliz e animado. "
    "Sem humanos, sem gatos, sem outros cachorros."
)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp("http://127.0.0.1:18800")
        pg = [x for x in b.contexts[0].pages if "flow.google.com" in x.url][0]
        await pg.wait_for_timeout(1500)
        antes = await pg.locator("video").count()
        print("videos antes:", antes, flush=True)

        ag = pg.locator('button:has-text("Agente")').first
        if await ag.count() and await ag.get_attribute("aria-pressed") != "true":
            await ag.click(timeout=5000)
            await pg.wait_for_timeout(700)
        print("agente:", await ag.get_attribute("aria-pressed") if await ag.count() else "ausente", flush=True)

        ed = pg.locator('div[role="textbox"].ProseMirror')
        await ed.last.click()
        await ed.last.fill(PROMPT)
        await pg.wait_for_timeout(1200)
        arrow = pg.locator('button:has(mat-icon:has-text("arrow_forward"))')
        warn = pg.locator('.prompt-warning-button')
        print("prompt:", len((await ed.last.inner_text()).strip()), "| arrow:", await arrow.count(), "| aviso:", await warn.count(), flush=True)
        if not await arrow.count():
            await pg.screenshot(path=r"C:\videomaker\subscribe_sem_botao.png")
            return
        await arrow.last.click(timeout=8000)
        print("ENVIADO", flush=True)

        t0 = time.time()
        url = None
        while time.time() - t0 < 540:
            await pg.wait_for_timeout(6000)
            n = await pg.locator("video").count()
            if n > antes:
                print("novo video na galeria", flush=True)
                await pg.wait_for_timeout(5000)
                vids = await pg.locator("video").evaluate_all("els=>els.map(e=>({src:(e.currentSrc||e.src||''),dur:e.duration,ready:e.readyState}))")
                for v in vids:
                    if v["ready"] >= 2 and v["dur"] > 0:
                        url = v["src"]
                if url:
                    break
            el = int(time.time() - t0)
            if el % 60 < 6:
                print("aguardando...", el, "s", flush=True)
        if url:
            data, ct = await ff.fetch_url(pg, url)
            if data and len(data) > 5000:
                SAVE.write_bytes(data)
                print("BAIXADO:", SAVE, SAVE.stat().st_size, flush=True)
        else:
            await pg.screenshot(path=r"C:\videomaker\subscribe_timeout.png")
            print("TIMEOUT", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
