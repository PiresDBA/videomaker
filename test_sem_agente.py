import asyncio, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright
sys.path.insert(0, r'C:\videomaker\scripts')
import flow_fetch as ff

PROMPT = """A single static 16:9 image, high-end cinematic 3D animation, Pixar style. Two dogs only, NO humans, NO cats:
FRIDA = a large fawn English bulldog with wrinkled face, short muzzle and a white pearl necklace.
LUNA = a long low chocolate-brown dachshund (sausage dog) with short legs and a thin gold collar.
They are sitting together in the living room looking at a red dog bed with golden hearts.
No other dogs. No pug, no labrador, no beagle. No text, no words, no letters."""

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        page = [p for p in b.contexts[0].pages if 'flow.google.com' in p.url][0]
        await ff.open_fresh(page, "image")
        chip = page.locator('button.agent-mode-chip')
        print("chip count", await chip.count(), "pressed", await chip.get_attribute('aria-pressed') if await chip.count() else 'none', flush=True)
        if await chip.count() and await chip.get_attribute('aria-pressed') == 'true':
            await chip.evaluate("(e)=>e.click()")
            await page.wait_for_timeout(700)
            print("desliguei agente", await chip.get_attribute('aria-pressed'), flush=True)
        out = Path(r'C:\videomaker\teste_individual')
        out.mkdir(exist_ok=True)
        res = await ff.grab_image(page, "teste_sem_agente", PROMPT, out, 300)
        print("RES", res, flush=True)
asyncio.run(main())
