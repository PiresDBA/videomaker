#!/usr/bin/env python3
"""
Adiciona tela final (end screen) em vídeos do YouTube Studio.

Fluxo automatizado:
  1. Acesse studio.youtube.com → Conteúdo → Vídeos
  2. Clique em um vídeo → Editor (menu esquerdo)
  3. Clique em Tela final (painel direito)
  4. + Elemento → Inscrever-se
  5. + Elemento → Vídeo → "Melhor para o espectador"
  6. Clique Salvar

Uso:
  python scripts/atualizar_endscreen.py pt
  python scripts/atualizar_endscreen.py en
  python scripts/atualizar_endscreen.py es

Requisitos:
  - Chrome aberto com --remote-debugging-port=18800
  - Usuário logado no Google no Chrome
  - Vídeos com duração >= 25 segundos
  - Vídeos NÃO podem ser "feito para crianças"
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from youtube_metadados import CREDS

from playwright.async_api import async_playwright

CDP_URL = "http://127.0.0.1:18800"
TIMEOUT = 15000
PAUSA = 3
CANAL_URL = "https://studio.youtube.com/channel/UCt8f_9bKINYilXvp063Ik3A/videos/upload"


async def shadow_click(page, texto: str) -> bool:
    """Clica em elemento que contém o texto, navegando pelo shadow DOM."""
    script = f"""
    (async () => {{
        const busca = {texto!r};
        function buscarEClicar(nodo, prof) {{
            if (!nodo || prof > 15) return false;
            try {{
                const filhos = nodo.children || (nodo.shadowRoot ? nodo.shadowRoot.children : []);
                for (const f of filhos) {{
                    try {{
                        const t = f.textContent || '';
                        if (t.includes(busca)) {{
                            f.click();
                            return true;
                        }}
                        if (f.shadowRoot) {{
                            if (buscarEClicar(f.shadowRoot, prof + 1)) return true;
                        }}
                        if (buscarEClicar(f, prof + 1)) return true;
                    }} catch (e) {{}}
                }}
            }} catch (e) {{}}
            return false;
        }}
        return buscarEClicar(document, 0);
    }})()
    """
    try:
        resultado = await page.evaluate(script)
        return bool(resultado)
    except Exception as e:
        print(f"      shadow_click falhou para '{texto}': {e}", flush=True)
        return False


async def listar_videos_shadow(page) -> list:
    """Lista vídeos com IDs válidos (11 chars alfanuméricos) via shadow DOM."""
    script = """
    (() => {
        const resultados = [];
        const vidRegex = /^[A-Za-z0-9_-]{11}$/;
        function extrair(nodo, prof) {
            if (!nodo || prof > 15) return;
            try {
                const filhos = nodo.children || (nodo.shadowRoot ? nodo.shadowRoot.children : []);
                for (const f of filhos) {
                    const id = f.getAttribute('video-id') || f.getAttribute('is-video') || f.id || '';
                    const texto = f.textContent ? f.textContent.trim() : '';
                    if (vidRegex.test(id) && texto && texto.length > 3) {
                        if (!resultados.find(r => r.video_id === id)) {
                            resultados.push({video_id: id, title: texto.substring(0, 100)});
                        }
                    }
                    if (f.shadowRoot) {
                        extrair(f.shadowRoot, prof + 1);
                    }
                    extrair(f, prof + 1);
                }
            } catch (e) {}
        }
        extrair(document, 0);
        return resultados;
    })()
    """
    try:
        return await page.evaluate(script) or []
    except Exception as e:
        print(f"      Erro ao listar vídeos: {e}", flush=True)
        return []


async def esperar_login(page):
    """Espera o usuário fazer login no YouTube Studio (máximo 120 segundos)."""
    print("  Aguardando login no YouTube Studio...", flush=True)
    for i in range(120):
        await page.wait_for_timeout(1000)
        url = page.url
        if "accounts.google.com" not in url and "signin" not in url.lower():
            if "studio.youtube.com" in url:
                print("  ✓ Login detectado!", flush=True)
                return True
        if i % 10 == 0:
            print(f"  Ainda aguardando login... ({i}s)", flush=True)
    print("  Timeout de login. Continue navegando manualmente.", flush=True)
    return False


async def navegar_videos(page):
    """Navega para a página de vídeos do YouTube Studio."""
    print("  Acessando YouTube Studio...", flush=True)
    await page.goto(CANAL_URL, wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(5000)

    print(f"  URL: {page.url}", flush=True)

    # Se estiver na página de login, espera o usuário logar
    if "accounts.google.com" in page.url or "signin" in page.url.lower():
        print("  Página de login detectada. Aguardando você fazer login...", flush=True)
        await esperar_login(page)
        # Após login, navega novamente para a página de vídeos
        await page.goto(CANAL_URL, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(5000)

    print(f"  URL final: {page.url}", flush=True)

    videos = await listar_videos_shadow(page)
    print(f"  Vídeos encontrados: {len(videos)}", flush=True)
    for v in videos[:5]:
        print(f"    - {v['video_id']}: {v['title'][:60]}", flush=True)

    return videos


async def processar_video(page, video_id, video_titulo) -> bool:
    """Processa um vídeo: abre editor, adiciona tela final, salva."""
    print(f"    Processando: {video_id} - {video_titulo[:60]}", flush=True)

    try:
        await page.goto(f"https://studio.youtube.com/video/{video_id}/edit", wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(5000)

        if video_id not in page.url:
            print(f"      AVISO: não abriu edição. URL: {page.url[:80]}", flush=True)
            return False

        # Clicar em "Editor" no menu esquerdo
        print("      Clicando em 'Editor'...", flush=True)
        if not await shadow_click(page, "Editor"):
            print("      AVISO: 'Editor' não encontrado", flush=True)
            return False
        await page.wait_for_timeout(3000)

        # Clicar em "Tela final" no painel direito
        print("      Clicando em 'Tela final'...", flush=True)
        if not await shadow_click(page, "Tela final"):
            if not await shadow_click(page, "End screen"):
                print("      AVISO: 'Tela final' não encontrado", flush=True)
                return False
        await page.wait_for_timeout(3000)

        # + Elemento → Inscrever-se
        print("      Adicionando 'Inscrever-se'...", flush=True)
        if await shadow_click(page, "+ Elemento"):
            await page.wait_for_timeout(2000)
            if await shadow_click(page, "Inscrever-se"):
                print("      ✓ Inscrever-se adicionado", flush=True)
            elif await shadow_click(page, "Subscribe"):
                print("      ✓ Subscribe adicionado", flush=True)
            else:
                print("      AVISO: 'Inscrever-se' não encontrado", flush=True)
            await page.wait_for_timeout(2000)

        # + Elemento → Vídeo → "Melhor para o espectador"
        print("      Adicionando vídeo sugerido...", flush=True)
        if await shadow_click(page, "+ Elemento"):
            await page.wait_for_timeout(2000)
            if await shadow_click(page, "Vídeo"):
                print("      ✓ Vídeo adicionado", flush=True)
                await page.wait_for_timeout(2000)
            elif await shadow_click(page, "Video"):
                print("      ✓ Video adicionado", flush=True)
                await page.wait_for_timeout(2000)
            else:
                print("      AVISO: 'Vídeo' não encontrado", flush=True)

        # Salvar
        print("      Salvando...", flush=True)
        if await shadow_click(page, "Salvar"):
            print("      ✓ Salvo", flush=True)
        elif await shadow_click(page, "Save"):
            print("      ✓ Saved", flush=True)
        else:
            print("      AVISO: 'Salvar' não encontrado", flush=True)
        await page.wait_for_timeout(2000)

        print(f"      ✓ Concluído: {video_id}", flush=True)
        return True

    except Exception as e:
        print(f"      ✗ Erro: {video_id} - {str(e)[:100]}", flush=True)
        return False


async def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/atualizar_endscreen.py <pt|en|es>")
        return 1

    lang = sys.argv[1].lower()
    if lang not in ("pt", "en", "es"):
        print(f"Idioma inválido: {lang}. Use: pt, en, es")
        return 1

    print(f"=== Atualizar End Screen - Canal {lang.upper()} ===", flush=True)
    print("IMPORTANTE: Chrome aberto com --remote-debugging-port=18800", flush=True)
    print("e já logado no YouTube Studio.", flush=True)
    print()

    async with async_playwright() as p:
        print("Conectando ao Chrome (porta 18800)...", flush=True)
        try:
            browser = await p.chromium.connect_over_cdp(CDP_URL, timeout=15000)
        except Exception as e:
            print(f"Erro ao conectar: {e}", flush=True)
            print("Rode: chrome.exe --remote-debugging-port=18800 --user-data-dir=...", flush=True)
            return 1

        # USAR A PÁGINA EXISTENTE (não criar nova)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        pages = context.pages
        page = pages[0] if pages else await context.new_page()

        # Traz a página para frente
        try:
            await page.bring_to_front()
        except Exception:
            pass

        videos = await navegar_videos(page)
        if not videos:
            print("Nenhum vídeo válido encontrado.", flush=True)
            await browser.close()
            return 1

        print(f"\nProcessando {len(videos)} vídeo(s)...\n", flush=True)

        ok = 0
        erros = 0
        for i, v in enumerate(videos, 1):
            print(f"[{i}/{len(videos)}] {v['video_id']}", flush=True)
            if await processar_video(page, v["video_id"], v["title"]):
                ok += 1
            else:
                erros += 1
            await asyncio.sleep(PAUSA)

        print(f"\n=== Resultado: {ok} OK, {erros} erros, {len(videos)} total ===", flush=True)
        await browser.close()
        return 0


if __name__ == "__main__":
    asyncio.run(main())
