# -*- coding: utf-8 -*-
path = "scripts/flow_fetch.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

def rep(old, new):
    global content
    n = content.count(old)
    if n != 1:
        raise SystemExit(f"ANCORA NAO ENCONTRADA/AMBIGUA (n={n}): {old[:70]!r}")
    content = content.replace(old, new, 1)
    print("OK substituiu:", old[:60].replace("\n", "\\n"))

# 1) Constantes apos MIME_EXT (antes de class LoginRequired).
rep(
    "class LoginRequired(Exception):",
    '# Labels aceitos para o toggle de modo Imagem no painel de configuracoes do Flow.\n'
    'IMAGE_MODE_LABELS = ("Imagem", "Gerar imagem", "Modo imagem", "Imagem estatica")\n'
    '# Seletores do botao que abre o painel de configuracoes (Gatilho de configuracoes).\n'
    'SETTINGS_TRIGGER_SELECTORS = (\n'
    '    \'button[aria-label="Gatilho de configuracoes"]\',\n'
    '    \'button.settings-trigger-button\',\n'
    '    \'button[aria-label*="configuracoes" i]\',\n'
    '    \'button[aria-label*="settings" i]\',\n'
    '    \'[role="button"][aria-label*="configuracoes" i]\',\n'
    ')\n'
    '\n'
    'class LoginRequired(Exception):'
)

# 2) Funcao auxiliar _loc_first_visible antes de select_image_mode.
rep(
    'async def select_image_mode(page, aspect: str = "16:9") -> bool:',
    'async def _loc_first_visible(page, selectors, timeout_ms: int = 4000):\n'
    '    """Retorna o primeiro locator visivel dentre os seletores informados."""\n'
    '    for sel in selectors:\n'
    '        try:\n'
    '            loc = page.locator(sel).first\n'
    '            if await loc.count() > 0:\n'
    '                try:\n'
    '                    await loc.wait_for(state="visible", timeout=timeout_ms)\n'
    '                    return loc\n'
    '                except Exception:\n'
    '                    continue\n'
    '        except Exception:\n'
    '            continue\n'
    '    return None\n'
    '\n'
    'async def select_image_mode(page, aspect: str = "16:9") -> bool:'
)

# 3) _dismiss_overlays: pressiona Escape antes de clicar no backdrop.
rep(
    "    try:\n        backdrop = page.locator('.cdk-overlay-backdrop').first",
    "    try:\n        await page.keyboard.press(\"Escape\")\n        await page.wait_for_timeout(400)\n    except Exception:\n        pass\n    try:\n        backdrop = page.locator('.cdk-overlay-backdrop').first"
)

# 4) grab_image: fecha overlays remanescentes antes do botao de download.
rep(
    "                continue\n            if await count_dl(page) > before:",
    "                continue\n"
    "            # Fecha overlays remanescentes antes de tentar o botao de download\n"
    "            try:\n"
    "                await _dismiss_overlays(page)\n"
    "            except Exception:\n"
    "                pass\n"
    "            if await count_dl(page) > before:"
)

# 5) Reescreve o corpo do try de select_image_mode (robusto a labels e seletores).
start_marker = "        toggle = page.locator('mat-button-toggle:has-text(\"Imagem\")').first"
end_marker = "        return True\n"
si = content.index(start_marker)
ei = content.index(end_marker, si) + len(end_marker)
new_body = (
    "        await _dismiss_overlays(page)\n"
    "        # Abrir o painel de configuracoes tentando todos os seletores conhecidos.\n"
    "        trig = await _loc_first_visible(page, SETTINGS_TRIGGER_SELECTORS, timeout_ms=5000)\n"
    "        if trig is None:\n"
    '            print("  AVISO: painel de configuracoes nao encontrado; abortando para nao gerar video", flush=True)\n'
    "            return False\n"
    "        try:\n"
    "            await trig.click(timeout=5000)\n"
    "        except Exception:\n"
    "            await trig.evaluate(\"(el) => el.click()\")\n"
    "        await page.wait_for_timeout(900)\n"
    "\n"
    "        # Procurar o toggle de modo Imagem entre os labels conhecidos.\n"
    "        toggle = None\n"
    "        for label in IMAGE_MODE_LABELS:\n"
    '            cand = page.locator(f\'mat-button-toggle:has-text("{label}")\').first\n'
    "            try:\n"
    "                if await cand.count() > 0:\n"
    "                    toggle = cand\n"
    "                    break\n"
    "            except Exception:\n"
    "                continue\n"
    "        if toggle is None:\n"
    '            print("  AVISO: opcao \'Imagem\' nao apareceu no painel; abortando para nao gerar video", flush=True)\n'
    "            return False\n"
    "\n"
    "        if not await _toggle_checked(toggle):\n"
    '            btn = toggle.locator("button").first\n'
    "            try:\n"
    "                if await btn.count():\n"
    "                    await btn.click(timeout=5000)\n"
    "                else:\n"
    "                    await toggle.click(timeout=5000)\n"
    "            except Exception:\n"
    "                await toggle.evaluate(\"(el) => el.click()\")\n"
    "            await page.wait_for_timeout(700)\n"
    "\n"
    "        if not await _toggle_checked(toggle):\n"
    '            print("  AVISO: nao foi possivel confirmar o modo Imagem; abortando para nao gerar video", flush=True)\n'
    "            return False\n"
    "\n"
    "        if aspect:\n"
    '            asp = page.locator(f\'mat-button-toggle:has-text("{aspect}")\').first\n'
    "            if await asp.count() and not await _toggle_checked(asp):\n"
    "                try:\n"
    '                    await asp.locator("button").first.click(timeout=4000)\n'
    "                except Exception:\n"
    "                    try:\n"
    '                        await asp.evaluate("(el) => el.click()")\n'
    "                    except Exception:\n"
    "                        pass\n"
    "                await page.wait_for_timeout(300)\n"
    "\n"
    "        try:\n"
    "            await page.keyboard.press(\"Escape\")\n"
    "        except Exception:\n"
    "            pass\n"
    "        await page.wait_for_timeout(300)\n"
    '        print(f"  modo Imagem selecionado (x1, {aspect or \'aspecto atual\'}) (nunca video)", flush=True)\n'
    "        return True\n"
)
content = content[:si] + new_body + content[ei:]

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("TODAS AS SUBSTITUICOES APLICADAS")
