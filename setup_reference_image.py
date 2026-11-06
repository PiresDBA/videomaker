#!/usr/bin/env python3
"""Script to create reference image for Frida and Luna characters."""

import json
import os
from pathlib import Path

def download_reference_image():
    """Download and save a reference image for Frida and Luna."""
    # This is a placeholder - you would need to get an actual reference image
    # For demonstration, we'll create a simple text file indicating the location
    
    reference_dir = Path("C:\videomaker\scripts\reference")
    reference_dir.mkdir(exist_ok=True)
    
    # In a real scenario, you would download an image of Frida (bulldog)
    # and Luna (dachshund) here
    # For now, we'll create a placeholder file
    
    placeholder_file = reference_dir / "frida_luna_reference.jpg"
    
    # Create a simple text file as a placeholder
    with open(placeholder_file, 'w', encoding='utf-8') as f:
        f.write("""Referência de Personagens: Frida (buldogue inglês) e Luna (dachshund)

Este arquivo indica onde a imagem de referência dos personagens deve ser salva.

Para setup:
1. Tire uma foto ou encontre uma imagem clara de:
   - Frida: buldogue inglês, focinho curto, olhos doces
   - Luna: dachshund marrom, orelhas erguidas, expressão curiosa
2. Salve a imagem em: scripts/reference/frida_luna_reference.jpg
3. Atualize config.json com o caminho correto

A imagem de referência é usada para:
- Dar contexto visual ao Gemini
- Manter consistência na aparência dos personagens
- Melhorar a qualidade das imagens geradas

Sem referência: as imagens podem variar muito em estilo e aparência
Com referência: as imagens mantêm a consistência das personagens
""")
    
    print(f"✓ Referência de personagens criada em: {placeholder_file}")
    return placeholder_file

def update_config(reference_path):
    """Update config.json with reference_image path."""
    scripts_dir = Path("scripts")
    config_file = scripts_dir / "config.json"
    
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        # Create default config
        config = {
            "gemini_skill": "gemini_media_scraping-1.0.0.ipkg.json",
            "ffmpeg_dir": "ffmpeg",
            "project_dir": "..",
            "image_bank": "banco de imagens",
            "reference_image": ""
        }
    
    # Update reference_image
    abs_path = os.path.abspath(reference_path)
    config["reference_image"] = abs_path
    
    # Save config
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"✓ config.json atualizado com referência de personagens: {abs_path}")
    
    return config_file

if __name__ == "__main__":
    print("=== Configuração de Imagem de Referência ===\n")
    
    # Check if config.json already has reference_image
    config_path = Path("scripts\config.json")
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        if "reference_image" in config and config["reference_image"]:
            print(f"✓ Configuração de referência de personagens já existe: {config['reference_image']}")
            exit(0)
    
    # Download reference image
    ref_path = download_reference_image()
    
    # Update config
    update_config(ref_path)
    
    print("\n=== Próximos Passos ===")
    print("1. Suba a foto real de Frida e Luna para:")
    print(f"   scripts/reference/frida_luna_reference.jpg")
    print("2. Atualize config.json com o caminho correto")
    print("3. Reinicie o Chrome com --login para salvar a nova sessão")
    print("4. Execute o pipeline novamente")
    
    print("\nNota: A referência de personagens deve ser:")
    print("  - Foto clara e em alta resolução")
    print("  - Mostra tanto Frida quanto Luna")
    print("  - Sem fundo ou contexto que possa confundir o Gemini")
    print("  - Arquivo no formato JPG/PNG, menos de 5MB")
