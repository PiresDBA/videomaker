import asyncio, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        page = b.contexts[0].pages[0]
        print("URL", page.url, flush=True)
        asb = await page.evaluate("() => Array.from(document.querySelectorAll('img')).map(i=>i.src).filter(s=>s.startsWith('https://flow.google.com/asb/'))")
        print("ASB count", len(asb), flush=True)
        ed = page.locator('[contenteditable="true"]').first
        print("editor text", repr((await ed.inner_text())[:300]), flush=True)
        chip = page.locator('button.agent-mode-chip')
        print("agent", await chip.get_attribute('aria-pressed'), flush=True)
        # botoes de geracao
        for sel in ['button[aria-label="Iniciar geração"]', 'button:has-text("Iniciar geração")']:
            loc = page.locator(sel)
            print(sel, await loc.count(), flush=True)
        body = await page.locator('body').inner_text()
        i = body.find('Crie exatamente')
        print("PROMPT IN BODY", i >= 0, flush=True)
        if i >= 0:
            print(repr(body[i:i+400]), flush=True)
        await b.close()
asyncio.run(main())
