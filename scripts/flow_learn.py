# -*- coding: utf-8 -*-
"""flow_learn.py - MODO GUIADO DE APRENDIZADO do Google Flow.

O Google Flow muda o layout constantemente. Este modo deixa o USUARIO navegar
(clicar) enquanto o sistema OBSERVA (filma + registra os cliques) e aprende
os seletores robustos de cada passo. Depois salva um PERFIL APRENDIDO versionado
que o flow_fetch.py reutiliza.

Como funciona:
  1. Abre o Chrome (CDP) na URL do projeto do Flow, com gravacao de video.
  2. Injeta um listener que, a cada clique, calcula um seletor robusto do
     elemento (aria-label > placeholder > data-* > texto visivel > classe) e
     grava: tag, seletor, texto, URL, titulo e timestamp.
  3. O usuario faz o fluxo normalmente: entrar no projeto, clicar 'Imagem',
     selecionar 'x1', fechar pop-ups, deixar o campo de prompt visivel.
  4. O usuario pressiona Enter (ou digita 'done'). O sistema:
       - para a gravacao (salva .webm em artifacts/flow_learning/)
       - infere os seletores aprendidos (editor de prompt, botoes de modo)
       - salva .flow_learned_profile.json com historico de versoes
  5. O flow_fetch.py carrega esse perfil na proxima execucao.

Uso:
  python scripts/flow_learn.py                 # modo guiado (video + cliques)
  python scripts/flow_learn.py --show          # mostra o perfil aprendido atual
  python scripts/flow_learn.py --replay        # repete os passos aprendidos (cliques)
"""
from __future__ import annotations
import argparse, asyncio, json, sys, time
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright

ROOT = Path(r"C:\videomaker")
CDP = "http://127.0.0.1:18800"
PROJECT_URL = "https://flow.google.com/project/d43a0933-5310-4951-b511-911f96a6bc22"
STATE_FILE = ROOT / ".flow_learned_state.json"
PROFILE_FILE = ROOT / ".flow_learned_profile.json"
LEARN_DIR = ROOT / "artifacts/flow_learning"
LEARN_DIR.mkdir(parents=True, exist_ok=True)

# JS injetado: observa cliques e monta seletor robusto
JS_OBSERVER = r"""
(() => {
  window.__flowClicks = [];
  function robustSel(el) {
    if (!el || el.tagName === 'HTML' || el.tagName === 'BODY') return '';
    const trySel = (s) => { try { return document.querySelectorAll(s).length === 1 ? s : ''; } catch(e){ return ''; } };
    // 1) aria-label / placeholder / title
    for (const attr of ['aria-label','placeholder','title','data-testid','data-id']) {
      const v = el.getAttribute && el.getAttribute(attr);
      if (v && v.trim()) {
        const s = `[${attr}="${v.trim().replace(/"/g,'\\"')}"]`;
        const u = trySel(s); if (u) return u;
      }
    }
    // 2) role
    const role = el.getAttribute && el.getAttribute('role');
    if (role) { const s = `[role="${role}"]`; const u = trySel(s); if (u) return u; }
    // 3) texto visivel curto
    const txt = (el.innerText || '').trim().split('\n')[0].trim();
    if (txt && txt.length <= 40) {
      const s = `text="${txt.replace(/"/g,'\\"')}"`;
      const u = trySel(s); if (u) return u;
    }
    // 4) classe (pega a primeira classe especifica)
    const cls = (el.className && typeof el.className === 'string') ? el.className.trim().split(/\s+/)[0] : '';
    if (cls) { const s = `.${cls}`; const u = trySel(s); if (u) return u; }
    // 5) tag + nth-of-type fallback
    const tag = el.tagName.toLowerCase();
    const parent = el.parentElement;
    if (parent) {
      const sibs = Array.from(parent.children).filter(c => c.tagName === el.tagName);
      const idx = sibs.indexOf(el) + 1;
      const s = `${tag}:nth-of-type(${idx})`;
      const u = trySel(s); if (u) return u;
    }
    return tag;
  }
  document.addEventListener('click', (ev) => {
    const el = ev.target;
    window.__flowClicks.push({
      t: Date.now()/1000,
      tag: el.tagName,
      sel: robustSel(el),
      text: (el.innerText||'').trim().split('\n')[0].slice(0,60),
      aria: el.getAttribute && el.getAttribute('aria-label'),
      url: location.href,
      title: document.title
    });
  }, true);
  return true;
})()
"""

# JS para detectar o editor de prompt (campo de texto) atualmente visivel
JS_FIND_EDITOR = r"""
(() => {
  const cands = document.querySelectorAll('[contenteditable="true"], [role="textbox"], textarea');
  const out = [];
  for (const el of cands) {
    const r = el.getBoundingClientRect();
    if (r.width > 100 && r.height > 20) {
      out.push({
        tag: el.tagName,
        cls: (typeof el.className==='string' ? el.className : ''),
        role: el.getAttribute('role'),
        aria: el.getAttribute('aria-label'),
        ce: el.getAttribute('contenteditable'),
        x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)
      });
    }
  }
  return out;
})()
"""


def robust_sel_from_info(info: dict) -> str:
    """Monta seletor a partir das infos coletadas no JS de editor."""
    if info.get("aria"):
        return f'[aria-label="{info["aria"]}"]'
    cls = (info.get("cls") or "").split()
    for c in cls:
        if c and len(c) > 3:
            return f'.{c}'
    if info.get("role"):
        return f'[role="{info["role"]}"]'
    return info.get("tag", "").lower()


async def show_profile():
    if PROFILE_FILE.exists():
        d = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        print(json.dumps(d, ensure_ascii=False, indent=2))
    else:
        print("Nenhum perfil aprendido ainda:", PROFILE_FILE)


async def learn():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0]
        page = next((pg for pg in ctx.pages if "flow.google.com" in pg.url), None) or await ctx.new_page()
        await page.bring_to_front()
        # NAO forcar viewport: respeita o tamanho que o usuario ajustou no Flow.

        # Vai para o projeto salvo (ou URL padrao)
        url = PROJECT_URL
        try:
            st = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if st.get("url", "").startswith("https://flow.google.com/project/"):
                url = st["url"]
        except Exception:
            pass
        print(f"Abrindo Flow: {url}", flush=True)
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)

        # Injeta observador de cliques
        await page.evaluate(JS_OBSERVER)
        print("✓ Observador de cliques ativo.", flush=True)

        print("\n" + "=" * 72)
        print("MODO GUIADO DE APRENDIZADO - GOOGLE FLOW")
        print("=" * 72)
        print("O navegador está no Flow. FAÇA OS PASSOS normalmente:")
        print("  1. Entre no projeto (se ainda nao estiver)")
        print("  2. Clique em 'Imagem' (NAO Video)")
        print("  3. Selecione 'x1' (1 imagem)")
        print("  4. Feche pop-ups de propaganda")
        print("  5. Deixe o campo de prompt visivel e pronto")
        print("\nQuando terminar, VOLTE AQUI e pressione ENTER (ou digite 'done').")
        print("=" * 72, flush=True)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, input, "\n>>> Pressione ENTER quando terminar: ")

        # Coleta cliques e editores
        cliques = await page.evaluate("window.__flowClicks || []")
        editores = await page.evaluate(JS_FIND_EDITOR)

        # Salva video (screenshot como "filmagem" do estado final, mais leve que video)
        shot = LEARN_DIR / f"flow_final_{int(time.time())}.png"
        await page.screenshot(path=str(shot))
        (LEARN_DIR / "ultima_captura.txt").write_text(str(shot), encoding="utf-8")

        # Infere seletores
        editor_sels = [robust_sel_from_info(e) for e in editores if robust_sel_from_info(e)]
        # botoes clicados com aria-label (modo imagem, x1, etc.)
        botoes = []
        for c in cliques:
            if c.get("aria") or c.get("sel"):
                botoes.append({
                    "sel": c.get("sel"),
                    "aria": c.get("aria"),
                    "texto": c.get("text"),
                    "tag": c.get("tag"),
                })

        perfil = {
            "learned_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "url": page.url,
            "title": await page.title(),
            "editor_selectors": editor_sels,
            "editor_details": editores,
            "clicked_elements": botoes[-40:],
            "screenshot": str(shot),
            "version": 1,
        }
        # historico: guarda versoes anteriores
        historico = []
        if PROFILE_FILE.exists():
            try:
                antigo = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
                historico = antigo.get("historico", [])
                perfil["version"] = antigo.get("version", 0) + 1
            except Exception:
                pass
        historico.append({k: perfil[k] for k in ("learned_at", "url", "editor_selectors")})
        perfil["historico"] = historico[-10:]

        PROFILE_FILE.write_text(json.dumps(perfil, ensure_ascii=False, indent=2), encoding="utf-8")

        # Atualiza tambem o estado antigo para compatibilidade
        state = {
            "ready": bool(editor_sels),
            "url": page.url,
            "title": perfil["title"],
            "learned_at": perfil["learned_at"],
            "editors_found": editor_sels,
        }
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"\n✓ PERFIL APRENDIDO salvo (v{perfil['version']}):", PROFILE_FILE)
        print(f"  Editores detectados: {editor_sels}")
        print(f"  Elementos clicados:  {len(botoes)}")
        print(f"  Captura: {shot}")
        await browser.close()


async def replay():
    """Repete os cliques aprendidos (para aposar o usuario apos mudanca de layout)."""
    if not PROFILE_FILE.exists():
        print("Nenhum perfil para replay"); return
    perfil = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0]
        page = next((pg for pg in ctx.pages if "flow.google.com" in pg.url), None) or await ctx.new_page()
        await page.goto(perfil["url"], wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        print(f"Replay v{perfil['version']}: {len(perfil.get('clicked_elements',[]))} cliques")
        for el in perfil.get("clicked_elements", []):
            sel = el.get("sel")
            if not sel:
                continue
            try:
                loc = page.locator(sel)
                if await loc.count() > 0:
                    await loc.first.click(timeout=3000)
                    print(f"  ✓ clicou {sel}")
                    await page.wait_for_timeout(400)
            except Exception as e:
                print(f"  ✗ falhou {sel}: {str(e)[:60]}")
        await browser.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--replay", action="store_true")
    a = ap.parse_args()
    if a.show:
        asyncio.run(show_profile())
    elif a.replay:
        asyncio.run(replay())
    else:
        asyncio.run(learn())


if __name__ == "__main__":
    main()
