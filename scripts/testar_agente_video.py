# -*- coding: utf-8 -*-
"""Testa gerar o 3o video pelo MODO AGENTE do Flow (sem toggle de Video)."""
import asyncio
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import flow_fetch as ff

SAVE = Path(r"C:\videomaker\projects\a-caminha-nova-que-ninguem-quer-usar\assets\images\gemini\scenes\outro_8s.mp4")
PROMPT = (
    "Gere um vídeo animado de 8 segundos, 16:9, estilo desenho 3D para crianças. "
    "Use os MESMOs dois cachorros: FRIDA = buldogue inglês fawn grande com colar de pérolas; "
    "LUNA = dachshund marrom comprido com coleira dourada. "
    "Os dois sorriem e acenam para a câmera com confete colorido numa sala aconchegante "
    "com uma caminha vermelha de corações dourados. Luz dourada, zoom suave, final feliz. "
    "Sem humanos, sem gatos, sem outros cachorros, sem texto."
)


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp("http://127.0.0.1:18800")
        pg = [x for x in b.contexts[0].pages if "flow.google.com" in x.url][0]

        # Recarrega limpo
        await pg.goto("https://flow.google.com/project/d43a0933-5310-4951-b511-911f96a6bc22",
                      wait_until="domcontentloaded", timeout=60000)
        await pg.wait_for_timeout(4000)
        await ff.dismiss_ads_and_permissions(pg)
        await ff._dismiss_overlays(pg)
        await pg.wait_for_timeout(800)

        vids_antes = await pg.locator("video").count()
        print("videos antes:", vids_antes, flush=True)

        # Liga o modo AGENTE
        ag = pg.locator('button:has-text("Agente")').first
        print("botao Agente:", await ag.count(), flush=True)
        if await ag.count():
            pressed = await ag.get_attribute("aria-pressed")
            print("aria-pressed antes:", pressed, flush=True)
            if pressed != "true":
                await ag.click(timeout=5000)
                await pg.wait_for_timeout(900)
                print("AGENTE ligado, aria-pressed:", await ag.get_attribute("aria-pressed"), flush=True)

        # Preenche o prompt
        ed = pg.locator('div[role="textbox"].ProseMirror')
        await ed.last.click()
        await ed.last.fill(PROMPT)
        await pg.wait_for_timeout(1500)
        print("prompt:", len((await ed.last.inner_text()).strip()), "chars", flush=True)

        arrow = pg.locator('button:has(mat-icon:has-text("arrow_forward"))')
        warn = pg.locator('.prompt-warning-button')
        print("arrow:", await arrow.count(), "| aviso credito:", await warn.count(), flush=True)
        await pg.screenshot(path=r"C:\videomaker\agente_antes_enviar.png")

        if not await arrow.count():
            print("SEM BOTAO DE ENVIO — abortando", flush=True)
            return

        await arrow.last.click(timeout=8000)
        print("ENVIADO pelo modo Agente", flush=True)

        # Aguarda novo video na galeria
        t0 = time.time()
        novo_url = None
        while time.time() - t0 < 540:
            await pg.wait_for_timeout(6000)
            n = await pg.locator("video").count()
            if n > vids_antes:
                print("NOVO VIDEO detectado na galeria!", flush=True)
                await pg.wait_for_timeout(5000)
                vids = await pg.locator("video").evaluate_all(
                    "els => els.map(e => ({src:(e.currentSrc||e.src||''), dur:e.duration, ready:e.readyState}))")
                for v in vids:
                    if v["ready"] >= 2 and v["dur"] > 0:
                        novo_url = v["src"]
                if novo_url:
                    break
            el = int(time.time() - t0)
            if el % 60 < 6:
                print("aguardando...", el, "s | videos:", n, flush=True)

        if novo_url:
            data, ct = await ff.fetch_url(pg, novo_url)
            if data and len(data) > 5000:
                SAVE.write_bytes(data)
                print("BAIXADO:", SAVE, SAVE.stat().st_size, flush=True)
        else:
            print("Nao conseguiu baixar — screenshot final", flush=True)
            await pg.screenshot(path=r"C:\videomaker\agente_timeout.png")


if __name__ == "__main__":
    asyncio.run(main())
