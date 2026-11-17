import asyncio, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        page = b.contexts[0].pages[0]
        # menu lateral Personagens
        item = page.locator('[matlistitemtitle]').filter(has_text='Personagens').last
        print("item", await item.count(), flush=True)
        if await item.count():
            await item.evaluate("(e)=>e.click()")
            await page.wait_for_timeout(2000)
            print("URL", page.url, flush=True)
            body = await page.locator('body').inner_text()
            print("BODY", repr(body[:2500]), flush=True)
            # procurar por Frida/Luna como entidades clicaveis
            for kw in ['Frida', 'Luna', 'Criar personagem']:
                loc = page.get_by_text(kw, exact=False)
                print(kw, "count", await loc.count(), flush=True)
asyncio.run(main())
