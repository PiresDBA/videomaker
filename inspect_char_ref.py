import asyncio, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        page = b.contexts[0].pages[0]
        print("URL", page.url, flush=True)
        # procurar o botao/area 'Adicionar elementos a caixa de comando'
        for sel in ['[aria-label*="Adicionar elementos" i]', 'button:has-text("Adicionar elementos")']:
            loc = page.locator(sel)
            print(sel, await loc.count(), flush=True)
        # clicar no chip 'add' para ver opcoes
        add = page.locator('button[aria-label*="Adicionar elementos" i]')
        if await add.count():
            await add.last.evaluate("(e)=>e.click()")
            await page.wait_for_timeout(1200)
            print("--- after add click ---", flush=True)
            body = await page.locator('body').inner_text()
            for kw in ['Personagens', 'Frida', 'Luna', 'Pipoca', 'personagem']:
                i = body.find(kw)
                print(kw, i, repr(body[max(0,i-150):i+200]) if i>=0 else '', flush=True)
            # listar itens de menu/popover
            items = page.locator('[role="menuitem"], .mat-mdc-menu-item, [role="option"], li')
            print("items", await items.count(), flush=True)
            for i in range(min(await items.count(), 60)):
                t = (await items.nth(i).inner_text()).strip()
                if t:
                    print("  ITEM", i, repr(t[:80]), flush=True)
asyncio.run(main())
