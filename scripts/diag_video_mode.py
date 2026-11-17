# -*- coding: utf-8 -*-
"""Diagnostico: alterna para VIDEO e inspeciona o estado do botao de envio."""
import asyncio
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import flow_fetch as ff

PROMPT = (
    "An 8-second cheerful animated video, 16:9, 3D cartoon. "
    "The SAME two dogs: FRIDA = big fawn bulldog with pearl necklace; "
    "LUNA = long brown dachshund with gold collar. Both smile and wave at the camera "
    "with confetti in a cozy living room with a red dog bed with golden hearts. "
    "No humans, no cats, no other dogs, no text."
)


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp("http://127.0.0.1:18800")
        pg = [x for x in b.contexts[0].pages if "flow.google.com" in x.url][0]
        await pg.wait_for_timeout(1500)

        # Painel pode ja estar aberto (usuario clicou). Fecha e reabre de forma controlada.
        await pg.keyboard.press("Escape")
        await pg.wait_for_timeout(700)
        trig = await ff._loc_first_visible(pg, ff.SETTINGS_TRIGGER_SELECTORS, timeout_ms=6000)
        print("trigger:", await trig.count() if trig else 0, flush=True)
        if trig:
            try:
                await trig.click(timeout=5000)
            except Exception:
                await trig.evaluate("(e) => e.click()")
            await pg.wait_for_timeout(900)

        toggles = await pg.locator("mat-button-toggle").all_inner_texts()
        print("TOGGLES:", [t.strip() for t in toggles if t.strip()][:18], flush=True)

        # Seleciona VIDEO (tenta com acento e sem)
        ok = False
        for label in ("Vídeo", "Video", "videocam\nVídeo", "videocam\nVideo"):
            cand = pg.locator(f'mat-button-toggle:has-text("{label}")').first
            if await cand.count():
                if not await ff._toggle_checked(cand):
                    try:
                        await cand.locator("button").first.click(timeout=4000)
                    except Exception:
                        await cand.evaluate("(e) => e.click()")
                print("modo VIDEO selecionado via:", label, flush=True)
                ok = True
                break
        if not ok:
            print("FALHA: toggle VIDEO nao encontrado", flush=True)
            await pg.screenshot(path=r"C:\videomaker\diag_video_fail.png")
            return

        await pg.wait_for_timeout(800)
        # Texto do painel (creditos)
        painel = await pg.locator("body").inner_text()
        i = painel.find("créditos")
        print("TRECHO CREDITOS:", painel[max(0, i-100):i+220].replace("\n", " | "), flush=True)

        await pg.keyboard.press("Escape")
        await pg.wait_for_timeout(700)

        ed = pg.locator('div[role="textbox"].ProseMirror')
        await ed.last.click()
        await ed.last.fill(PROMPT)
        await pg.wait_for_timeout(1500)

        arrow = pg.locator('button:has(mat-icon:has-text("arrow_forward"))')
        warn = pg.locator('.prompt-warning-button')
        print("RESULTADO -> arrow:", await arrow.count(), "| aviso:", await warn.count(), flush=True)
        if await warn.count():
            print("ARIA:", await warn.first.get_attribute("aria-label"), flush=True)
            await warn.first.click(timeout=5000)
            await pg.wait_for_timeout(1200)
            await pg.screenshot(path=r"C:\videomaker\diag_video_aviso.png")
        if await arrow.count():
            print("Enviando...", flush=True)
            await arrow.last.click(timeout=8000)
            print("ENVIADO!", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
