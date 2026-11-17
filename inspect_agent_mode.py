import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        page = b.contexts[0].pages[0]
        print("URL", page.url, flush=True)
        # find anything with text 'Agente' / 'Agent'
        for pat in ['Agente', 'Agent', 'agente']:
            loc = page.get_by_text(pat, exact=False)
            n = await loc.count()
            print(f"text {pat!r}: {n}", flush=True)
            for i in range(min(n, 5)):
                print("  ", (await loc.nth(i).inner_text())[:100], flush=True)
        # switches / toggles / checkboxes near prompt
        for sel in ['[role="switch"]', '[role="checkbox"]', 'input[type="checkbox"]', 'button[aria-pressed]', 'button[aria-label*="Agente" i]', 'button:has-text("Agente")']:
            loc = page.locator(sel)
            n = await loc.count()
            print(f"{sel}: {n}", flush=True)
            for i in range(min(n, 6)):
                el = loc.nth(i)
                print("   ", (await el.evaluate("(e)=>e.outerHTML.slice(0,250)")), flush=True)
        # prompt panel html
        ed = page.locator('[contenteditable="true"]').first
        if await ed.count():
            parent = ed.locator('xpath=../..')
            print("PROMPT PANEL HTML:", (await parent.evaluate("(e)=>e.outerHTML.slice(0,4000)")), flush=True)
        await b.close()

asyncio.run(main())
