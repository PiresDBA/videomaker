# -*- coding: utf-8 -*-
"""flow_provocar_recusa.py - Envia um prompt que o Flow recusa (para treinar
o clique de 'gerar de novo'/refresh no modo guiado)."""
import asyncio, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright
from flow_learn import CDP, JS_OBSERVER

PROMPT = ("A cute bulldog dog in 3D Pixar Disney style, exact replica of a famous "
          "movie character, realistic fur, cinematic lighting, no text. Generate "
          "one static image.")

async def main():
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp(CDP)
        ctx = b.contexts[0]
        page = next((pg for pg in ctx.pages if "flow.google.com" in pg.url), None)
        if not page:
            print("sem aba Flow"); return
        await page.bring_to_front()
        # reinstala observador (por seguranca)
        await page.evaluate(JS_OBSERVER)
        ed = page.locator('[aria-label="O que você quer criar?"]').first
        await ed.click()
        await ed.fill(PROMPT)
        await page.wait_for_timeout(500)
        # botao enviar (seta) - tenta varios seletores
        enviado = False
        for sel in ['button[aria-label*="Enviar" i]', 'button:has(mat-icon:has-text("arrow_forward"))',
                    'button:has(mat-icon:has-text("send"))', '[aria-label="Enviar prompt"]']:
            try:
                loc = page.locator(sel)
                if await loc.count() > 0:
                    await loc.first.click(timeout=3000)
                    enviado = True
                    print("enviado via", sel); break
            except Exception:
                pass
        if not enviado:
            # Enter no campo
            await ed.press("Enter")
            print("enviado via Enter")
        await page.wait_for_timeout(6000)
        print(">>> Aguarde a recusa aparecer na tela, clique no refresh 2-3 vezes e me avise.")
        await b.close()

if __name__ == "__main__":
    asyncio.run(main())
