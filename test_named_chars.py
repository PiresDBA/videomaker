import asyncio, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright
sys.path.insert(0, r'C:\videomaker\scripts')
import flow_fetch as ff

PROMPT = """Use os personagens SALVOS no Google Flow chamados Frida e Luna (os personagens criados neste projeto).
Crie exatamente 1 imagem estatica: Frida e Luna sentadas juntas na sala olhando para uma caminha vermelha com coracoes dourados.
Nao escreva texto na imagem."""

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        page = b.contexts[0].pages[0]
        await ff.open_fresh(page, "image")
        chip = page.locator('button.agent-mode-chip')
        if await chip.count() and await chip.get_attribute('aria-pressed') == 'true':
            await chip.evaluate("(e)=>e.click()")  # desliga agente para 1 imagem
            await page.wait_for_timeout(500)
        print("agent", await chip.get_attribute('aria-pressed') if await chip.count() else 'no chip', flush=True)
        # captura response
        bodies=[]
        async def on_resp(resp):
            url=resp.url or ""
            if "flow.google.com/asb/" in url:
                ct=(resp.headers or {}).get("content-type","")
                if ct.startswith("image/"):
                    body=await resp.body()
                    if len(body)>20000: bodies.append(body)
        page.on("response", on_resp)
        res = await ff.submit_flow_prompt(page, ff._enforce_image_only(PROMPT), clear=True)
        print("submit", res, flush=True)
        for _ in range(90):
            if bodies: break
            await asyncio.sleep(2)
        print("bodies", len(bodies), flush=True)
        if bodies:
            from pathlib import Path
            Path(r'C:\videomaker\named_char_test.jpg').write_bytes(bodies[-1])
            print("saved", flush=True)
asyncio.run(main())
