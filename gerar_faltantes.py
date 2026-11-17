import asyncio, sys, json
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright
sys.path.insert(0, r'C:\videomaker\scripts')
import flow_fetch as ff

PROJ = Path(r'C:\videomaker\projects\a-caminha-nova-que-ninguem-quer-usar')
OUT = PROJ / "assets" / "images" / "gemini" / "scenes"

# 5 imagens faltantes com cenas curtas em ingles
FALTANTES = {
    "desenvolvimento_5_scene_e": "Luna stretches her neck as far as she can to reach the green tennis ball, her short legs on the floor, near the red dog bed with golden hearts.",
    "desenvolvimento_8_scene_e": "Frida and Luna tangled in a funny pile of paws inside the red dog bed with golden hearts, both dogs looking surprised.",
    "desenvolvimento_11_scene_d": "Luna lying in the red dog bed with golden hearts, smelling the clean fabric and the soft heart pillow, eyes closed happily.",
    "desenvolvimento_11_scene_f": "Luna resting in the red dog bed with golden hearts, stretching her short paws out over the red edge, relaxed.",
    "desenvolvimento_12_scene": "Frida and Luna in the living room suddenly looking toward the kitchen with curious faces, a strange noise, the red dog bed with golden hearts nearby.",
}
BASE = ("Pixar-style 3D cartoon, 16:9. The SAME two dogs in every image: "
        "FRIDA = big fawn English bulldog with pearl necklace; "
        "LUNA = long low chocolate-brown dachshund with gold collar. ")
FIM = " No humans, no cats, no other dog breeds. No text, no words. Warm cozy light."

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        page = [p for p in b.contexts[0].pages if 'flow.google.com' in p.url][0]
        await ff.open_fresh(page, "image")
        chip = page.locator('button.agent-mode-chip')
        if await chip.count() and await chip.get_attribute('aria-pressed') == 'true':
            await chip.evaluate("(e)=>e.click()")
            await page.wait_for_timeout(500)
        for name, cena in FALTANTES.items():
            jpg = OUT / (name + ".jpg")
            if jpg.exists() and jpg.stat().st_size > 0:
                print("ja existe:", name, flush=True); continue
            prompt = BASE + "Scene: " + cena + "." + FIM
            print("\nGERANDO:", name, flush=True)
            res = await ff.grab_image(page, name, prompt, OUT, 300)
            print("  RES:", res, flush=True)
asyncio.run(main())
