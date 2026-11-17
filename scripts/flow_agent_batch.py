# -*- coding: utf-8 -*-
r"""flow_agent_batch.py - gera varias imagens de uma so vez com o MODO AGENTE do Google Flow.

Experimental (branch experiment/flow-agent-batch). Nao altera flow_fetch.py.

Fluxo:
  1. Le image_prompts.json (nome -> prompt).
  2. Filtra as imagens que ja existem no out-dir.
  3. Agrupa em lotes de --batch-size (padrao 10).
  4. Para cada lote, monta UM prompt com as cenas numeradas (IMAGEM 1, IMAGEM 2, ...)
     e envia com o modo Agente ligado.
  5. Captura as imagens via response handler (na ordem em que o Flow baixa) e salva
     com os nomes corretos do lote.

Uso:
  python scripts/flow_agent_batch.py --project-dir <proj> --batch-size 10 --wait 600
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from io import BytesIO
from pathlib import Path

from playwright.async_api import async_playwright

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
DEFAULT_CDP = "http://127.0.0.1:18800"


def _cena_do_prompt(prompt: str) -> str:
    """Extrai so a descricao da CENA (primeira linha do prompt)."""
    first = (prompt or "").splitlines()[0] if prompt else ""
    if first.startswith("CENA"):
        first = first.split(":", 1)[1].strip() if ":" in first else first
    return first.strip() or "cena ilustrativa da historia"


def _biblia_do_prompt(prompt: str) -> str:
    """Extrai o bloco BIBLIA DE CONTINUIDADE (se houver)."""
    txt = prompt or ""
    marker = "BIBLIA DE CONTINUIDADE"
    i = txt.find(marker)
    if i < 0:
        return ""
    # ate a proxima secao em maiusculas conhecida
    end = len(txt)
    for nxt in ("PERSONAGENS (", "REGRA ANTI-REPETICAO", "ESTILO IGUAL"):
        j = txt.find(nxt, i + len(marker))
        if j >= 0:
            end = min(end, j)
    return txt[i:end].strip()


def montar_prompt_lote(itens, biblia: str) -> str:
    """Monta o prompt unico do lote com cenas numeradas."""
    n = len(itens)
    linhas = [
        "Crie exatamente %d imagens estaticas, numeradas de 1 a %d, uma diferente da outra, todas em 16:9." % (n, n),
        "IMPORTANTE: gere as imagens NA ORDEM em que estao numeradas. A IMAGEM 1 primeiro, depois a IMAGEM 2, e assim por diante.",
    ]
    if biblia:
        linhas.append("")
        linhas.append("BIBLIA DE CONTINUIDADE (vale para TODAS as %d imagens): %s" % (n, biblia))
    linhas.append("")
    for idx, (name, cena) in enumerate(itens, 1):
        linhas.append("IMAGEM %d (%s): %s" % (idx, name, cena))
    linhas.append("")
    linhas.append(
        "REGRAS PARA TODAS: mantenha os mesmos personagens e os mesmos objetos/cenario da BIBLIA "
        "em todas as imagens; mude apenas angulo, enquadramento, poses e acao. "
        "A caminha e SEMPRE uma caminha de cachorro comum, do mesmo jeito: se a cena usar "
        "comparacoes ou metatoras como 'parece uma espaconave', 'nuvem', 'trono' ou 'monstro', "
        "essas palavras descrevem apenas a SENSACAO dos personagens - NUNCA transforme a caminha "
        "em nave, nuvem, trono ou monstro, e NAO adicione rodas, asas, luzes ou motor. "
        "Nao adicione personagens novos (gatos, coelhos, passaros etc.) que nao estejam escritos na cena. "
        "Uma unica imagem estatica por numero (NAO gere video, NAO gere audio). "
        "Nao escreva NADA nas imagens: sem palavras, letras, numeros, legendas ou baloes. Sem marcas."
    )
    return "\n".join(linhas)


async def get_page(ctx):
    for p in ctx.pages:
        if "flow.google.com" in p.url:
            return p
    return await ctx.new_page()


async def open_image_page(page):
    """Reusa open_fresh do flow_fetch se disponivel; senao so navega."""
    try:
        sys.path.insert(0, str(HERE))
        import flow_fetch as ff
        await ff.open_fresh(page, "image")
        return True
    except Exception as e:
        print("  aviso: open_fresh falhou (%s); usando pagina atual" % str(e)[:80], flush=True)
        return False


async def ativar_agente(page) -> bool:
    chip = page.locator("button.agent-mode-chip")
    if await chip.count() == 0:
        print("  AVISO: botao Agente nao encontrado", flush=True)
        return False
    if await chip.get_attribute("aria-pressed") != "true":
        await chip.evaluate("(e)=>e.click()")
        await page.wait_for_timeout(800)
    pressed = await chip.get_attribute("aria-pressed") == "true"
    print("  modo Agente:", "ON" if pressed else "OFF", flush=True)
    return pressed


async def baixar_novas(page, quantidade: int, wait_s: int):
    """Captura imagens novas via response handler. Retorna lista de bytes na ordem de chegada."""
    capturadas = []
    urls_vistas = set()

    # ja carregadas na tela antes do envio
    try:
        pre = await page.evaluate(
            "() => Array.from(document.querySelectorAll('img')).map(i=>i.src)"
        )
        urls_vistas.update(u for u in pre if u)
    except Exception:
        pass

    async def on_resp(resp):
        if len(capturadas) >= quantidade:
            return
        url = resp.url or ""
        if url in urls_vistas:
            return
        if not ("flow.google.com/asb/" in url or "flow-content.google" in url
                or "googleusercontent.com" in url):
            return
        try:
            ct = (resp.headers or {}).get("content-type", "")
            if not ct.startswith("image/"):
                return
            body = await resp.body()
            if body and len(body) > 20000:
                urls_vistas.add(url)
                capturadas.append(body)
                print("  capturada %d/%d (%s, %d bytes)" % (
                    len(capturadas), quantidade, ct, len(body)), flush=True)
        except Exception:
            pass

    page.on("response", on_resp)
    deadline = asyncio.get_event_loop().time() + wait_s
    while len(capturadas) < quantidade and asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(2)
    page.remove_listener("response", on_resp)
    return capturadas


def salvar_como_jpg(body: bytes, destino: Path):
    """Converte webp/png para JPEG (o pipeline espera .jpg)."""
    try:
        from PIL import Image
        im = Image.open(BytesIO(body)).convert("RGB")
        im.save(destino, format="JPEG", quality=92)
    except Exception:
        destino.write_bytes(body)


async def processar_lote(page, itens, biblia, out_dir, wait_s):
    prompt = montar_prompt_lote(itens, biblia)
    print("\n=== LOTE: %d imagem(ns) | prompt %d chars ===" % (len(itens), len(prompt)), flush=True)
    for name, cena in itens:
        print("   -", name, ":", cena[:90], flush=True)

    await open_image_page(page)
    await ativar_agente(page)

    # usa o envio consolidado do flow_fetch (ja testado no modo agente)
    sys.path.insert(0, str(HERE))
    import flow_fetch as ff
    full = ff._enforce_image_only(ff._enforce_characters(prompt))
    captor = asyncio.create_task(baixar_novas(page, len(itens), wait_s))
    res = await ff.submit_flow_prompt(page, full, clear=True)
    print("  submit:", res, flush=True)
    if not res.get("ok"):
        captor.cancel()
        return []
    print("  prompt enviado; aguardando imagens...", flush=True)
    bodies = await captor

    if len(bodies) < len(itens):
        print("  AVISO: recebidas %d de %d imagens" % (len(bodies), len(itens)), flush=True)
    salvos = []
    for (name, _), body in zip(itens, bodies):
        dest = out_dir / (name + ".jpg")
        salvar_como_jpg(body, dest)
        salvos.append(dest)
        print("  salvo:", dest.name, flush=True)
    return salvos


async def main_async(args):
    prompts_path = Path(args.prompts_file)
    prompts = json.loads(prompts_path.read_text(encoding="utf-8"))
    itens_todos = [(k, _cena_do_prompt(v)) for k, v in prompts.items() if not k.startswith("_")]
    biblia = ""
    for v in prompts.values():
        b = _biblia_do_prompt(v)
        if b:
            biblia = b
            break
    print("Biblia encontrada:", bool(biblia), flush=True)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pendentes = [(n, c) for n, c in itens_todos
                 if not (out_dir / (n + ".jpg")).exists()
                 or (out_dir / (n + ".jpg")).stat().st_size == 0]
    print("Total:", len(itens_todos), "| pendentes:", len(pendentes), flush=True)
    if not pendentes:
        return

    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp(args.cdp_url)
        ctx = b.contexts[0]
        page = await get_page(ctx)
        if "flow.google.com" not in page.url:
            await page.goto("https://flow.google.com/", wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(2000)

        lotes = [pendentes[i:i + args.batch_size]
                 for i in range(0, len(pendentes), args.batch_size)]
        for li, lote in enumerate(lotes, 1):
            print("\n=== LOTE %d/%d ===" % (li, len(lotes)), flush=True)
            await processar_lote(page, lote, biblia, out_dir, args.wait)
            await page.wait_for_timeout(args.pause * 1000)
        # NAO chamar b.close(): conectamos via CDP e fecharia o Chrome do usuario.


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts-file", default=str(PROJECT / "artifacts" / "image_prompts.json"))
    ap.add_argument("--project-dir", default="")
    ap.add_argument("--out-dir", default="")
    ap.add_argument("--batch-size", type=int, default=10)
    ap.add_argument("--wait", type=int, default=600)
    ap.add_argument("--pause", type=float, default=4.0)
    ap.add_argument("--cdp-url", default=DEFAULT_CDP)
    args = ap.parse_args()
    if args.project_dir and not args.out_dir:
        args.out_dir = str(Path(args.project_dir) / "assets" / "images" / "gemini" / "scenes")
    if not args.out_dir:
        args.out_dir = str(PROJECT / "assets" / "images" / "gemini" / "scenes")
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
