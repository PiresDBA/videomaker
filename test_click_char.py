import asyncio, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        page = [p for p in b.contexts[0].pages if 'flow.google.com' in p.url][0]
        add = page.locator('[aria-label*="Adicionar elementos" i]')
        if await add.count():
            await add.last.evaluate("(e)=>e.click()")
            await page.wait_for_timeout(700)
        pers = page.locator('span[matlistitemtitle]').filter(has_text='Personagens')
        if await pers.count():
            await pers.last.evaluate("(e)=>e.click()")
            await page.wait_for_timeout(1000)
        thumb = page.locator('img.character-tile-thumbnail').first
        try:
            await thumb.click(timeout=5000)
            print("clicked thumb", flush=True)
        except Exception as e:
            print("click err", str(e)[:100], flush=True)
        await page.wait_for_timeout(1500)
        ed = page.locator('[contenteditable="true"]').first
        print("EDITOR", repr((await ed.inner_text())[:300]), flush=True)
        body = await page.locator('body').inner_text()
        for kw in ['Usar', 'Gerar com', 'Criar', 'Inserir', 'Selecionar']:
            i = body.find(kw)
            if i>=0: print("BODY", kw, repr(body[max(0,i-80):i+150]), flush=True)
asyncio.run(main())
