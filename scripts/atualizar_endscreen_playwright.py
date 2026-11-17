#!/usr/bin/env python3
"""
Adiciona tela final (end screen) em TODOS os vídeos publicados de um canal,
usando automação de navegador (Playwright + CDP) no YouTube Studio.

End screen inclui:
  1. Botao de inscricao no canal (canto inferior esquerdo)
  2. Video sugerido do proprio canal (canto inferior direito)
     - o YouTube escolhe automaticamente qual video recomendar

Uso:
  python scripts/atualizar_endscreen_playwright.py pt
  python scripts/atualizar_endscreen_playwright.py en
  python scripts/atualizar_endscreen_playwright.py es

Requisitos:
  - Chrome aberto com remote-debugging-port=18800
  - Usuario logado no Google no Chrome
  - Vídeos devem ter duracao >= 25 segundos
  - Vídeos nao podem ser "feito para criancas" (kids=true bloqueia end screen)

Fluxo no YouTube Studio:
  1. https://studio.youtube.com/channel/UC/videos
  2. Clicar em um vídeo para abrir "Detalhes do vídeo"
  3. Clicar em "Editor" no menu lateral esquerdo
  4. Clicar em "Tela final" no painel direito
  5. Clicar em "+ Elemento" para adicionar inscrição
  6. Clicar em "+ Elemento" para adicionar vídeo sugerido
  7. Clicar em "Salvar"

O YouTube Studio usa shadow DOM extensivamente. O script usa JavaScript
que percorre element.shadowRoot recursivamente para acessar elementos
internos.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from youtube_metadados import CREDS

from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent
CDP_URL = "http://127.0.0.1:18800"

TIMEOUT_ELEMENTO = 15000
PAUSA_ENTRE_VIDEOS = 3


async def js_click_texto(page, texto: str) -> bool:
    """Clica em elemento que contenha o texto especificado, navegando shadow DOM."""
    codigo = f"""
    (async () => {{
        const textoBusca = {texto!r};
        function encontrarEClicar(root, profundidade) {{
            if (!root || profundidade > 10) return false;
            const filhos = root.children || root.shadowRoot?.children || [];
            for (const filho of filhos) {{
                try {{
                    // Verificar se este elemento contém o texto
                    const textoEl = filho.textContent || '';
                    if (textoEl.includes(textoBusca)) {{
                        filho.click();
                        return true;
                    }}
                    // Recursivamente entrar em shadow root
                    if (filho.shadowRoot) {{
                        if (encontrarEClicar(filho.shadowRoot, profundidade + 1)) return true;
                    }}
                    // Recursivamente entrar em filhos normais
                    if (encontrarEClicar(filho, profundidade + 1)) return true;
                }} catch (e) {{}}
            }}
            return false;
        }}
        return encontrarEClicar(document, 0);
    }})();
    """
    try:
        resultado = await page.evaluate(codigo)
        return bool(resultado)
    except Exception as e:
        print(f"      js_click falhou para '{texto}': {e}", flush=True)
        return False


async def js_existe_texto(page, texto: str) -> bool:
    """Verifica se elemento com o texto existe no shadow DOM."""
    codigo = f"""
    (() => {{
        const textoBusca = {texto!r};
        function encontrar(root, profundidade) {{
            if (!root || profundidade > 10) return false;
            const filhos = root.children || root.shadowRoot?.children || [];
            for (const filho of filhos) {{
                try {{
                    const textoEl = filho.textContent || '';
                    if (textoEl.includes(textoBusca)) return true;
                    if (filho.shadowRoot && encontrar(filho.shadowRoot, profundidade + 1)) return true;
                    if (encontrar(filho, profundidade + 1)) return true;
                }} catch (e) {{}}
            }}
            return false;
        }}
        return encontrar(document, 0);
    }})();
    """
    try:
        resultado = await page.evaluate(codigo)
        return bool(resultado)
    except Exception:
        return False


async def listar_videos_pagina(page) -> list:
    """Lista vídeos visíveis na página atual do YouTube Studio."""
    try:
        dados = await page.evaluate("""
            () => {
                const resultados = [];
                function extrair(root, profundidade) {
                    if (!root || profundidade > 10) return;
                    const filhos = root.children || root.shadowRoot?.children || [];
                    for (const filho of filhos) {
                        try {
                            const tag = filho.tagName || '';
                            const texto = filho.textContent ? filho.textContent.trim() : '';
                            const id = filho.getAttribute('video-id') || filho.id || '';
                            // IDs do YouTube têm exatamente 11 caracteres alfanuméricos
                            const ehIdValido = /^[A-Za-z0-9_-]{11}$/.test(id);
                            if (ehIdValido && texto && texto.length > 3 && !resultados.find(r => r.video_id === id)) {
                                resultados.push({video_id: id, title: texto.substring(0, 100)});
                            }
                            if (filho.shadowRoot) {
                                extrair(filho.shadowRoot, profundidade + 1);
                            }
                            extrair(filho, profundidade + 1);
                        } catch (e) {}
                    }
                }
                extrair(document, 0);
                return resultados;
            }
        """)
        return dados or []
    except Exception as e:
        print(f"      Erro ao listar vídeos: {e}", flush=True)
        return []


async def navegar_conteudo(page, lang):
    """Navega para a página de Conteúdo/Vídeos do YouTube Studio."""
    print(f"  Navegando para YouTube Studio (canal {lang.upper()})...", flush=True)
    await page.goto("https://studio.youtube.com", wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(5000)

    if "accounts.google.com" in page.url:
        print("  LOGIN NECESSÁRIO no navegador!", flush=True)
        print("  Faça login no YouTube Studio no Chrome.", flush=True)
        return False

    await page.goto("https://studio.youtube.com/channel/UC/videos", wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(5000)

    url_atual = page.url
    print(f"  URL: {url_atual}", flush=True)

    videos = await listar_videos_pagina(page)
    print(f"  Encontrados {len(videos)} vídeo(s).", flush=True)
    for v in videos[:5]:
        print(f"    - {v['video_id']}: {v['title'][:60]}", flush=True)

    return len(videos) > 0


async def processar_video_endscreen(page, video_id, video_title) -> bool:
    """Adiciona end screen a um único vídeo."""
    print(f"    Processando: {video_id} - {video_title[:60]}", flush=True)

    try:
        # Navegar para edição do vídeo
        await page.goto(f"https://studio.youtube.com/video/{video_id}/edit", wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(5000)

        url_atual = page.url
        if video_id not in url_atual:
            print(f"      AVISO: não navegar para edição de {video_id}, URL: {url_atual[:80]}", flush=True)
            return False

        # Clicar em "Editor" no menu lateral esquerdo
        print("      Procurando botão 'Editor'...", flush=True)
        clicou_editor = await js_click_texto(page, "Editor")
        if not clicou_editor:
            print("      AVISO: não encontrou botão 'Editor'", flush=True)
            return False
        await page.wait_for_timeout(3000)

        # Clicar em "Tela final" no painel direito
        print("      Procurando 'Tela final'...", flush=True)
        clicou_tela = await js_click_texto(page, "Tela final")
        if not clicou_tela:
            clicou_tela = await js_click_texto(page, "End screen")
        if not clicou_tela:
            print("      AVISO: não encontrou 'Tela final'", flush=True)
            return False
        await page.wait_for_timeout(3000)

        # Adicionar botão de inscrição
        print("      Adicionando botão de inscrição...", flush=True)
        clicou_elemento = await js_click_texto(page, "+ Elemento")
        if clicou_elemento:
            await page.wait_for_timeout(2000)
            clicou_inscricao = await js_click_texto(page, "Inscrever-se")
            if not clicou_inscricao:
                clicou_inscricao = await js_click_texto(page, "Subscribe")
            if clicou_inscricao:
                print("      Botão de inscrição adicionado.", flush=True)
                await page.wait_for_timeout(2000)

        # Adicionar vídeo sugerido
        print("      Adicionando vídeo sugerido...", flush=True)
        clicou_elemento2 = await js_click_texto(page, "+ Elemento")
        if clicou_elemento2:
            await page.wait_for_timeout(2000)
            clicou_video = await js_click_texto(page, "Vídeo")
            if not clicou_video:
                clicou_video = await js_click_texto(page, "Video")
            if clicou_video:
                print("      Vídeo sugerido adicionado.", flush=True)
                await page.wait_for_timeout(2000)

        # Salvar
        print("      Salvando...", flush=True)
        clicou_salvar = await js_click_texto(page, "Salvar")
        if not clicou_salvar:
            clicou_salvar = await js_click_texto(page, "Save")
        if clicou_salvar:
            print("      Salvo com sucesso.", flush=True)
            await page.wait_for_timeout(2000)

        print(f"      ✓ Concluído: {video_id}", flush=True)
        return True

    except Exception as e:
        print(f"      ✗ Erro: {video_id} - {str(e)[:100]}", flush=True)
        return False


async def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/atualizar_endscreen_playwright.py <pt|en|es>")
        return 1

    lang = sys.argv[1].lower()
    if lang not in ("pt", "en", "es"):
        print(f"Idioma inválido: {lang}. Use: pt, en, es")
        return 1

    print(f"=== Atualizar End Screen - Canal {lang.upper()} ===", flush=True)
    print("IMPORTANTE: Deixe o Chrome aberto com remote-debugging-port=18800", flush=True)
    print("e já logado no YouTube Studio.", flush=True)
    print()

    async with async_playwright() as p:
        print("Conectando ao Chrome na porta 18800...", flush=True)
        try:
            browser = await p.chromium.connect_over_cdp(CDP_URL, timeout=15000)
        except Exception as e:
            print(f"Erro ao conectar ao Chrome: {e}", flush=True)
            print("Rode primeiro: chrome.exe --remote-debugging-port=18800 --user-data-dir=...", flush=True)
            return 1

        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        pages = context.pages
        page = pages[0] if pages else await context.new_page()

        tem_videos = await navegar_conteudo(page, lang)
        if not tem_videos:
            print("Não foi possível encontrar vídeos na página do YouTube Studio.", flush=True)
            print("Verifique se está logado e na página correta.", flush=True)
            await browser.close()
            return 1

        videos = await listar_videos_pagina(page)
        print(f"\nProcessando {len(videos)} vídeo(s)...\n", flush=True)

        ok = 0
        erros = 0
        for i, v in enumerate(videos, 1):
            print(f"[{i}/{len(videos)}] {v['video_id']}", flush=True)
            sucesso = await processar_video_endscreen(page, v["video_id"], v["title"])
            if sucesso:
                ok += 1
            else:
                erros += 1
            await asyncio.sleep(PAUSA_ENTRE_VIDEOS)

        print(f"\n=== Resultado: {ok} OK, {erros} erros, {len(videos)} total ===", flush=True)

        await browser.close()
        return 0


if __name__ == "__main__":
    asyncio.run(main())
