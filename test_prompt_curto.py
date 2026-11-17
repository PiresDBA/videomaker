import asyncio, sys, json
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright
sys.path.insert(0, r'C:\videomaker\scripts')
import flow_fetch as ff

# Prompt CURTO em ingles, sem o bloco gigante de regras em portugues
PROMPT = """Pixar 3D cartoon. Frida (big fawn bulldog with pearl collar) and Luna (long brown dachshund with gold collar) in a cozy living room. Luna nudges a green tennis ball with her nose near a red dog bed with golden hearts. Warm light, cheerful. No humans, no cats, no text."""

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        page = [p for p in b.contexts[0].pages if 'flow.google.com' in p.url][0]
        await ff.open_fresh(page, "image")
        chip = page.locator('button.agent-mode-chip')
        if await chip.count() and await chip.get_attribute('aria-pressed') == 'true':
            await chip.evaluate("(e)=>e.click()")
            await page.wait_for_timeout(500)
        # NAO usa _enforce_characters (bloco gigante) -prompt direto curto
        out = Path(r'C:\videomaker\teste_prompt_curto'); out.mkdir(exist_ok=True)
        res = await ff.grab_image(page, "curto", PROMPT, out, 300)
        print("RES", res, flush=True)
asyncio.run(main())
