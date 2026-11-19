# -*- coding: utf-8 -*-
"""flow_observe_collect.py - Coleta os cliques observados, infere seletores,
tira captura e salva o PERFIL APRENDIDO (versionado).
"""
import asyncio, json, sys, time
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright
from flow_learn import (CDP, PROFILE_FILE, STATE_FILE, LEARN_DIR,
                        JS_FIND_EDITOR, robust_sel_from_info)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp(CDP)
        ctx = b.contexts[0]
        page = next((pg for pg in ctx.pages if "flow.google.com" in pg.url), None)
        if not page:
            print("ERRO: aba do Flow nao encontrada"); return
        cliques = await page.evaluate("window.__flowClicks || []")
        editores = await page.evaluate(JS_FIND_EDITOR)
        shot = LEARN_DIR / f"flow_{int(time.time())}.png"
        await page.screenshot(path=str(shot))

        editor_sels = [robust_sel_from_info(e) for e in editores if robust_sel_from_info(e)]
        botoes = [{"sel": c.get("sel"), "aria": c.get("aria"), "texto": c.get("text"), "tag": c.get("tag")}
                  for c in cliques if c.get("sel") or c.get("aria")]

        perfil = {
            "learned_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "url": page.url, "title": await page.title(),
            "editor_selectors": editor_sels, "editor_details": editores,
            "clicked_elements": botoes[-60:], "screenshot": str(shot), "version": 1,
        }
        historico = []
        if PROFILE_FILE.exists():
            try:
                antigo = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
                historico = antigo.get("historico", [])
                perfil["version"] = antigo.get("version", 0) + 1
            except Exception: pass
        historico.append({k: perfil[k] for k in ("learned_at", "url", "editor_selectors")})
        perfil["historico"] = historico[-10:]
        PROFILE_FILE.write_text(json.dumps(perfil, ensure_ascii=False, indent=2), encoding="utf-8")

        state = {"ready": bool(editor_sels), "url": page.url, "title": perfil["title"],
                 "learned_at": perfil["learned_at"], "editors_found": editor_sels}
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"✓ PERFIL v{perfil['version']} salvo:", PROFILE_FILE)
        print(f"  Editores: {editor_sels}")
        print(f"  Cliques observados: {len(botoes)}")
        for bt in botoes[-12:]:
            print(f"    - {bt.get('aria') or bt.get('texto') or bt.get('tag')}  ->  {bt.get('sel')}")
        print(f"  Captura: {shot}")
        await b.close()

if __name__ == "__main__":
    asyncio.run(main())
