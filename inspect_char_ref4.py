import asyncio, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        page = b.contexts[0].pages[0]
        for kw in ['Luna', 'Frida']:
            loc = page.get_by_text(kw, exact=True)
            print("==", kw, await loc.count(), flush=True)
            for i in range(min(await loc.count(), 4)):
                el = loc.nth(i)
                print(" ", i, await el.evaluate("(e)=>e.outerHTML.slice(0,300)"), flush=True)
        # procurar chips de personagens no prompt
        chips = page.locator('button, [role="button"]').filter(has_text='Frida')
        print("chips Frida", await chips.count(), flush=True)
        for i in range(await chips.count()):
            print("  ", await chips.nth(i).evaluate("(e)=>e.outerHTML.slice(0,400)"), flush=True)
asyncio.run(main())
