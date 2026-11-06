#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path

def generate_description(script):
    theme = script.get("title", "Os Superfocinhos em Ação!")
    
    hook = ""
    storyline = []
    
    for section in script.get("sections", []):
        if section.get("id") == "s0":
            continue
        elif section.get("id") == "s1":
            hook = section.get("text", "")
        elif section.get("id") != "s_outro":
            storyline.append(section.get("text", ""))
    
    description_parts = []
    title = theme
    
    if hook:
        description_parts.append(f"{hook}")
    
    if storyline:
        description_parts.append("")
        for i, sentence in enumerate(storyline, 1):
            description_parts.append(f"{sentence}")
        description_parts.append("")
    
    description_parts.append("Vídeo gerado por inteligência artificial — a criatividade brilha aqui! Este vídeo foi criado completamente com IA e sem humanos no set, mostrando todo o poder da nova geração de ferramentas criativas.")
    
    description_parts.append("")
    description_parts.append("Não contém promoção paga — apenas diversão pura de cachorros! 🐶📺")
    
    description_parts.append("")
    description_parts.append("Siga-nos para mais aventuras diárias com a Frida e a Luna — a alegria dos pets nunca termina!")
    
    return title, "\n\n".join(description_parts)

def main():
    project_path = Path(r"C:\videomaker\projects\caes-de-resgate-como-eles-encontram-pess")
    
    with open(project_path / "project-control.json", "r", encoding="utf-8") as f:
        project_data = json.load(f)
    
    with open(project_path / r"artifacts\script.json", "r", encoding="utf-8") as f:
        script_data = json.load(f)
    
    title, description = generate_description(script_data)
    
    project_data["publish"]["title"] = title
    project_data["publish"]["description"] = description
    project_data["publish"]["done"] = True
    project_data["publish"]["ts"] = "2026-11-06 16:00:00"
    
    with open(project_path / "project-control.json", "w", encoding="utf-8") as f:
        json.dump(project_data, f, ensure_ascii=False, indent=2)
    
    print("=== Remediado com sucesso ===")
    print(f"Título: {title}")
    word_count = len(description.split())
    print(f"Descrição gerada com {word_count} palavras")
    print(f"Status: publish.done = True")
    print(f"\n=== Preview da descrição ===")
    print(description)

if __name__ == "__main__":
    main()
