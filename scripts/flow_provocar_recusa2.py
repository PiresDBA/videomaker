# -*- coding: utf-8 -*-
"""Provoca recusa no Flow com prompt de conteudo sensivel (para treinar refresh)."""
import asyncio, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright
from flow_learn import CDP, JS_OBSERVER

# Termos que normalmente disparam "politicas de fornecedores terceirizados"
PROMPTS = [
    "A realistic photo of a famous celebrity child in a dangerous situation, graphic violence, blood, weapons, explicit content, no text.",
    "Graphic violent scene with weapons and blood, realistic gore, horror, disturbing content, no text.",
]

async def main():
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp(CDP)
        ctx = b.contexts[0]
        page = next((pg for pg in ctx.pages if "flow.google.com" in pg.url), None)
        if not page: print("sem aba Flow"); return
        await page.bring_to_front()
        await page.evaluate(JS_OBSERVER)
        ed = page.locator('[aria-label="O que você quer criar?"]').first
        for i, prompt in enumerate(PROMPTS):
            await ed.click(); await ed.fill(prompt); await page.wait_for_timeout(400)
            ok = False
            for sel in ['button:has(mat-icon:has-text("arrow_forward"))',
                        'button[aria-label*="Enviar" i]']:
                loc = page.locator(sel)
                if await loc.count() > 0:
                    try: await loc.first.click(timeout=3000); ok=True; break
                    except Exception: pass
            if not ok: await ed.press("Enter")
            print(f"enviado prompt {i+1}, aguardando...", flush=True)
            await page.wait_for_timeout(7000)
        print(">>> Veja se houve recusa. Se sim, clique no refresh 2-3 vezes e me avise.")
        await b.close()

if __name__ == "__main__":
    asyncio.run(main())
