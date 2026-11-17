import asyncio, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        page = [p for p in b.contexts[0].pages if 'flow.google.com' in p.url][0]
        # abrir menu 'Adicionar elementos' (chip 'add')
        add = page.locator('[aria-label*="Adicionar elementos" i]')
        print("add", await add.count(), flush=True)
        if await add.count():
            await add.last.evaluate("(e)=>e.click()")
            await page.wait_for_timeout(1200)
        # clicar em Personagens
        pers = page.locator('span[matlistitemtitle]').filter(has_text='Personagens')
        print("pers", await pers.count(), flush=True)
        if await pers.count():
            await pers.last.evaluate("(e)=>e.click()")
            await page.wait_for_timeout(1500)
        # agora procurar os tiles Frida/Luna
        tiles = page.locator('.character-tile-name')
        print("tiles", await tiles.count(), flush=True)
        for i in range(await tiles.count()):
            print("  tile", i, await tiles.nth(i).inner_text(), flush=True)
        # clicar numa tile e ver o que entra no prompt
        ed = page.locator('[contenteditable="true"]').first
        before = await ed.inner_text()
        card = page.locator('.character-tile-name').filter(has_text='Frida').first.locator('xpath=../..')
        print("card", await card.count(), flush=True)
        if await card.count():
            # clique normal (nao evaluate) para disparar handler do Angular
            try:
                await card.click(timeout=5000)
            except Exception as e:
                print("click err", str(e)[:80], flush=True)
            await page.wait_for_timeout(1500)
        after = await ed.inner_text()
        print("BEFORE", repr(before[:150]), flush=True)
        print("AFTER", repr(after[:300]), flush=True)
asyncio.run(main())
