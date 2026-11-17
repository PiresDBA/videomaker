import asyncio, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        for i, page in enumerate(b.contexts[0].pages):
            print("PAGE", i, page.url, flush=True)
            chip = page.locator('button.agent-mode-chip')
            print("  chip", await chip.count(), "pressed", await chip.get_attribute('aria-pressed') if await chip.count() else '?', flush=True)
            ed = page.locator('[contenteditable="true"]').first
            print("  editor", repr((await ed.inner_text())[:80]) if await ed.count() else 'none', flush=True)
asyncio.run(main())
