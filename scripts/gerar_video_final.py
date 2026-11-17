# -*- coding: utf-8 -*-
"""Gera o 3o video (outro) — corrige o modal de edicao de prompt.

Anexar referencia via JS as vezes abre um modal de edicao; o prompt fica la
e o botao da barra principal nao envia. Este script fecha o modal e envia
pela barra normal, sem mencionar marcas (o logo/joinha vai como overlay HTML).
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import flow_fetch as ff

CDP = "http://127.0.0.1:18800"
SAVE = Path(r"C:\videomaker\projects\a-caminha-nova-que-ninguem-quer-usar\assets\images\gemini\scenes\outro_8s.mp4")
PROMPT = (
    "An 8-second cheerful animated video, 16:9, high-end 3D cartoon for children. "
    "Use the SAME two dogs from the reference image: FRIDA = a big fawn English "
    "bulldog with a pearl necklace; LUNA = a long brown dachshund with a gold collar. "
    "Both dogs smile, wave at the camera and celebrate happily with little confetti "
    "and sparkles in a cozy living room with a red dog bed with golden hearts. "
    "Warm golden light, gentle zoom out, happy children ending. "
    "Same breeds, faces, colors and sizes. No humans, no cats, no other dogs."
)


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp(CDP)
        pg = [x for x in b.contexts[0].pages if "flow.google.com" in x.url][0]

        # Fecha o modal de edicao (X) e overlays
        await pg.keyboard.press("Escape")
        await pg.wait_for_timeout(600)
        close = pg.locator('button[aria-label="Fechar"], .cdk-dialog-close, [aria-label*="Close" i]').first
        if await close.count():
            try:
                await close.click(timeout=3000)
            except Exception:
                pass
        await ff._dismiss_overlays(pg)
        await pg.wait_for_timeout(800)

        # Confere videos ja gerados
        vids = await pg.locator("video").count()
        print("videos na galeria antes:", vids, flush=True)

        # Preenche a BARRA principal (ultimo editor visivel fora do modal)
        eds = pg.locator(ff.EDITORS[0])
        n = await eds.count()
        print("editors:", n, flush=True)
        ed = eds.last
        await ed.click()
        await pg.wait_for_timeout(300)
        await ed.fill(PROMPT)
        await pg.wait_for_timeout(500)
        typed = (await ed.inner_text()).strip()
        print("prompt na barra:", len(typed), flush=True)

        # Botao arrow_forward dentro da barra de prompt
        gen = pg.locator('button:has(mat-icon:has-text("arrow_forward"))').last
        print("gen buttons:", await gen.count(), flush=True)
        if await gen.count():
            await gen.click(timeout=8000)
        else:
            await pg.keyboard.press("Enter")
        await pg.wait_for_timeout(4000)

        # Confirmacao: prompt sumiu da barra?
        after = (await ed.inner_text()).strip()
        print("prompt depois do submit:", len(after), flush=True)
        if len(after) > 20:
            print("NAO ENVIOU — prompt ainda na barra", flush=True)
            await pg.screenshot(path=r"C:\videomaker\video_outro_nao_enviou.png")
            return

        # Aguarda novo video e baixa
        antes = await pg.locator("video").count()
        net = {"url": None}

        def on_resp(resp):
            try:
                ct = (resp.headers or {}).get("content-type", "").split(";")[0].lower()
                if ct.startswith("video/") and resp.status in (200, 206) and net["url"] is None:
                    net["url"] = resp.url
                    print("URL video detectada", flush=True)
            except Exception:
                pass

        pg.on("response", on_resp)
        t0 = time.time()
        try:
            while time.time() - t0 < 540:
                await pg.wait_for_timeout(5000)
                if await pg.locator("video").count() > antes:
                    print("novo video na galeria!", flush=True)
                    await pg.wait_for_timeout(4000)
                if net["url"]:
                    try:
                        data, ct = await ff.fetch_url(pg, net["url"])
                        if data and len(data) > 5000:
                            SAVE.write_bytes(data)
                            print("BAIXADO:", SAVE, SAVE.stat().st_size, flush=True)
                            return
                    except Exception as e:
                        print("download falhou:", str(e)[:80], flush=True)
                        net["url"] = None
                el = int(time.time() - t0)
                if el % 60 < 5:
                    print("aguardando...", el, "s", flush=True)
            print("TIMEOUT — video pode estar na galeria", flush=True)
        finally:
            pg.remove_listener("response", on_resp)


if __name__ == "__main__":
    asyncio.run(main())
