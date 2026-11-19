# -*- coding: utf-8 -*-
"""flow_observe_arm.py - Instala o observador de cliques no Flow e fica
gravando. O usuario navega livremente; depois flow_observe_collect.py salva.

Uso:
  python scripts/flow_observe_arm.py      # instala observador (fica pronto)
  python scripts/flow_observe_collect.py  # coleta e salva perfil aprendido
"""
import asyncio, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright
from flow_learn import JS_OBSERVER, CDP, PROJECT_URL, STATE_FILE
import subprocess, time, urllib.request

def cdp_alive():
    try:
        urllib.request.urlopen(CDP.rstrip('/') + '/json/version', timeout=2)
        return True
    except Exception:
        return False

async def main():
    if not cdp_alive():
        import os
        exe = next((c for c in [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ] if os.path.exists(c)), None)
        profile = r"C:\videomaker\.chrome-gemini-profile"
        print("Chrome nao estava aberto. Abrindo no projeto (sem forcar tamanho)...", flush=True)
        subprocess.Popen([exe, "--remote-debugging-port=18800", f"--user-data-dir={profile}",
                          "--no-first-run", "--no-default-browser-check", PROJECT_URL],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(30):
            if cdp_alive(): break
            time.sleep(1)
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp(CDP)
        ctx = b.contexts[0]
        page = next((pg for pg in ctx.pages if "flow.google.com" in pg.url), None) or await ctx.new_page()
        await page.bring_to_front()
        # navega para o projeto se nao estiver la
        if "/project/" not in page.url:
            import json
            try:
                st = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                url = st.get("url", PROJECT_URL)
            except Exception:
                url = PROJECT_URL
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)
        await page.evaluate(JS_OBSERVER)
        print("✓ Observador de cliques INSTALADO e gravando.")
        print("  URL:", page.url)
        print("\n>>> Navegue no Flow agora (Imagem, x1, fechar pop-ups, deixar campo visivel).")
        print(">>> Quando terminar, me avise no chat para eu coletar e salvar.")
        await b.close()

if __name__ == "__main__":
    asyncio.run(main())
