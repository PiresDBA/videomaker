import asyncio, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.async_api import async_playwright

OUT = Path(r"C:\videomaker\agent_test")
OUT.mkdir(exist_ok=True)

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
        ctx = b.contexts[0]
        page = ctx.pages[0]
        imgs = await page.evaluate("() => Array.from(document.querySelectorAll('img')).map(i=>i.src).filter(s=>s.startsWith('https://flow.google.com/asb/'))")
        print("ASB IMGS", len(imgs), flush=True)
        for i, url in enumerate(imgs[:4]):
            try:
                r = await page.request.get(url, timeout=60000)
                body = await r.body()
                print(i, r.status, r.headers.get('content-type'), len(body), flush=True)
                if r.status == 200 and len(body) > 20000:
                    (OUT / f"img_{i}.jpg").write_bytes(body)
                    print("  saved", OUT / f"img_{i}.jpg", flush=True)
            except Exception as e:
                print(i, "ERR", str(e)[:100], flush=True)
        await b.close()

asyncio.run(main())
