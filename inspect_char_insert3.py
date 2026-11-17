import asyncio, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        page = [p for p in b.contexts[0].pages if 'flow.google.com' in p.url][0]
        # garantir painel personagens aberto
        add = page.locator('[aria-label*="Adicionar elementos" i]')
        if await add.count():
            await add.last.evaluate("(e)=>e.click()")
            await page.wait_for_timeout(800)
        pers = page.locator('span[matlistitemtitle]').filter(has_text='Personagens')
        if await pers.count():
            await pers.last.evaluate("(e)=>e.click()")
            await page.wait_for_timeout(1200)
        tiles = page.locator('.character-tile-name')
        print("tiles", await tiles.count(), flush=True)
        for i in range(await tiles.count()):
            name = await tiles.nth(i).inner_text()
            card = tiles.nth(i).locator('xpath=../../..')
            print("===", name, "===", flush=True)
            print((await card.evaluate("(e)=>e.outerHTML.slice(0,3000)")), flush=True)
asyncio.run(main())
