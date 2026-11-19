# -*- coding: utf-8 -*-
"""flow_agent_batch_on.py - Variante do flow_agent_batch que MANTEM o modo
Agente LIGADO (o usuario confirmou que o Agente gera bem no Flow atual).

Wrappa o flow_agent_batch original e substitui ativar_agente() para nao desligar.
Gera em lotes (padrao 10), sem regerar imagens ja existentes, mantendo a biblia
de continuidade e a identidade dos personagens.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, r"C:\videomaker\scripts")
import flow_agent_batch as fb


async def ativar_agente_on(page) -> bool:
    """Mantem o Agente LIGADO (o usuario prefere: gera varias de uma vez)."""
    chip = page.locator("button.agent-mode-chip")
    if await chip.count() == 0:
        print("  modo Agente: chip indisponivel (segue com padrao do Flow)", flush=True)
        return True
    pressed = await chip.get_attribute("aria-pressed") == "true"
    if not pressed:
        await chip.evaluate("(e)=>e.click()")
        await page.wait_for_timeout(800)
    pressed = await chip.get_attribute("aria-pressed") == "true"
    print("  modo Agente:", "ON (desejado)" if pressed else "OFF (nao conseguiu ligar)", flush=True)
    return pressed


def main():
    # substitui a funcao no modulo antes de rodar o main original
    fb.ativar_agente = ativar_agente_on
    fb.main()


if __name__ == "__main__":
    main()
