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
  6. VARIEDADE VISUAL (CONTRATO §5.15 / MANUAL_GRAFOS.md §60): em cada lote sortea
     entre imagens separadas (1 painel) e colagens de 2/3/4 painéis, lado a lado
     (linhas verticais) ou empilhados (linhas horizontais), estilo história em
     quadrinho. Colagens 16:9 ficam inteiras (é o efeito desejado no vídeo); só
     proporções extremas são fatiadas pelo `dividir_colagem`.

Uso:
  python scripts/flow_agent_batch.py --project-dir <proj> --batch-size 10 --wait 600
  python scripts/flow_agent_batch.py ... --layout colagem --orientacao empilhado
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
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


IDENTIDADE_PERSONAGENS = (
    "IDENTIDADE FIXA DOS PERSONAGENS (vale para TODAS as imagens, SEM EXCECAO): "
    "FRIDA e um buldogue ingles FEMEA, sempre a MESMA: pelagem fawn/bege-amarelada, "
    "corpo grande, compacto e robusto, rugas na cara, focinho curto e achatado, "
    "orelhas pequenas e dobradas, olhos grandes castanhos com cilios, colar de "
    "PEROLAS BRANCAS com pingente dourado. NUNCA a desenhe como outro tipo de "
    "cachorro (sem poodle, sem pastor, sem cachorro peludo, sem dachshund). "
    "LUNA e uma dachshund/salsicha FEMEA, sempre a MESMA: pelagem marrom-chocolate "
    "curta e brilhante, corpo MUITO comprido e baixo, pernas curtinhas, orelhas "
    "longas e caidas, focinho fino, coleira DOURADA fina com pingente, olhos "
    "grandes castanhos com cilios. NUNCA a desenhe como outro tipo de cachorro. "
    "QUALQUER PERSONAGEM NOVO (ex.: Pipoca) deve manter SEMPRE a MESMA raca, cor, "
    "tamanho e tracos em todas as imagens em que aparecer, conforme descrito na cena. "
    "Se um personagem novo aparece em mais de uma imagem, copie exatamente o mesmo "
    "desenho dele - NAO troque a raca de um cachorro entre imagens."
)

# Orientacoes possiveis dos paineis (estilo historia em quadrinho).
ORIENTACOES = ("lado_a_lado", "empilhado")
PANEIS_POSSIVEIS = (2, 3, 4)

_ORIENTACAO_TEXTO = {
    "lado_a_lado": (
        "paineis VERTICAIS iguais LADO A LADO (divisao em colunas): o painel 1 e o "
        "mais a ESQUERDA, o painel 2 o seguinte, e assim por diante, da esquerda "
        "para a direita"
    ),
    "empilhado": (
        "paineis HORIZONTAIS iguais EMPILHADOS (divisao em linhas): o painel 1 e o "
        "mais ACIMA, o painel 2 o seguinte, e assim por diante, de cima para baixo"
    ),
}


def montar_prompt_lote(itens, biblia: str, colagem: bool = False,
                       orientacao: str = "lado_a_lado", n_paineis: int = 0) -> str:
    """Monta o prompt unico do lote com cenas numeradas.

    colagem=True: pede UMA imagem 16:9 com N paineis internos (2/3/4), na
    orientacao escolhida (`lado_a_lado` ou `empilhado`). Colagens 16:9 sao
    preservadas inteiras pelo `dividir_colagem` — esse e o efeito de historia
    em quadrinho mostrado no video. colagem=False: pede N imagens separadas.
    O Flow as vezes entrega colagem mesmo pedindo separadas; o divisor detecta.
    """
    n = len(itens)
    if colagem and n > 1:
        qtd = min(max(int(n_paineis or n), 2), 4)
        descricao = _ORIENTACAO_TEXTO.get(orientacao, _ORIENTACAO_TEXTO["lado_a_lado"])
        cabecalho = (
            "Crie UMA UNICA imagem estatica em 16:9, dividida em %d %s, com linhas "
            "finas separando os paineis. Cada painel mostra uma CENA diferente e "
            "segue a ordem: painel 1 = CENA 1, painel 2 = CENA 2, e assim por diante. "
            "A cena manda em cada painel: mude angulo, enquadramento e poses entre "
            "eles. NAO escreva NADA na imagem: sem palavras, numeros, legendas ou "
            "baloes." % (qtd, descricao)
        )
    else:
        cabecalho = (
            "Crie exatamente %d imagens estaticas SEPARADAS (arquivos diferentes, NAO uma "
            "colagem), numeradas de 1 a %d, uma diferente da outra, todas em 16:9. "
            "IMPORTANTE: gere na ordem: IMAGEM 1 primeiro, depois IMAGEM 2." % (n, n)
        )
    linhas = [
        cabecalho,
        "",
        IDENTIDADE_PERSONAGENS,
    ]
    if biblia:
        linhas.append("")
        linhas.append("BIBLIA DE CONTINUIDADE (vale para TODAS as %d imagens): %s" % (n, biblia))
    linhas.append("")
    for idx, (name, cena) in enumerate(itens, 1):
        linhas.append("IMAGEM %d (%s): %s" % (idx, name, cena))
    linhas.append("")
    linhas.append(
        "REGRAS PARA TODAS: FRIDA E LUNA DEVEM SER EXATAMENTE IGUAIS A 'IDENTIDADE FIXA DOS "
        "PERSONAGENS' ACIMA EM TODAS AS %d IMAGENS. mantenha os mesmos objetos/cenario da BIBLIA "
        "em todas as imagens; mude apenas angulo, enquadramento, poses e acao. "
        "A caminha e SEMPRE uma caminha de cachorro comum, do mesmo jeito: se a cena usar "
        "comparacoes ou metatoras como 'parece uma espaconave', 'nuvem', 'trono' ou 'monstro', "
        "essas palavras descrevem apenas a SENSACAO dos personagens - NUNCA transforme a caminha "
        "em nave, nuvem, trono ou monstro, e NAO adicione rodas, asas, luzes ou motor. "
        "Nao adicione personagens novos (gatos, coelhos, passaros etc.) que nao estejam escritos na cena. "
        "Uma unica imagem estatica por numero (NAO gere video, NAO gere audio). "
        "Nao escreva NADA nas imagens: sem palavras, letras, numeros, legendas ou baloes. Sem marcas." % n
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
    """NAO usar o modo Agente: ele reescreve o prompt e troca os personagens.
    Se estiver ligado, desliga. Retorna True se o agente ficou DESLIGADO."""
    chip = page.locator("button.agent-mode-chip")
    if await chip.count() == 0:
        print("  modo Agente: indisponivel (ok, segue sem agente)", flush=True)
        return True
    if await chip.get_attribute("aria-pressed") == "true":
        await chip.evaluate("(e)=>e.click()")
        await page.wait_for_timeout(800)
    pressed = await chip.get_attribute("aria-pressed") == "true"
    print("  modo Agente:", "ON (RUIM)" if pressed else "OFF (bom)", flush=True)
    return not pressed


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


def _hash_imagem(body: bytes) -> str:
    return hashlib.md5(body).hexdigest()


def _hashes_existentes(out_dir: Path) -> set:
    """Hashes das imagens ja salvas, para descartar duplicatas vindas da galeria."""
    hashes = set()
    for f in out_dir.glob("*.jpg"):
        try:
            from PIL import Image
            im = Image.open(f).convert("RGB")
            buf = BytesIO()
            im.save(buf, format="JPEG", quality=92)
            hashes.add(_hash_imagem(buf.getvalue()))
        except Exception:
            pass
    return hashes


def salvar_como_jpg(body: bytes, destino: Path):
    """Converte webp/png para JPEG (o pipeline espera .jpg)."""
    try:
        from PIL import Image
        im = Image.open(BytesIO(body)).convert("RGB")
        im.save(destino, format="JPEG", quality=92)
    except Exception:
        destino.write_bytes(body)


def dividir_colagem(body: bytes, n: int, orientacao: str = ""):
    """Trata uma imagem que pode ser colagem de N paineis internos.

    - colagem LARGA (largura/altura > 1.9): fatia em N colunas verticais;
    - colagem ALTA (altura/largura > 1.9): fatia em N linhas horizontais;
    - imagem 16:9 com paineis internos: devolve INTEIRA — e exatamente esse o
      efeito de historia em quadrinho que aparece no video (CONTRATO §5.15).

    Devolve sempre uma lista de bytes (1 item quando nao ha fatia extrema).
    """
    try:
        from PIL import Image
        im = Image.open(BytesIO(body)).convert("RGB")
        w, h = im.size
        margem = 6  # remove linhas divisoriais

        if n > 1 and w / h > 1.9:
            paineis = []
            for i in range(n):
                x0 = int(w * i / n) + (margem if i else 0)
                x1 = int(w * (i + 1) / n) - (margem if i < n - 1 else 0)
                buf = BytesIO()
                im.crop((x0, 0, x1, h)).save(buf, format="JPEG", quality=92)
                paineis.append(buf.getvalue())
            print("  dividida colagem LARGA em %d paineis (%dx%d)" % (n, w, h), flush=True)
            return paineis

        if n > 1 and h / w > 1.9:
            paineis = []
            for i in range(n):
                y0 = int(h * i / n) + (margem if i else 0)
                y1 = int(h * (i + 1) / n) - (margem if i < n - 1 else 0)
                buf = BytesIO()
                im.crop((0, y0, w, y1)).save(buf, format="JPEG", quality=92)
                paineis.append(buf.getvalue())
            print("  dividida colagem ALTA em %d paineis (%dx%d)" % (n, w, h), flush=True)
            return paineis
    except Exception as e:
        print("  aviso ao dividir colagem: %s" % str(e)[:60], flush=True)
    return [body]


async def _enviar_uma_vez(page, itens, biblia, wait_s, hashes_conhecidos,
                         colagem=False, orientacao="lado_a_lado", n_paineis=0):
    """Envia um lote e devolve os bytes das imagens novas nao-duplicadas."""
    prompt = montar_prompt_lote(itens, biblia, colagem=colagem,
                                orientacao=orientacao, n_paineis=n_paineis)
    layout = ("colagem de %d paineis %s" % (n_paineis or len(itens), orientacao)
              if colagem else "imagens separadas (1 painel)")
    print("\n=== LOTE: %d cena(s) | layout=%s | prompt %d chars ===" % (
        len(itens), layout, len(prompt)), flush=True)
    for name, cena in itens:
        print("   -", name, ":", cena[:90], flush=True)

    await open_image_page(page)
    await ativar_agente(page)

    sys.path.insert(0, str(HERE))
    import flow_fetch as ff
    # NAO usa _enforce_image_only: ele injeta "gere SOMENTE UMA IMAGEM" e o Flow
    # responde com um triptico dentro de um unico arquivo. Aqui queremos N imagens
    # SEPARADAS. Mantemos so a injecao de personagens e a regra anti-video.
    chars = ff._enforce_characters(prompt)
    for pat, repl in ff.VIDEO_REQUEST_PATTERNS:
        import re as _re
        chars = _re.sub(pat, repl, chars, flags=_re.I)
    full = chars
    # Uma colagem 16:9 e UMA imagem: esperar N aqui causaria um timeout de minutos.
    esperadas = 1 if colagem else len(itens)
    captor = asyncio.create_task(baixar_novas(page, esperadas, wait_s))
    res = await ff.submit_flow_prompt(page, full, clear=True)
    print("  submit:", res, flush=True)
    if not res.get("ok"):
        captor.cancel()
        return []
    print("  prompt enviado; aguardando imagens...", flush=True)
    bodies = await captor

    novas = []
    for body in bodies:
        h = _hash_imagem(body)
        if h in hashes_conhecidos:
            print("  descartada (duplicata da galeria)", flush=True)
            continue
        hashes_conhecidos.add(h)
        # colagens 16:9 ficam inteiras (efeito quadrinho); proporcoes extremas
        # sao fatiadas em N paineis na orientacao sorteada
        paineis = dividir_colagem(body, len(itens), orientacao=orientacao)
        novas.extend(paineis)
    print("  uteis: %d de %d recebidas (apos tratar colagens)" % (
        len(novas), len(bodies)), flush=True)
    return novas


async def processar_lote(page, itens, biblia, out_dir, wait_s, max_tentativas=4,
                         layout="auto", orientacao_fixa="auto"):
    """Gera o lote e recupera automaticamente as imagens que o Flow nao gerou.

    O Flow as vezes gera menos imagens que o pedido (ex.: 8 de 10). As imagens
    chegam na ordem do prompt, entao salvamos as M primeiras nos primeiros M nomes
    e reenviamos somente os nomes restantes, ate max_tentativas.

    `layout`/`orientacao_fixa` permitem forcar um modo (uteis para teste); o
    default `auto` sortea a variacao visual a cada lote (MANUAL_GRAFOS §60).
    """
    import random
    hashes = _hashes_existentes(out_dir)
    pendentes = list(itens)
    salvos = []
    for tentativa in range(1, max_tentativas + 1):
        if not pendentes:
            break
        tamanho = len(pendentes)

        # VARIEDADE VISUAL: 1 painel (imagens separadas) ou colagem de 2/3/4
        # paineis, lado a lado ou empilhados. Recuperacoes usam imagens separadas
        # para nao repetir a cena ja entregue na colagem.
        if layout == "separado":
            colagem = False
        elif layout == "colagem":
            colagem = tamanho >= 2
        elif tamanho >= 3 and tentativa == 1:
            colagem = random.random() < 0.5
        elif tamanho == 2 and tentativa == 1:
            colagem = random.random() < 0.35
        else:
            colagem = False

        if colagem:
            n_paineis = min(random.choice(PANEIS_POSSIVEIS), tamanho)
            orientacao = (random.choice(ORIENTACOES) if orientacao_fixa == "auto"
                          else orientacao_fixa)
            itens_lote = pendentes[:n_paineis]
        else:
            n_paineis, orientacao, itens_lote = 0, "lado_a_lado", pendentes

        print("\n--- tentativa %d/%d: %d cena(s) pendente(s) | layout=%s ---" % (
            tentativa, max_tentativas, tamanho,
            ("colagem %d paineis %s" % (n_paineis, orientacao) if colagem
             else "separadas (1 painel)")), flush=True)
        novas = await _enviar_uma_vez(page, itens_lote, biblia, wait_s, hashes,
                                      colagem=colagem, orientacao=orientacao,
                                      n_paineis=n_paineis)
        if not novas:
            print("  nenhuma imagem nova recebida; tentando de novo...", flush=True)
            await page.wait_for_timeout(5000)
            continue
        # salva as M primeiras nos primeiros M nomes pendentes
        para_salvar = pendentes[:len(novas)]
        for (name, _), body in zip(para_salvar, novas):
            dest = out_dir / (name + ".jpg")
            salvar_como_jpg(body, dest)
            salvos.append(dest)
            print("  salvo:", dest.name, flush=True)
        pendentes = pendentes[len(novas):]
        await page.wait_for_timeout(4000)

    if pendentes:
        print("\n!!! FALTANDO APOS %d TENTATIVAS: %s" % (
            max_tentativas, ", ".join(n for n, _ in pendentes)), flush=True)
        for name in pendentes:
            print("   FALTANDO:", name, flush=True)
    return salvos, pendentes


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
        todos_faltantes = []
        for li, lote in enumerate(lotes, 1):
            print("\n=== LOTE %d/%d ===" % (li, len(lotes)), flush=True)
            _, faltantes = await processar_lote(page, lote, biblia, out_dir,
                                                args.wait, args.max_attempts,
                                                layout=args.layout,
                                                orientacao_fixa=args.orientacao)
            todos_faltantes.extend(faltantes)
            await page.wait_for_timeout(args.pause * 1000)
        if todos_faltantes:
            print("\n============================================================", flush=True)
            print("IMAGENS QUE FALTARAM (gerar depois):", flush=True)
            for n in todos_faltantes:
                print("  -", n, flush=True)
            print("============================================================", flush=True)
        # NAO chamar b.close(): conectamos via CDP e fecharia o Chrome do usuario.


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts-file", default=str(PROJECT / "artifacts" / "image_prompts.json"))
    ap.add_argument("--project-dir", default="")
    ap.add_argument("--out-dir", default="")
    ap.add_argument("--batch-size", type=int, default=10)
    ap.add_argument("--wait", type=int, default=600)
    ap.add_argument("--pause", type=float, default=4.0)
    ap.add_argument("--max-attempts", type=int, default=4,
                    help="tentativas para recuperar imagens faltantes de um lote")
    ap.add_argument("--layout", choices=("auto", "separado", "colagem"), default="auto",
                    help="auto sortea entre 1 painel e colagens de 2/3/4 (padrao)")
    ap.add_argument("--orientacao", choices=("auto", "lado_a_lado", "empilhado"),
                    default="auto", help="orientacao dos paineis da colagem")
    ap.add_argument("--cdp-url", default=DEFAULT_CDP)
    args = ap.parse_args()
    if args.project_dir and not args.out_dir:
        args.out_dir = str(Path(args.project_dir) / "assets" / "images" / "gemini" / "scenes")
    if not args.out_dir:
        args.out_dir = str(PROJECT / "assets" / "images" / "gemini" / "scenes")
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
