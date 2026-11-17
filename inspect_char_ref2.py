import asyncio, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        page = b.contexts[0].pages[0]
        # menu 'Personagens' aberto? clicar
        loc = page.get_by_text('Personagens', exact=True)
        print("text Personagens", await loc.count(), flush=True)
        for i in range(await loc.count()):
            el = loc.nth(i)
            print("  ", await el.evaluate("(e)=>e.outerHTML.slice(0,400)"), flush=True)
        # clicar no ultimo
        if await loc.count():
            await loc.last.evaluate("(e)=>e.click()")
            await page.wait_for_timeout(1500)
            body = await page.locator('body').inner_text()
            i = body.find('Personagens')
            print("BODY after click:", repr(body[max(0,i-200):i+1500]), flush=True)
asyncio.run(main())
