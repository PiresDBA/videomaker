# -*- coding: utf-8 -*-
"""fix_prompts_ref_personagem.py - Adiciona referencias de personagem do Flow
(@Frida, @Luna) em TODOS os prompts de imagem, para o Flow usar os personagens
SALVOS em vez de inventar outros (bug: cachorros de outras racas, pessoas).

Regra do usuario: sempre que o nome Frida/Luna aparecer no prompt, escrever
@Frida / @Luna (entre colchetes com @) para o Flow puxar o personagem salvo.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def aplicar(texto: str) -> str:
    # normaliza qualquer forma antiga (@Frida, @[Frida], [Frida]) -> @[Frida]
    texto = re.sub(r"@?\[?(?:Frid[oó]ca|Frida)\]?", "@[Frida]", texto, flags=re.I)
    texto = re.sub(r"@?\[?(?:Luninha|Luna)\]?", "@[Luna]", texto, flags=re.I)
    return texto


def main(path):
    p = Path(path)
    d = json.loads(p.read_text(encoding="utf-8"))
    n = 0
    for k, v in list(d.items()):
        if isinstance(v, str):
            novo = aplicar(v)
            if novo != v:
                d[k] = novo
                n += 1
    backup = p.with_suffix(".json.bak-ref")
    if not backup.exists():
        backup.write_text(json.dumps(json.loads(p.read_text(encoding="utf-8")),
                                     ensure_ascii=False, indent=2), encoding="utf-8")
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"prompts atualizados: {n}/{len(d)} -> {p}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else
         r"C:\videomaker\projects\bulldogue-ingles-frida-e-dachshund-marrom-luna-fic\artifacts\image_prompts.json")
