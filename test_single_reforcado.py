import asyncio, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright
sys.path.insert(0, r'C:\videomaker\scripts')
import flow_fetch as ff

# Prompt CURTO e direto: o Flow ja tem os personagens Frida e Luna criados.
PROMPT = """Use os personagens FRIDA e LUNA que ja estao criados neste projeto do Google Flow como referencia. Gere uma imagem estatica unica, 16:9, estilo Disney Pixar 3D.
CENA: Frida e Luna estao na sala, sentadas juntas olhando para a caminha vermelha com coracoes dourados.
Frida e a buldogue inglesa fawn. Luna e a salsicha dachshund marrom. Use exatamente os personagens criados. Sem texto, sem humanos, sem gatos."""

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        page = b.contexts[0].pages[0]
        await ff.open_fresh(page, "image")
        chip = page.locator('button.agent-mode-chip')
        if await chip.count() and await chip.get_attribute('aria-pressed') == 'true':
            await chip.evaluate("(e)=>e.click()")
            await page.wait_for_timeout(500)
        print("agent off", await chip.get_attribute('aria-pressed') if await chip.count() else 'none', flush=True)
        out = Path(r'C:\videomaker\teste_individual')
        out.mkdir(exist_ok=True)
        res = await ff.grab_image(page, "teste_individual", PROMPT, out, 420)
        print("RES", res, flush=True)
        # NAO chamar b.close() - isso fecha o Chrome real conectado via CDP
asyncio.run(main())
