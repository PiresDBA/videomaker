# -*- coding: utf-8 -*-
import asyncio, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import flow_fetch as ff
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp("http://127.0.0.1:18800")
        pg = [x for x in b.contexts[0].pages if "flow.google.com" in x.url][0]
        trig = await ff._loc_first_visible(pg, ff.SETTINGS_TRIGGER_SELECTORS, timeout_ms=6000)
        print("trigger:", bool(trig), flush=True)
        if trig:
            try:
                await trig.click(timeout=5000)
            except Exception:
                await trig.evaluate("(e) => e.click()")
        await pg.wait_for_timeout(1200)
        t = await pg.locator("body").inner_text()
        i = t.find("créditos")
        print("CREDITOS:", t[max(0,i-160):i+260].replace("\n", " | "), flush=True)
        print("TOGGLES:", [x.strip() for x in await pg.locator("mat-button-toggle").all_inner_texts() if x.strip()][:20], flush=True)
        await pg.screenshot(path=r"C:\videomaker\diag_modelo_config.png")
        await pg.keyboard.press("Escape")

if __name__ == "__main__":
    asyncio.run(main())
