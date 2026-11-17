import asyncio, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        page = b.contexts[0].pages[0]
        for name in ['Luna','Frida']:
            tile = page.locator('.character-tile-name').filter(has_text=name)
            print(name, await tile.count(), flush=True)
            if await tile.count():
                card = tile.first.locator('xpath=../..')
                print("  CARD", (await card.evaluate("(e)=>e.outerHTML.slice(0,1200)")), flush=True)
        ed = page.locator('[contenteditable="true"]').first
        before = await ed.inner_text()
        card = page.locator('.character-tile-name').filter(has_text='Frida').first.locator('xpath=../..')
        await card.evaluate("(e)=>e.click()")
        await page.wait_for_timeout(1200)
        after = await ed.inner_text()
        print("BEFORE", repr(before[:200]), flush=True)
        print("AFTER", repr(after[:300]), flush=True)
asyncio.run(main())
