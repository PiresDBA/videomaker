import asyncio, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright
sys.path.insert(0, r'C:\videomaker\scripts')
import flow_fetch as ff

PROMPT = """Crie exatamente 2 imagens estaticas, uma diferente da outra, em 16:9.
IMAGEM 1: Frida (buldogue fawn) e Luna (salsicha marrom) na sala, olhando para uma caminha de cachorro VERMELHA com coracoes DOURADOS, bordas altas e travesseiro branco, sobre o tapete perto da janela.
IMAGEM 2: Frida e Luna deitadas juntas DENTRO da MESMA caminha VERMELHA com coracoes DOURADOS, mesma sala, angulo diferente.
A caminha e exatamente a mesma nas duas imagens: VERMELHA, coracoes DOURADOS, bordas altas, travesseiro branco. Nao escreva nenhuma palavra, letra ou numero nas imagens. Sem video, sem audio, sem marcas."""

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        page = b.contexts[0].pages[0]
        await ff.open_fresh(page, "image")
        chip = page.locator('button.agent-mode-chip')
        if await chip.get_attribute('aria-pressed') != 'true':
            await chip.evaluate("(e)=>e.click()")
            await page.wait_for_timeout(800)
        print("AGENT ON", await chip.get_attribute('aria-pressed'), flush=True)
        full = ff._enforce_image_only(ff._enforce_characters(PROMPT))
        print("PROMPT LEN", len(full), flush=True)
        # snapshot current image urls
        before = await page.evaluate("() => Array.from(document.querySelectorAll('img')).map(i=>i.src).filter(s=>s.startsWith('http'))")
        print("BEFORE IMGS", len(before), flush=True)
        res = await ff.submit_flow_prompt(page, full, clear=True)
        print("SUBMIT", res, flush=True)
        await page.wait_for_timeout(180000)
        after = await page.evaluate("() => Array.from(document.querySelectorAll('img')).map(i=>i.src).filter(s=>s.startsWith('http'))")
        new = [u for u in after if u not in before]
        print("AFTER IMGS", len(after), "NEW", len(new), flush=True)
        for u in new[:10]:
            print("NEW URL", u[:160], flush=True)
        await b.close()

asyncio.run(main())
