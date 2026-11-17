import asyncio, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        page = [p for p in b.contexts[0].pages if 'flow.google.com' in p.url][0]
        # abrir menu 'Adicionar elementos'
        add = page.locator('[aria-label*="Adicionar elementos" i]')
        await add.last.evaluate("(e)=>e.click()")
        await page.wait_for_timeout(1000)
        # listar opcoes do menu
        body = await page.locator('body').inner_text()
        for kw in ['Personagens','Avatares','Envios','Fazer upload de mídia']:
            i = body.find(kw)
            print("MENU", kw, i, repr(body[max(0,i-80):i+120]) if i>=0 else '', flush=True)
        # clicar em Personagens pelo texto dentro do menu
        pers = page.locator('[role="menuitem"], .mat-mdc-menu-item, [matlistitemtitle]').filter(has_text='Personagens')
        print("pers count", await pers.count(), flush=True)
        for i in range(await pers.count()):
            print("  ", (await pers.nth(i).evaluate("(e)=>e.outerHTML.slice(0,300)")), flush=True)
        if await pers.count():
            await pers.first.evaluate("(e)=>e.click()")
            await page.wait_for_timeout(1500)
            print("apos clicar Personagens", flush=True)
            body2 = await page.locator('body').inner_text()
            j = body2.find('Frida')
            print("Frida idx", j, repr(body2[max(0,j-200):j+300]) if j>=0 else '', flush=True)
asyncio.run(main())
