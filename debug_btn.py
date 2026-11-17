import asyncio, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        page = b.contexts[0].pages[0]
        btn = page.locator('button[aria-label="Iniciar geração"]')
        print("count", await btn.count(), flush=True)
        print("html", await btn.evaluate("(e)=>e.outerHTML.slice(0,500)"), flush=True)
        print("disabled", await btn.is_disabled(), flush=True)
        print("visible", await btn.is_visible(), flush=True)
        await b.close()
asyncio.run(main())
