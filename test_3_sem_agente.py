import asyncio, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright
sys.path.insert(0, r'C:\videomaker\scripts')
import flow_fetch as ff

PROMPT = """Create exactly 3 static 16:9 images, numbered IMAGEM 1, IMAGEM 2, IMAGEM 3, in order. High-end cinematic 3D animation, Pixar style.
FRIDA = large fawn English bulldog, wrinkled face, pearl necklace. LUNA = long low chocolate dachshund, short legs, gold collar. NO humans, NO cats, NO other dog breeds.
IMAGEM 1: Frida and Luna standing in the living room looking at a red dog bed with golden hearts.
IMAGEM 2: Frida sniffing the red dog bed with golden hearts.
IMAGEM 3: Luna lying down inside the red dog bed with golden hearts.
Same two dogs, same red bed in all 3 images. No text, no words, no letters."""

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        page = [p for p in b.contexts[0].pages if 'flow.google.com' in p.url][0]
        await ff.open_fresh(page, "image")
        chip = page.locator('button.agent-mode-chip')
        print("chip", await chip.count(), "pressed", await chip.get_attribute('aria-pressed') if await chip.count() else 'none', flush=True)
        if await chip.count() and await chip.get_attribute('aria-pressed') == 'true':
            await chip.evaluate("(e)=>e.click()")
            await page.wait_for_timeout(700)
            print("desliguei agente", await chip.get_attribute('aria-pressed'), flush=True)

        capturadas = []
        vistas = set(await page.evaluate("() => Array.from(document.querySelectorAll('img')).map(i=>i.src).filter(s=>s)"))
        async def on_resp(resp):
            url = resp.url or ""
            if url in vistas: return
            if not ("flow.google.com/asb/" in url or "flow-content.google" in url or "googleusercontent.com" in url): return
            try:
                ct = (resp.headers or {}).get("content-type","")
                if not ct.startswith("image/"): return
                body = await resp.body()
                if body and len(body) > 20000:
                    vistas.add(url); capturadas.append(body)
                    print("capturada", len(capturadas), ct, len(body), flush=True)
            except Exception: pass
        page.on("response", on_resp)
        res = await ff.submit_flow_prompt(page, ff._enforce_image_only(PROMPT), clear=True)
        print("submit", res, flush=True)
        deadline = asyncio.get_event_loop().time()+600
        while len(capturadas) < 3 and asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(2)
        print("TOTAL CAPTURADAS", len(capturadas), flush=True)
        out = Path(r'C:\videomaker\teste_3_sem_agente')
        out.mkdir(exist_ok=True)
        from io import BytesIO
        from PIL import Image
        for i, body in enumerate(capturadas):
            try:
                Image.open(BytesIO(body)).convert("RGB").save(out/f"img_{i}.jpg", quality=92)
            except Exception:
                (out/f"img_{i}.jpg").write_bytes(body)
        # NAO fechar browser
asyncio.run(main())
