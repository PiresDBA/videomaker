import asyncio, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        page = [p for p in b.contexts[0].pages if 'flow.google.com' in p.url][0]
        # abrir painel personagens
        add = page.locator('[aria-label*="Adicionar elementos" i]')
        if await add.count():
            await add.last.evaluate("(e)=>e.click()")
            await page.wait_for_timeout(700)
        pers = page.locator('span[matlistitemtitle]').filter(has_text='Personagens')
        if await pers.count():
            await pers.last.evaluate("(e)=>e.click()")
            await page.wait_for_timeout(1000)
        ed = page.locator('[contenteditable="true"]').first
        before = await ed.inner_text()
        thumb = page.locator('img.character-tile-thumbnail').first
        print("thumb", await thumb.count(), await thumb.get_attribute('draggable'), flush=True)
        await thumb.drag_to(ed)
        await page.wait_for_timeout(1500)
        after = await ed.inner_text()
        html = await ed.evaluate("(e)=>e.innerHTML.slice(0,1500)")
        print("BEFORE", repr(before[:120]), flush=True)
        print("AFTER", repr(after[:300]), flush=True)
        print("HTML", html[:1500], flush=True)
asyncio.run(main())
