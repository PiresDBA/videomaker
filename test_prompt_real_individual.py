import asyncio, sys, json
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright
sys.path.insert(0, r'C:\videomaker\scripts')
import flow_fetch as ff

# pega um prompt REAL do projeto (o de desenvolvimento_4 que estava errado)
d = json.load(open(r'C:\videomaker\projects\a-caminha-nova-que-ninguem-quer-usar\artifacts\image_prompts.json', encoding='utf-8'))
PROMPT = d['desenvolvimento_4_scene']

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        page = [p for p in b.contexts[0].pages if 'flow.google.com' in p.url][0]
        await ff.open_fresh(page, "image")
        chip = page.locator('button.agent-mode-chip')
        if await chip.count() and await chip.get_attribute('aria-pressed') == 'true':
            await chip.evaluate("(e)=>e.click()")
            await page.wait_for_timeout(700)
        print("prompt len", len(PROMPT), flush=True)
        out = Path(r'C:\videomaker\teste_prompt_real')
        out.mkdir(exist_ok=True)
        res = await ff.grab_image(page, "prompt_real", PROMPT, out, 420)
        print("RES", res, flush=True)
asyncio.run(main())
