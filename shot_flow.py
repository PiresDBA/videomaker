import asyncio, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        page = [p for p in b.contexts[0].pages if 'flow.google.com' in p.url][0]
        print("URL", page.url, flush=True)
        body = await page.locator('body').inner_text()
        i = body.find('crédito')
        print("CREDITO", repr(body[max(0,i-100):i+250]) if i>=0 else 'sem aviso', flush=True)
        await page.screenshot(path=r'C:\videomaker\flow_state.png', full_page=False)
        print("shot salvo", flush=True)
asyncio.run(main())
