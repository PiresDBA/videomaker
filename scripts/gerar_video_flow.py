# -*- coding: utf-8 -*-
r"""gerar_video_flow.py - gera UM clipe de ~8s no Google Flow (modo Vídeo).

Teste seguro: --inspect só abre a UI e tira screenshot (NAO gera, NAO consome
o limite de 3 vídeos/dia). --generate envia o prompt e baixa o MP4.

Uso:
  python scripts/gerar_video_flow.py --inspect
  python scripts/gerar_video_flow.py --generate --kind intro \
      --prompt "..." --ref "C:\\...\\frame.jpg" --save "C:\\...\\intro.mp4"
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import flow_fetch as ff

CDP = "http://127.0.0.1:18800"
PROJECT_URL = "https://flow.google.com/project/d43a0933-5310-4951-b511-911f96a6bc22"
VIDEO_MODE_LABELS = ("Vídeo", "Video", "Gerar vídeo", "Modo vídeo", "Veo", "Gerar video")
DURATION_LABELS = ("8s", "8 s", "8 segundos", "8 seg")
# MODELO ECONOMICO (usuario): Veo 3.1 Lite, qualidade baixa (10 creditos/video
# -> ate 5 videos). Exportacao em 720p na hora de baixar.
MODEL_LABELS = ("Veo 3.1 Lite", "3.1 Lite", "Veo 3.1-lite", "Lite")
QUALITY_LABELS = ("Baixa", "baixa", "Low", "low", "Qualidade baixa")
EXPORT_720_LABELS = ("720p", "720 p", "720")


async def conectar():
    from playwright.async_api import async_playwright
    pw = await async_playwright().__aenter__()
    b = await pw.chromium.connect_over_cdp(CDP)
    ctx = b.contexts[0]
    page = next((p for p in ctx.pages if "flow.google.com" in p.url), None)
    if page is None:
        page = await ctx.new_page()
    return pw, page


async def preparar(page, inspecionar: bool):
    await page.goto(PROJECT_URL, wait_until="domcontentloaded", timeout=60000)
    try:
        await page.wait_for_load_state("networkidle", timeout=25000)
    except Exception:
        pass
    await page.wait_for_timeout(1500)
    if await ff.needs_login(page):
        raise RuntimeError("Flow deslogado — rode --login primeiro")
    await ff.dismiss_ads_and_permissions(page)
    await ff._dismiss_overlays(page)

    # Abre o painel de configurações
    trig = await ff._loc_first_visible(page, ff.SETTINGS_TRIGGER_SELECTORS, timeout_ms=6000)
    if trig is None:
        raise RuntimeError("painel de configurações do Flow não encontrado")
    try:
        await trig.click(timeout=5000)
    except Exception:
        await trig.evaluate("(e) => e.click()")
    await page.wait_for_timeout(1000)

    # Lista o que o painel oferece (diagnóstico)
    toggles = await page.locator("mat-button-toggle").all_inner_texts()
    print("TOGGLES no painel:", [t.strip() for t in toggles if t.strip()][:20], flush=True)

    # Seleciona modo VÍDEO
    escolhido = None
    for label in VIDEO_MODE_LABELS:
        cand = page.locator(f'mat-button-toggle:has-text("{label}")').first
        if await cand.count():
            escolhido = (label, cand)
            break
    if escolhido is None:
        await page.screenshot(path=r"C:\videomaker\video_ui_painel.png")
        raise RuntimeError("toggle de VÍDEO não encontrado — screenshot em video_ui_painel.png")
    label, toggle = escolhido
    if not await ff._toggle_checked(toggle):
        btn = toggle.locator("button").first
        try:
            if await btn.count():
                await btn.click(timeout=5000)
            else:
                await toggle.click(timeout=5000)
        except Exception:
            await toggle.evaluate("(e) => e.click()")
        await page.wait_for_timeout(900)
    print(f"modo VÍDEO selecionado ('{label}')", flush=True)

    # Duração 8s (se o Flow oferecer)
    for label_d in DURATION_LABELS:
        dur = page.locator(f'mat-button-toggle:has-text("{label_d}")').first
        if await dur.count():
            if not await ff._toggle_checked(dur):
                try:
                    await dur.locator("button").first.click(timeout=4000)
                except Exception:
                    await dur.evaluate("(e) => e.click()")
            print(f"duração {label_d} selecionada", flush=True)
            break
    else:
        print("AVISO: seletor de duração 8s não apareceu (o Flow decide a duração)", flush=True)

    try:
        await page.keyboard.press("Escape")
    except Exception:
        pass
    await page.wait_for_timeout(500)
    await page.screenshot(path=r"C:\videomaker\video_ui_preparado.png")
    print("screenshot: C:\\videomaker\\video_ui_preparado.png", flush=True)
    return page


async def enviar(page, prompt: str, ref: str | None):
    if ref:
        ok = await ff.attach_reference(page, ref)
        print("referência anexada:", ok, flush=True)
    ed = await ff.editor(page)
    await ed.click()
    await page.wait_for_timeout(300)
    try:
        await ed.fill(prompt)
    except Exception:
        await page.keyboard.insert_text(prompt)
    await page.wait_for_timeout(500)
    typed = (await ed.inner_text()).strip()
    print("prompt no campo:", len(typed), "chars", flush=True)
    if len(typed) < 20:
        raise RuntimeError("prompt não entrou no campo")

    gen = page.locator(
        'button[aria-label*="Iniciar geração"], button:has(mat-icon:has-text("arrow_forward"))'
    ).first
    if await gen.count():
        await gen.click(timeout=8000)
    else:
        await page.keyboard.press("Enter")
    await page.wait_for_timeout(3000)
    print("submit disparado", flush=True)


async def baixar(page, save: Path, wait_s: int = 600):
    save.parent.mkdir(parents=True, exist_ok=True)
    dl = page.locator(ff.DL_SELECTOR)
    antes = await dl.count()
    net = {"url": None}

    def on_resp(resp):
        try:
            ct = (resp.headers or {}).get("content-type", "").split(";")[0].lower()
            if ct.startswith("video/") and resp.status in (200, 206) and net["url"] is None:
                net["url"] = resp.url
                print("URL de vídeo detectada", flush=True)
        except Exception:
            pass

    page.on("response", on_resp)
    t0 = time.time()
    tentativas = 0
    try:
        while time.time() - t0 < wait_s:
            await page.wait_for_timeout(4000)
            # 1) botão de download
            if tentativas < 6 and await dl.count() > antes:
                btn = dl.last
                try:
                    if await btn.is_visible() and await btn.is_enabled():
                        tentativas += 1
                        async with page.expect_download(timeout=30000) as dinfo:
                            await btn.click(timeout=10000)
                        d = await dinfo.value
                        p = save.with_suffix(Path(d.suggested_filename).suffix or ".mp4")
                        await d.save_as(str(p))
                        print("BAIXADO via botão:", p, p.stat().st_size, "bytes", flush=True)
                        return p
                except Exception as e:
                    print("download botão falhou:", str(e)[:90], flush=True)
            # 2) URL de rede
            if net["url"]:
                try:
                    data, ct = await ff.fetch_url(page, net["url"])
                    if data and len(data) > 10000:
                        ext = ff.MIME_EXT.get(ct.split(";")[0].strip().lower(), ".mp4")
                        p = save.with_suffix(ext)
                        p.write_bytes(data)
                        print("BAIXADO via URL:", p, len(data), "bytes", flush=True)
                        return p
                except Exception as e:
                    print("download URL falhou:", str(e)[:90], flush=True)
                    net["url"] = None
            el = int(time.time() - t0)
            if el % 60 < 4:
                print(f"aguardando vídeo... {el}s", flush=True)
        await page.screenshot(path=r"C:\videomaker\video_timeout.png")
        raise RuntimeError(f"timeout {wait_s}s sem baixar o vídeo (screenshot: video_timeout.png)")
    finally:
        page.remove_listener("response", on_resp)


async def main_async(args):
    pw, page = await conectar()
    try:
        await preparar(page, args.inspect)
        if args.inspect:
            print("MODO INSPEÇÃO — nada foi gerado", flush=True)
            return
        await enviar(page, args.prompt, args.ref)
        await baixar(page, Path(args.save), args.wait)
    finally:
        # NAO fechar o Chrome do usuario (conexao CDP)
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inspect", action="store_true", help="só inspecionar a UI, não gera")
    ap.add_argument("--prompt", default="")
    ap.add_argument("--ref", default="", help="imagem de referência")
    ap.add_argument("--save", default=r"C:\videomaker\projects\a-caminha-nova-que-ninguem-quer-usar\assets\images\gemini\scenes\intro_8s.mp4")
    ap.add_argument("--wait", type=int, default=600)
    args = ap.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
