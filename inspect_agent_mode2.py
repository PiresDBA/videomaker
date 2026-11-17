import asyncio, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright
sys.path.insert(0, r'C:\videomaker\scripts')
import flow_fetch as ff

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        page = b.contexts[0].pages[0]
        await ff.open_fresh(page, "image")
        chip = page.locator('button.agent-mode-chip')
        print("chip", await chip.count(), "pressed", await chip.get_attribute('aria-pressed'), flush=True)
        await chip.evaluate("(e)=>e.click()")
        await page.wait_for_timeout(1500)
        print("chip pressed after", await chip.get_attribute('aria-pressed'), flush=True)
        ed = await ff.editor(page)
        print("placeholder", await ed.get_attribute('data-placeholder'), flush=True)
        print("editor html", (await ed.evaluate("(e)=>e.outerHTML.slice(0,1500)")), flush=True)
        # look for any text about number of images/scenes
        body = await page.locator('body').inner_text()
        for kw in ['imagens', 'cenas', 'agent', 'Agente', 'quantidade', 'número']:
            idx = body.find(kw)
            if idx >= 0:
                print("BODY", kw, repr(body[max(0,idx-120):idx+180]), flush=True)
        await b.close()

asyncio.run(main())
